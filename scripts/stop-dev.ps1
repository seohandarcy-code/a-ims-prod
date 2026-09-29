param(
    [int]$BackendPort = $(if ($env:BACKEND_PORT) { [int]$env:BACKEND_PORT } else { 8000 }),
    [int]$VitePort    = $(if ($env:VITE_PORT)    { [int]$env:VITE_PORT }    else { 5173 }),
    [int]$NginxPort   = $(if ($env:NGINX_PORT)   { [int]$env:NGINX_PORT }   else { 8080 })
)

$ports = [ordered]@{ "$BackendPort" = "backend (uvicorn)"; "$VitePort" = "frontend (vite)"; "$NginxPort" = "nginx" }

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
