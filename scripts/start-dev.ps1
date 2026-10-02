param(
    [int]$BackendPort = 0,
    [int]$VitePort = 0,
    [int]$NginxPort = 0,
    [int]$NginxHttpsPort = 0
)

$root = Split-Path -Parent $PSScriptRoot

# 포트 우선순위: 위 -BackendPort 등 명시적 파라미터(0이면 "안 줌") >
# $env:BACKEND_PORT 등 세션 환경변수 > 각 컴포넌트 .env 파일(backend/.env의
# PORT, frontend/.env의 FRONTEND_PORT, nginx/.env의 NGINX_PORT/NGINX_HTTPS_PORT)
# > 하드코딩 기본값(8000/5173/8080/8443). 세부 로직은 _ports.ps1 참고.
. "$PSScriptRoot\_ports.ps1"
$defaultPorts = Get-DevPorts -Root $root
if ($BackendPort -eq 0) { $BackendPort = $defaultPorts.BackendPort }
if ($VitePort -eq 0) { $VitePort = $defaultPorts.VitePort }
if ($NginxPort -eq 0) { $NginxPort = $defaultPorts.NginxPort }
if ($NginxHttpsPort -eq 0) { $NginxHttpsPort = $defaultPorts.NginxHttpsPort }

# 창을 숨겨서(-WindowStyle Hidden) 띄우므로, 평소처럼 웹페이지를 쓰면서 로그를
# 따로 보려면 파일로 남겨야 한다 — stdout/stderr를 합쳐서 하나의 로그 파일에
# 쓴다(uvicorn/Python logging 둘 다 보통 stderr로 나가므로 2>&1로 합침).
# 실시간으로 보려면 별도 창에서: Get-Content backend\uvicorn.log -Wait -Tail 20
Write-Host "Starting backend (uvicorn) on http://127.0.0.1:$BackendPort ... (log: backend\uvicorn.log)"
# PYTHONIOENCODING: 리다이렉트된 stdout/stderr는 콘솔이 아니라서 Python이
# Windows 로캘 코드페이지(cp949 등)로 쓸 수 있다 — 한글 로그가 깨지는 걸
# 막기 위해 UTF-8로 고정한다.
$env:PYTHONIOENCODING = "utf-8"
Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "$root\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $BackendPort > $root\backend\uvicorn.log 2>&1" `
    -WorkingDirectory $root -WindowStyle Hidden

Write-Host "Starting frontend (vite dev) on http://127.0.0.1:$VitePort ... (log: frontend\vite.log)"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd frontend && npm run dev -- --port $VitePort --strictPort > vite.log 2>&1" `
    -WorkingDirectory $root -WindowStyle Hidden

Start-Sleep -Seconds 2

$nginxExe = (Get-Command nginx -ErrorAction SilentlyContinue).Source
if (-not $nginxExe) {
    $fallback = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\nginxinc.nginx_*\nginx-*\nginx.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($fallback) { $nginxExe = $fallback.FullName }
}
if (-not $nginxExe) {
    Write-Warning "nginx.exe를 찾을 수 없습니다. 새 PowerShell 세션을 열어 PATH를 갱신한 뒤 다시 시도하세요."
} else {
    New-Item -ItemType Directory -Force -Path "$root\nginx\logs" | Out-Null
    New-Item -ItemType Directory -Force -Path "$root\nginx\temp" | Out-Null

    # 포트가 하드코딩된 nginx.conf 대신, 템플릿에서 매번 실제 포트로 치환한
    # 설정을 생성해 기동한다 — 세 서비스 포트를 .env 파일에서만 바꿔도 nginx가
    # 항상 같이 맞춰지게 하기 위함.
    $template = Get-Content "$root\nginx\nginx.conf.template" -Raw
    $generated = $template.
        Replace('__NGINX_PORT__', "$NginxPort").
        Replace('__BACKEND_PORT__', "$BackendPort").
        Replace('__VITE_PORT__', "$VitePort")

    # scripts/setup-local-https.ps1로 인증서를 만들어둔 경우에만 HTTPS
    # server 블록을 켠다 — 안 만들어뒀으면(지금까지 대부분의 경우) 이 블록
    # 전체를 들어내서 기존 HTTP-only 동작과 100% 동일하게 유지한다.
    $certPath = "$root\nginx\certs\dev-selfsigned.crt"
    $keyPath = "$root\nginx\certs\dev-selfsigned.key"
    $httpsEnabled = (Test-Path $certPath) -and (Test-Path $keyPath)

    if ($httpsEnabled) {
        $generated = $generated.
            Replace('__NGINX_HTTPS_PORT__', "$NginxHttpsPort").
            Replace('__SSL_CERT_PATH__', $certPath.Replace('\', '/')).
            Replace('__SSL_KEY_PATH__', $keyPath.Replace('\', '/')).
            Replace('# __HTTPS_SERVER_BLOCK_START__', '').
            Replace('# __HTTPS_SERVER_BLOCK_END__', '')
    } else {
        $generated = $generated -replace '(?s)# __HTTPS_SERVER_BLOCK_START__.*?# __HTTPS_SERVER_BLOCK_END__\r?\n', ''
    }

    Set-Content -Path "$root\nginx\nginx.generated.conf" -Value $generated -Encoding Ascii

    Write-Host "Starting nginx reverse proxy on http://127.0.0.1:$NginxPort ..."
    if ($httpsEnabled) {
        Write-Host "  + HTTPS(자체 서명 인증서) on https://127.0.0.1:$NginxHttpsPort ..."
    }
    Start-Process -FilePath $nginxExe -ArgumentList "-p", "$root\nginx\", "-c", "nginx.generated.conf" -WindowStyle Hidden
}

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "=== Status ==="
$portsToCheck = @($BackendPort, $VitePort, $NginxPort)
if ($httpsEnabled) { $portsToCheck += $NginxHttpsPort }
foreach ($port in $portsToCheck) {
    $listening = [bool](Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue)
    Write-Host "port $port : $(if ($listening) { 'UP' } else { 'DOWN' })"
}
