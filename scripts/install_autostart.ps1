# Registers a Windows Scheduled Task that starts the Van Udyan backend (port 8000) and
# dashboard (port 5173) in the background every time the current user logs in.
# Run:        powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1
# Remove:     powershell -ExecutionPolicy Bypass -File scripts\install_autostart.ps1 -Uninstall

param([switch]$Uninstall)

$TaskName = "VanUdyanPlatform"
$Root = Split-Path -Parent $PSScriptRoot

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Removed scheduled task '$TaskName'. Running servers keep running until you log off or stop them."
    return
}

$Pythonw = Join-Path $Root "backend\venv\Scripts\pythonw.exe"
$Supervisor = Join-Path $Root "scripts\run_services.py"
if (-not (Test-Path $Pythonw)) { throw "Virtual environment not found: $Pythonw" }

$User = "$env:USERDOMAIN\$env:USERNAME"
$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument "`"$Supervisor`"" -WorkingDirectory $Root
# Short delay so PostgreSQL and the network are ready after boot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $User
$Trigger.Delay = "PT30S"
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable -MultipleInstances IgnoreNew
$Principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Principal $Principal -Description "Starts the Van Udyan Biodiversity Platform (backend :8000, dashboard :5173) at logon." -Force | Out-Null

Write-Output "Registered scheduled task '$TaskName' for $User (runs at logon)."
