param(
    [ValidateSet("Start", "Stop", "Status")]
    [string]$Action = "Status",
    [switch]$OpenDashboard
)

$ErrorActionPreference = "Stop"

$ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$RuntimeDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "runtime"))
$LogsDir = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "logs"))
$StateFile = [System.IO.Path]::GetFullPath((Join-Path $RuntimeDir "mq3_stack_state.json"))
$RootPrefix = $ProjectRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$ConfigPath = Join-Path $ProjectRoot "config.json"
$DashboardPort = 5050
try {
    $portConfig = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $configuredPort = [int]$portConfig.bot.dashboard_port
    if ($configuredPort -ge 1024 -and $configuredPort -le 65535) {
        $DashboardPort = $configuredPort
    }
}
catch {
    throw "Cannot read a valid bot.dashboard_port from config.json."
}
$DashboardBaseUrl = "http://127.0.0.1:$DashboardPort"

foreach ($targetPath in @($RuntimeDir, $LogsDir, $StateFile)) {
    if (-not $targetPath.StartsWith($RootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Managed path escaped the MQ3 workspace: $targetPath"
    }
}

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

function Read-StackState {
    if (-not (Test-Path -LiteralPath $StateFile)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
    }
    catch {
        Write-Warning "Runtime state is unreadable; treating it as stale."
        return $null
    }
}

function Write-StackState([hashtable]$State) {
    $State.updated_at = [DateTime]::UtcNow.ToString("o")
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $StateFile -Encoding UTF8
}

function Get-ValidatedManagedProcess($Entry) {
    if ($null -eq $Entry -or $null -eq $Entry.pid) {
        return $null
    }
    $processId = [int]$Entry.pid
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($null -eq $processInfo) {
        return $null
    }
    $expected = [string]$Entry.expected_command
    $expectedBase = [System.IO.Path]::GetFileName($expected)
    $cmdLine = [string]$processInfo.CommandLine
    if (-not $expected -or ($cmdLine -notlike "*$expected*" -and $cmdLine -notlike "*$expectedBase*")) {
        Write-Warning "PID $processId exists but does not match managed command '$expected'; it will not be touched."
        return $null
    }
    return $processInfo
}

function Test-HttpReady([string]$Uri) {
    try {
        $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-HttpReady([string]$Uri, [int]$TimeoutSeconds = 60) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-HttpReady $Uri) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Assert-PortAvailable([int]$Port) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $listener) {
        throw "Port $Port is already owned by unmanaged PID $($listener.OwningProcess). Stop that process or use MQ3 Stop first."
    }
}

function Get-ConflictingBotProcesses([int[]]$AllowedProcessIds = @()) {
    $projectPattern = [regex]::Escape($ProjectRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar))
    return @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $command = [string]$_.CommandLine
        # Only police processes launched from this exact workspace.  Relative
        # commands owned by another IDE/workspace are not safe targets for MQ3.
        $isMq3Command = $command -match "$projectPattern[/\\](?:run\.py|run_jarvis\.py|whatsapp_bridge[/\\]server\.js)"
        $isMq3Command -and $_.ProcessId -notin $AllowedProcessIds
    })
}

function Assert-NoConflictingBotProcesses([int[]]$AllowedProcessIds = @()) {
    $conflicts = Get-ConflictingBotProcesses $AllowedProcessIds
    if ($conflicts.Count -gt 0) {
        $summary = ($conflicts | ForEach-Object { "PID $($_.ProcessId): $($_.CommandLine)" }) -join '; '
        throw "Unmanaged MQ3/Jarvis process conflict detected. $summary"
    }
}

function Get-SafeStartMode {
    $configPath = Join-Path $ProjectRoot "config.json"
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
    if ($config.execution.live_enabled -eq $true) {
        throw "Managed Desktop Start refused: real-money execution.live_enabled must remain false."
    }
    $mode = [string]$config.execution.default_mode
    if ($mode -notin @("paper", "broker_demo")) {
        throw "Managed Desktop Start refused: execution.default_mode must be 'paper' or 'broker_demo'."
    }
    if ($mode -eq "broker_demo" -and $config.execution.demo_telemetry_enabled -ne $true) {
        throw "Managed Desktop Start refused: broker_demo requires demo_telemetry_enabled=true."
    }
    if ($config.execution.demo_order_execution_enabled -eq $true) {
        throw "Managed Desktop Start refused: unattended broker-demo order execution must remain disabled."
    }
    if ($config.execution.enable_unattended_routine_broadcasts -eq $true) {
        throw "Safe Desktop Start refused: unattended routine broadcasts must remain disabled."
    }
    return $mode
}

