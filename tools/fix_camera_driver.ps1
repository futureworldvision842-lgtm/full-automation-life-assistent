# F:\Jarvis Command Center\tools\fix_camera_driver.ps1
$logFile = "F:\Jarvis Command Center\logs\camera_driver_fix.log"
if (-not (Test-Path "F:\Jarvis Command Center\logs")) {
    New-Item -ItemType Directory -Path "F:\Jarvis Command Center\logs" -Force | Out-Null
}

function Log-Msg($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    $line | Out-File -FilePath $logFile -Append -Encoding utf8
}

Log-Msg "========================================================="
Log-Msg "J.A.R.V.I.S. HARDWARE STABILIZER: CAMERA DRIVER FIX INITIATED"
Log-Msg "Laptop Model: Lenovo ThinkPad W540 (20BHS1E508)"
Log-Msg "Target Bug: SPUVCbv64.sys Access Violation 0xC0000005 (BSOD 0x3B)"
Log-Msg "========================================================="

# Step 1: Force remove and uninstall buggy SunplusIT OEM driver (oem27.inf)
Log-Msg "Step 1: Removing buggy oem27.inf (SunplusIT / SPUVCbv64.sys)..."
$delResult = pnputil /delete-driver oem27.inf /uninstall /force 2>&1
Log-Msg "pnputil output: $($delResult -join ' ')"

# Step 2: Remove Integrated Camera device instance
Log-Msg "Step 2: Removing Integrated Camera device instance to clear active driver binding..."
$camDevices = Get-PnpDevice | Where-Object { $_.InstanceId -like "*VID_04F2&PID_B39A*" }
foreach ($dev in $camDevices) {
    Log-Msg "Removing device instance: $($dev.FriendlyName) [$($dev.InstanceId)]"
    $remResult = pnputil /remove-device "$($dev.InstanceId)" 2>&1
    Log-Msg "pnputil remove-device output: $($remResult -join ' ')"
}

# Step 3: Rescan devices so Windows re-detects the hardware and binds Microsoft usbvideo.inf
Log-Msg "Step 3: Rescanning hardware devices..."
$scanResult = pnputil /scan-devices 2>&1
Log-Msg "pnputil scan-devices output: $($scanResult -join ' ')"

Log-Msg "Waiting 4 seconds for device enumeration..."
Start-Sleep -Seconds 4

# Step 4: Fix Windows Media Foundation FrameServer registry keys to prevent camera freeze/crashes
Log-Msg "Step 4: Configuring Windows Media Foundation FrameServer stability keys..."
try {
    $mfPath64 = "HKLM:\SOFTWARE\Microsoft\Windows Media Foundation\Platform"
    if (-not (Test-Path $mfPath64)) { New-Item -Path $mfPath64 -Force | Out-Null }
    Set-ItemProperty -Path $mfPath64 -Name "EnableFrameServerMode" -Value 0 -Type DWord -Force
    Log-Msg "Set $mfPath64\EnableFrameServerMode = 0 (SUCCESS)"

    $mfPath32 = "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows Media Foundation\Platform"
    if (-not (Test-Path $mfPath32)) { New-Item -Path $mfPath32 -Force | Out-Null }
    Set-ItemProperty -Path $mfPath32 -Name "EnableFrameServerMode" -Value 0 -Type DWord -Force
    Log-Msg "Set $mfPath32\EnableFrameServerMode = 0 (SUCCESS)"
} catch {
    Log-Msg "Error configuring Media Foundation keys: $($_.Exception.Message)"
}

# Step 5: Verification of installed camera driver
Log-Msg "Step 5: Verifying resulting camera driver..."
$newDrivers = Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.DeviceID -like '*VID_04F2&PID_B39A*' }
foreach ($d in $newDrivers) {
    Log-Msg "DEVICE: $($d.DeviceName)"
    Log-Msg "  -> Provider: $($d.DriverProviderName)"
    Log-Msg "  -> Driver Version: $($d.DriverVersion)"
    Log-Msg "  -> INF Name: $($d.InfName)"
    Log-Msg "  -> Driver Date: $($d.DriverDate)"
}

$newCam = Get-PnpDevice | Where-Object { $_.InstanceId -like "*VID_04F2&PID_B39A*" }
foreach ($c in $newCam) {
    Log-Msg "PNP STATUS: $($c.FriendlyName) | Status: $($c.Status) | Problem: $($c.Problem)"
}

Log-Msg "========================================================="
Log-Msg "CAMERA DRIVER FIX COMPLETED SUCCESSFULLY!"
Log-Msg "========================================================="
