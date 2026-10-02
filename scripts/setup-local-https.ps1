<#
.SYNOPSIS
로컬 nginx에 자체 서명 인증서로 HTTPS를 추가한다 — 실제 사내 SSO 브로커/ADFS가
콜백(redirect_uri)에 HTTPS를 요구할 때, 외부 터널(ngrok 등) 없이 사내망 안에서만
테스트할 수 있게 해준다. README.md "다른 서버로 옮겨서 실제 SSO 브로커에
연동하기" H번 절 참고.

.PARAMETER HostIp
브라우저가 실제로 접속하는 주소(방화벽에 열어둔 IP 등). 인증서의 SAN에
포함시켜야 브라우저가 "도메인이 안 맞다"는 별도 경고를 내지 않는다.

.PARAMETER TrustLocally
이 컴퓨터의 Windows 신뢰 저장소(Trusted Root Certification Authorities)에
생성한 인증서를 등록한다 — 등록하면 이 컴퓨터의 Chrome에서 "연결이 비공개
상태가 아님" 경고 없이 바로 접속된다. 로컬 신뢰 저장소를 바꾸는 보안 관련
동작이라 기본값은 꺼져 있다. 관리자 권한 PowerShell에서 실행해야 한다.

.PARAMETER Force
이미 인증서가 있어도 새로 만든다(기본은 있으면 그대로 종료 — 여러 번 실행해도
안전하게 아무 일도 안 일어남).

.EXAMPLE
scripts\setup-local-https.ps1 -HostIp 12.82.123.45 -TrustLocally
#>
param(
    [string]$HostIp = "",
    [switch]$TrustLocally,
    [switch]$Force
)

$root = Split-Path -Parent $PSScriptRoot
$certDir = "$root\nginx\certs"
$certPath = "$certDir\dev-selfsigned.crt"
$keyPath = "$certDir\dev-selfsigned.key"

if ((Test-Path $certPath) -and (Test-Path $keyPath) -and -not $Force) {
    Write-Host "이미 인증서가 있습니다(다시 만들려면 -Force): $certPath"
} else {
    # Windows PowerShell 5.1(.NET Framework)은 PFX -> PEM 변환에 필요한 편의
    # API(ExportRSAPrivateKeyPem 등)가 없어 순수 PowerShell로는 번거롭고
    # 깨지기 쉽다 — 이 프로젝트는 이미 Git for Windows 설치를 전제하므로
    # (README 전반에서 git 사용), 번들된 openssl로 PEM을 바로 만든다.
    $opensslExe = (Get-Command openssl -ErrorAction SilentlyContinue).Source
    if (-not $opensslExe) {
        $fallback = "C:\Program Files\Git\usr\bin\openssl.exe"
        if (Test-Path $fallback) { $opensslExe = $fallback }
    }
    if (-not $opensslExe) {
        Write-Error "openssl을 찾을 수 없습니다. Git for Windows가 설치돼 있는지 확인하거나, PATH에 openssl을 추가한 뒤 다시 시도하세요."
        exit 1
    }

    if (-not $HostIp) {
        Write-Warning "-HostIp를 지정하지 않았습니다 — localhost/127.0.0.1만 인증서에 포함됩니다. 실제 방화벽 IP로 접속한다면 -HostIp <그 IP>를 지정하세요."
    }

    New-Item -ItemType Directory -Force -Path $certDir | Out-Null

    $sanEntries = @("DNS:localhost", "IP:127.0.0.1")
    if ($HostIp) { $sanEntries += "IP:$HostIp" }
    $sanString = $sanEntries -join ","
    $subjectCn = if ($HostIp) { $HostIp } else { "localhost" }

    Write-Host "자체 서명 인증서 생성 중... (SAN: $sanString)"
    & $opensslExe req -x509 -newkey rsa:2048 -nodes -days 365 `
        -keyout $keyPath `
        -out $certPath `
        -subj "/CN=$subjectCn" `
        -addext "subjectAltName=$sanString"

    if ($LASTEXITCODE -ne 0) {
        Write-Error "인증서 생성에 실패했습니다(openssl 종료 코드 $LASTEXITCODE)."
        exit 1
    }
    Write-Host "생성 완료: $certPath / $keyPath"
}

if ($TrustLocally) {
    Write-Host ""
    Write-Host "이 컴퓨터의 Windows 신뢰 저장소(Trusted Root Certification Authorities)에"
    Write-Host "인증서를 등록합니다 — 관리자 권한이 필요합니다. 거부되면 수동으로"
    Write-Host "'$certPath' 파일을 더블클릭해 '로컬 컴퓨터' > '신뢰할 수 있는 루트 인증 기관'에 설치하세요."
    try {
        Import-Certificate -FilePath $certPath -CertStoreLocation Cert:\LocalMachine\Root -ErrorAction Stop | Out-Null
        Write-Host "등록 완료: Cert:\LocalMachine\Root"
    } catch {
        Write-Warning "LocalMachine\Root 등록 실패($($_.Exception.Message)) — CurrentUser\Root로 재시도합니다."
        Import-Certificate -FilePath $certPath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
        Write-Host "등록 완료: Cert:\CurrentUser\Root (이 사용자 계정에서만 신뢰됨)"
    }
}

# nginx/.env의 NGINX_HTTPS_PORT를 읽어 안내 메시지에 그대로 반영한다(없으면 기본값 8443).
. "$PSScriptRoot\_ports.ps1"
$httpsPort = (Get-DevPorts -Root $root).NginxHttpsPort
$displayHost = if ($HostIp) { $HostIp } else { "127.0.0.1" }

Write-Host ""
Write-Host "=== 다음 단계 ==="
Write-Host "1. scripts\start-dev.ps1을 (다시) 실행하면 nginx가 HTTPS도 같이 리슨합니다."
Write-Host "2. backend\.env의 SSO_REDIRECT_URI를 아래 값으로 바꾸세요:"
Write-Host "   https://${displayHost}:${httpsPort}/api/v1/auth/sso/callback"
Write-Host "3. 브로커에 등록된 redirect URI도 위와 동일하게 바꿔달라고 요청하세요(문자 그대로 일치해야 함)."
Write-Host "4. scripts\stop-dev.ps1 / scripts\start-dev.ps1로 완전히 재시작한 뒤 로그인을 다시 시도하세요."
if (-not $TrustLocally) {
    Write-Host ""
    Write-Host "참고: -TrustLocally 없이 실행했다면, 브라우저가 '연결이 비공개 상태가 아님' 경고를 띄웁니다 —"
    Write-Host "      테스트 중에는 '고급' -> '이동(안전하지 않음)'으로 진행하면 됩니다."
}

