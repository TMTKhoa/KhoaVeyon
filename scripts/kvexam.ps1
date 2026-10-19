param([string]$Mode = 'on', [string]$What = 'usb,print')
# KhoaVeyonExam: chay bang SYSTEM trong gio thi. Mode on = khoa, Mode off = tra lai nhu cu. What: usb, print (cach nhau bang dau phay).
$ErrorActionPreference = 'SilentlyContinue'
$items = @($What -split '[,\s]+' | Where-Object { $_ } | ForEach-Object { $_.Trim().ToLower() })
$stateDir = Join-Path $env:ProgramData 'KhoaVeyon'
if (-not (Test-Path -LiteralPath $stateDir)) { New-Item -ItemType Directory -Path $stateDir -Force | Out-Null }

if ($items -contains 'usb') {
    # Chinh sach "Removable Disks: Deny read/write access" (o USB, the nho). Co hieu luc voi lan truy cap moi, khong can khoi dong lai.
    $rem = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\RemovableStorageDevices\{53f5630d-b6bf-11d0-94f2-00a0c91efb8b}'
    if ($Mode -eq 'on') {
        if (-not (Test-Path -LiteralPath $rem)) { New-Item -Path $rem -Force | Out-Null }
        New-ItemProperty -Path $rem -Name 'Deny_Read'  -Value 1 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $rem -Name 'Deny_Write' -Value 1 -PropertyType DWord -Force | Out-Null
    } else {
        Remove-ItemProperty -Path $rem -Name 'Deny_Read'
        Remove-ItemProperty -Path $rem -Name 'Deny_Write'
    }
}

if ($items -contains 'print') {
    # Tat dich vu in (Print Spooler). Luu kieu khoi dong cu de tra lai dung nhu truoc.
    $saved = Join-Path $stateDir 'spooler_start.txt'
    if ($Mode -eq 'on') {
        if (-not (Test-Path -LiteralPath $saved)) {
            $cur = (Get-Service -Name Spooler).StartType
            if ($cur) { Set-Content -LiteralPath $saved -Value ([string]$cur) }
        }
        Set-Service -Name Spooler -StartupType Disabled
        Stop-Service -Name Spooler -Force
    } else {
        $type = 'Automatic'
        if (Test-Path -LiteralPath $saved) {
            $t = (Get-Content -LiteralPath $saved | Select-Object -First 1)
            if ($t -in @('Automatic', 'Manual', 'Boot', 'System')) { $type = $t }
            Remove-Item -LiteralPath $saved
        }
        Set-Service -Name Spooler -StartupType $type
        Start-Service -Name Spooler
    }
}
exit 0
