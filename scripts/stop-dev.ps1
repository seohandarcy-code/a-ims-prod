param(
    [int]$BackendPort = 0,
    [int]$VitePort = 0,
    [int]$NginxPort = 0,
    [int]$NginxHttpsPort = 0
)

$root = Split-Path -Parent $PSScriptRoot

# start-dev.ps1과 동일한 우선순위로 포트를 계산한다 — 여기서도 .env 파일
# 값이 바뀌어 있으면 자동으로 그 포트를 찾아서 끈다.
. "$PSScriptRoot\_ports.ps1"
$defaultPorts = Get-DevPorts -Root $root
if ($BackendPort -eq 0) { $BackendPort = $defaultPorts.BackendPort }
if ($VitePort -eq 0) { $VitePort = $defaultPorts.VitePort }
if ($NginxPort -eq 0) { $NginxPort = $defaultPorts.NginxPort }
if ($NginxHttpsPort -eq 0) { $NginxHttpsPort = $defaultPorts.NginxHttpsPort }

$ports = [ordered]@{ "$BackendPort" = "backend (uvicorn)"; "$VitePort" = "frontend (vite)"; "$NginxPort" = "nginx" }

# nginx가 자체 서명 인증서로 HTTPS도 같이 띄우고 있었다면(scripts/setup-local-https.ps1
# 참고) 그 포트도 상태 확인 목록에 추가한다 — 어차피 같은 nginx 프로세스라
# 위 sweep으로 이미 같이 종료되지만, 상태 출력에서 빠지지 않게 한다.
$certPath = "$root\nginx\certs\dev-selfsigned.crt"
$keyPath = "$root\nginx\certs\dev-selfsigned.key"
if ((Test-Path $certPath) -and (Test-Path $keyPath)) {
    $ports["$NginxHttpsPort"] = "nginx (https)"
}

foreach ($portKey in $ports.Keys) {
    $port = [int]$portKey
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $procId = $conn.OwningProcess
        if ($procId) {
            Write-Host "Stopping $($ports[$portKey]) (port $port, PID $procId)"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

# nginx uses a master/worker process pair on Windows; sweep any survivors.
Get-Process -Name nginx -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1
Write-Host ""
Write-Host "=== Status ==="
foreach ($portKey in $ports.Keys) {
    $port = [int]$portKey
    $stillUp = [bool](Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue)
    if ($stillUp) {
        Write-Warning "$($ports[$portKey]) : port $port still in use"
    } else {
        Write-Host "$($ports[$portKey]) : port $port released"
    }
}
