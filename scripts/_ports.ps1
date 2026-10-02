# start-dev.ps1 / stop-dev.ps1이 공유하는 포트 계산 로직.
#
# 우선순위: PowerShell 파라미터/세션 환경변수($env:BACKEND_PORT 등, 일회성
# 오버라이드용) > 각 컴포넌트의 .env 파일 값(backend/.env의 PORT,
# frontend/.env의 FRONTEND_PORT, nginx/.env의 NGINX_PORT — 평소에 쓰는 주된
# 방식) > 하드코딩 기본값(8000/5173/8080).
#
# HOST는 의도적으로 여기서 다루지 않는다 — 바인드 주소는 보안에 영향을 주므로
# .env 값 하나로 조용히 바뀌지 않게 분리해둔 기존 원칙을 그대로 따른다
# (backend/.env.example 참고). 이 파일은 포트 충돌 회피만 다룬다.

function Get-EnvFileValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Default
    )
    if (-not (Test-Path $Path)) { return $Default }

    $line = Get-Content $Path | Where-Object { $_ -match "^\s*$Key\s*=\s*(.+)$" } | Select-Object -Last 1
    if ($line -and $line -match "^\s*$Key\s*=\s*(.+?)\s*$") {
        $val = $Matches[1].Trim()
        if ($val) { return $val }
    }
    return $Default
}

function Get-DevPorts {
    param([string]$Root)

    $defaultBackendPort = Get-EnvFileValue "$Root\backend\.env" "PORT" 8000
    $defaultFrontendPort = Get-EnvFileValue "$Root\frontend\.env" "FRONTEND_PORT" 5173
    $defaultNginxPort = Get-EnvFileValue "$Root\nginx\.env" "NGINX_PORT" 8080
    $defaultNginxHttpsPort = Get-EnvFileValue "$Root\nginx\.env" "NGINX_HTTPS_PORT" 8443

    [PSCustomObject]@{
        BackendPort      = if ($env:BACKEND_PORT) { [int]$env:BACKEND_PORT } else { [int]$defaultBackendPort }
        VitePort         = if ($env:VITE_PORT) { [int]$env:VITE_PORT } else { [int]$defaultFrontendPort }
        NginxPort        = if ($env:NGINX_PORT) { [int]$env:NGINX_PORT } else { [int]$defaultNginxPort }
        NginxHttpsPort   = if ($env:NGINX_HTTPS_PORT) { [int]$env:NGINX_HTTPS_PORT } else { [int]$defaultNginxHttpsPort }
    }
}
