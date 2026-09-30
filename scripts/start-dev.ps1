param(
    [int]$BackendPort = 0,
    [int]$VitePort = 0,
    [int]$NginxPort = 0
)

$root = Split-Path -Parent $PSScriptRoot

# 포트 우선순위: 위 -BackendPort 등 명시적 파라미터(0이면 "안 줌") >
# $env:BACKEND_PORT 등 세션 환경변수 > 각 컴포넌트 .env 파일(backend/.env의
# PORT, frontend/.env의 FRONTEND_PORT, nginx/.env의 NGINX_PORT) > 하드코딩
# 기본값(8000/5173/8080). 세부 로직은 _ports.ps1 참고.
. "$PSScriptRoot\_ports.ps1"
$defaultPorts = Get-DevPorts -Root $root
if ($BackendPort -eq 0) { $BackendPort = $defaultPorts.BackendPort }
if ($VitePort -eq 0) { $VitePort = $defaultPorts.VitePort }
if ($NginxPort -eq 0) { $NginxPort = $defaultPorts.NginxPort }

Write-Host "Starting backend (uvicorn) on http://127.0.0.1:$BackendPort ..."
Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "$BackendPort" `
    -WorkingDirectory $root -WindowStyle Hidden

Write-Host "Starting frontend (vite dev) on http://127.0.0.1:$VitePort ..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd frontend && npm run dev -- --port $VitePort --strictPort" `
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
    Set-Content -Path "$root\nginx\nginx.generated.conf" -Value $generated -Encoding Ascii

    Write-Host "Starting nginx reverse proxy on http://127.0.0.1:$NginxPort ..."
    Start-Process -FilePath $nginxExe -ArgumentList "-p", "$root\nginx\", "-c", "nginx.generated.conf" -WindowStyle Hidden
}

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "=== Status ==="
foreach ($port in $BackendPort, $VitePort, $NginxPort) {
    $listening = [bool](Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue)
    Write-Host "port $port : $(if ($listening) { 'UP' } else { 'DOWN' })"
}