function New-EphemeralBridgeToken {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Show-StackStatus {
    $state = Read-StackState
    Write-Host ""
    Write-Host "MQ3 + JARVIS MANAGED STACK" -ForegroundColor Cyan
    $displayMode = if ($null -ne $state -and $state.mode) { [string]$state.mode } else { "NOT STARTED" }
    Write-Host "Mode: $displayMode (real-money funded execution locked)" -ForegroundColor Yellow
    if ($null -eq $state) {
        Write-Host "State: NOT STARTED"
    }
    else {
        Write-Host "State: $($state.status)"
        foreach ($serviceName in @("whatsapp_bridge", "dashboard", "jarvis")) {
            $entry = $state.services.$serviceName
            $managed = Get-ValidatedManagedProcess $entry
            $processText = if ($null -ne $managed) { "RUNNING PID $($managed.ProcessId)" } else { "STOPPED" }
            Write-Host ("{0,-18} {1}" -f $serviceName, $processText)
        }
    }
    Write-Host ("Dashboard health: {0}" -f $(if (Test-HttpReady "$DashboardBaseUrl/api/readiness") { "READY" } else { "DOWN" }))
    Write-Host ("WhatsApp bridge: {0}" -f $(if (Test-HttpReady "http://127.0.0.1:3001/status") { "HTTP READY (pairing may still be required)" } else { "DOWN" }))
    Write-Host "Dashboard: $DashboardBaseUrl/"
    Write-Host "WhatsApp QR: $DashboardBaseUrl/whatsapp"
    Write-Host "State file: $StateFile"
}

function Stop-ManagedStack {
    $state = Read-StackState
    if ($null -eq $state) {
        Write-Host "No managed MQ3 state exists; no unknown processes were stopped." -ForegroundColor Yellow
        return
    }

    foreach ($serviceName in @("jarvis", "dashboard", "whatsapp_bridge")) {
        $entry = $state.services.$serviceName
        $managed = Get-ValidatedManagedProcess $entry
        if ($null -ne $managed) {
            Stop-Process -Id ([int]$managed.ProcessId) -Force
            Write-Host "Stopped $serviceName (PID $($managed.ProcessId))."
        }
    }

    Write-StackState @{
        schema_version = 1
        status = "STOPPED"
        mode = "PAPER"
        project_root = $ProjectRoot
        services = @{}
    }
    Write-Host "MQ3 managed stack is stopped."
}

function Start-ManagedStack {
    $startMode = Get-SafeStartMode

    $existingState = Read-StackState
    if ($null -ne $existingState -and $existingState.status -eq "RUNNING") {
        $dashboardProcess = Get-ValidatedManagedProcess $existingState.services.dashboard
        $jarvisProcess = Get-ValidatedManagedProcess $existingState.services.jarvis
        $bridgeProcess = Get-ValidatedManagedProcess $existingState.services.whatsapp_bridge
        if ($null -ne $dashboardProcess -and $null -ne $jarvisProcess -and $null -ne $bridgeProcess) {
            Write-Host "MQ3 managed stack is already running." -ForegroundColor Green
            Show-StackStatus
            if ($OpenDashboard) {
                Start-Process "$DashboardBaseUrl/"
            }
            return
        }
        Write-Warning "Previous stack state is stale; rebuilding it."
    }

    Assert-PortAvailable $DashboardPort
    Assert-PortAvailable 3001
    Assert-NoConflictingBotProcesses

    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    $nodePath = (Get-Command node -ErrorAction Stop).Source
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $startedProcesses = New-Object System.Collections.Generic.List[System.Diagnostics.Process]

    if ($startMode -eq "paper") {
        $env:MQ3_FORCE_PAPER = "1"
        Remove-Item Env:MQ3_FORCE_BROKER_DEMO -ErrorAction SilentlyContinue
    }
    else {
        Remove-Item Env:MQ3_FORCE_PAPER -ErrorAction SilentlyContinue
        $env:MQ3_FORCE_BROKER_DEMO = "1"
    }
    Remove-Item Env:MQ3_LIVE_TRADING_CONFIRMATION -ErrorAction SilentlyContinue
    Remove-Item Env:MQ3_DEMO_TRADING_CONFIRMATION -ErrorAction SilentlyContinue
    $env:MQ3_BRIDGE_TOKEN = New-EphemeralBridgeToken
    $tokenPath = Join-Path $RuntimeDir "bridge_token.txt"
    $env:MQ3_BRIDGE_TOKEN | Set-Content -LiteralPath $tokenPath -Encoding UTF8 -NoNewline
    $env:MQ3_DASHBOARD_BASE_URL = $DashboardBaseUrl

    try {
        $bridgeOut = Join-Path $LogsDir "stack_whatsapp_$stamp.out.log"
        $bridgeErr = Join-Path $LogsDir "stack_whatsapp_$stamp.err.log"
        $bridgeScript = Join-Path $ProjectRoot "whatsapp_bridge\server.js"
        $bridge = Start-Process -FilePath $nodePath -ArgumentList @("`"$bridgeScript`"") -WorkingDirectory (Join-Path $ProjectRoot "whatsapp_bridge") -RedirectStandardOutput $bridgeOut -RedirectStandardError $bridgeErr -WindowStyle Hidden -PassThru
        $startedProcesses.Add($bridge)
        if (-not (Wait-HttpReady "http://127.0.0.1:3001/status" 45)) {
            throw "WhatsApp bridge did not become healthy. Inspect $bridgeErr"
        }
        if ($bridge.HasExited) {
            throw "Managed WhatsApp bridge exited while another process answered its health port. Inspect $bridgeErr"
        }

        $dashboardOut = Join-Path $LogsDir "stack_dashboard_$stamp.out.log"
        $dashboardErr = Join-Path $LogsDir "stack_dashboard_$stamp.err.log"
        $dashboardModeArg = if ($startMode -eq "broker_demo") { "--demo" } else { "--sim" }
        $dashboardScript = Join-Path $ProjectRoot "run.py"
        $dashboardArgs = @("`"$dashboardScript`"", $dashboardModeArg, "--host", "127.0.0.1", "--port", "$DashboardPort")
        $dashboard = Start-Process -FilePath $pythonPath -ArgumentList $dashboardArgs -WorkingDirectory $ProjectRoot -RedirectStandardOutput $dashboardOut -RedirectStandardError $dashboardErr -WindowStyle Hidden -PassThru
        $startedProcesses.Add($dashboard)
        if (-not (Wait-HttpReady "$DashboardBaseUrl/api/readiness" 75)) {
            throw "Dashboard/bot did not become healthy. Inspect $dashboardErr"
        }
        if ($dashboard.HasExited) {
            throw "Managed dashboard exited while another process answered its health port. Inspect $dashboardErr"
        }

        $jarvisOut = Join-Path $LogsDir "stack_jarvis_$stamp.out.log"
        $jarvisErr = Join-Path $LogsDir "stack_jarvis_$stamp.err.log"
        $jarvisScript = Join-Path $ProjectRoot "run_jarvis.py"
        $jarvisArgs = @("`"$jarvisScript`"", "--poll", "20")
        $jarvis = Start-Process -FilePath $pythonPath -ArgumentList $jarvisArgs -WorkingDirectory $ProjectRoot -RedirectStandardOutput $jarvisOut -RedirectStandardError $jarvisErr -WindowStyle Hidden -PassThru
        $startedProcesses.Add($jarvis)
        Start-Sleep -Seconds 5
        if ($jarvis.HasExited) {
            throw "Jarvis exited during startup. Inspect $jarvisErr"
        }

        Assert-NoConflictingBotProcesses @($bridge.Id, $dashboard.Id, $jarvis.Id)

        Write-StackState @{
            schema_version = 1
            status = "RUNNING"
            mode = $startMode.ToUpperInvariant()
            started_at = [DateTime]::UtcNow.ToString("o")
            project_root = $ProjectRoot
            services = @{
                whatsapp_bridge = @{ pid = $bridge.Id; expected_command = $bridgeScript; stdout = $bridgeOut; stderr = $bridgeErr; health = "http://127.0.0.1:3001/status" }
                dashboard = @{ pid = $dashboard.Id; expected_command = $dashboardScript; stdout = $dashboardOut; stderr = $dashboardErr; health = "$DashboardBaseUrl/api/readiness" }
                jarvis = @{ pid = $jarvis.Id; expected_command = $jarvisScript; stdout = $jarvisOut; stderr = $jarvisErr; health = "PROCESS_HEARTBEAT" }
            }
        }

        Write-Host "MQ3 + Jarvis managed $($startMode.ToUpperInvariant()) stack started successfully." -ForegroundColor Green
        Show-StackStatus
        if ($OpenDashboard) {
            Start-Process "$DashboardBaseUrl/"
        }
    }
    catch {
        foreach ($startedProcess in $startedProcesses) {
            if ($null -ne $startedProcess -and -not $startedProcess.HasExited) {
                Stop-Process -Id $startedProcess.Id -Force -ErrorAction SilentlyContinue
            }
        }
        Write-StackState @{
            schema_version = 1
            status = "FAILED"
            mode = $startMode.ToUpperInvariant()
            project_root = $ProjectRoot
            error = $_.Exception.Message
            services = @{}
        }
        throw
    }
}

Set-Location -LiteralPath $ProjectRoot
switch ($Action) {
    "Start" { Start-ManagedStack }
    "Stop" { Stop-ManagedStack }
    "Status" { Show-StackStatus }
}
