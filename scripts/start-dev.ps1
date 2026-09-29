param(
    [int]$BackendPort = $(if ($env:BACKEND_PORT) { [int]$env:BACKEND_PORT } else { 8000 }),
    [int]$VitePort    = $(if ($env:VITE_PORT)    { [int]$env:VITE_PORT }    else { 5173 }),
    [int]$NginxPort   = $(if ($env:NGINX_PORT)   { [int]$env:NGINX_PORT }   else { 8080 })
)

$root = Split-Path -Parent $PSScriptRoot

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
    # 설정을 생성해 기동한다 — 세 서비스 포트를 한 곳(파라미터/환경변수)에서만
    # 바꿔도 nginx가 항상 같이 맞춰지게 하기 위함.
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
