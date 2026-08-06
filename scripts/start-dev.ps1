param()

$root = Split-Path -Parent $PSScriptRoot

Write-Host "Starting backend (uvicorn) on http://127.0.0.1:8000 ..."
Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory $root -WindowStyle Hidden

Write-Host "Starting frontend (vite dev) on http://127.0.0.1:5173 ..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd frontend && npm run dev" `
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

    Write-Host "Starting nginx reverse proxy on http://127.0.0.1:8080 ..."
    Start-Process -FilePath $nginxExe -ArgumentList "-p", "$root\nginx\", "-c", "nginx.conf" -WindowStyle Hidden
}

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "=== Status ==="
foreach ($port in 8000, 5173, 8080) {
    $listening = [bool](Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue)
    Write-Host "port $port : $(if ($listening) { 'UP' } else { 'DOWN' })"
}
