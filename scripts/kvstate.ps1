param([string]$Out = (Join-Path $PSScriptRoot 'kvstate.json'))
# KhoaVeyonState: CHI DOC trang thai hien tai cua may, khong thay doi gi. Chay bang SYSTEM, ghi ket qua ra file JSON (UTF-8).
$ErrorActionPreference = 'SilentlyContinue'
function Get-Dw($path, $name) {
    $v = (Get-ItemProperty -LiteralPath $path -Name $name -ErrorAction SilentlyContinue).$name
    return ($v -eq 1)
}
$fw = ((@(Get-NetFirewallRule -DisplayName 'KhoaVeyonBlock' -ErrorAction SilentlyContinue | Where-Object { $_.Enabled -eq 'True' })).Count -gt 0)
$users = @()
foreach ($k in @(Get-ChildItem -LiteralPath 'Registry::HKEY_USERS' -ErrorAction SilentlyContinue)) {
    $sid = $k.PSChildName
    if ($sid -notmatch '^S-1-5-21-[0-9-]+$') { continue }
    $base = "Registry::HKEY_USERS\$sid\Software\Microsoft\Windows\CurrentVersion\Policies"
    $name = $sid
    try { $name = (New-Object System.Security.Principal.SecurityIdentifier($sid)).Translate([System.Security.Principal.NTAccount]).Value } catch {}
    $users += [ordered]@{
        user        = $name
        taskmgr     = (Get-Dw "$base\System" 'DisableTaskMgr')
        restrictrun = (Get-Dw "$base\Explorer" 'RestrictRun')
        regtools    = (Get-Dw "$base\System" 'DisableRegistryTools')
    }
}
$kiosk = $false
$pf = Join-Path 'C:\cmd\log' ("lockapp_{0}.pid" -f $env:COMPUTERNAME)
if (Test-Path -LiteralPath $pf) {
    $p = Get-Content -LiteralPath $pf | Select-Object -First 1
    if ($p -and (Get-Process -Id ([int]$p) -ErrorAction SilentlyContinue)) { $kiosk = $true }
}
$res = [ordered]@{ ts = (Get-Date).ToString('s'); pc = $env:COMPUTERNAME; fw = $fw; kiosk = $kiosk; users = $users }
$json = $res | ConvertTo-Json -Depth 4
[IO.File]::WriteAllText($Out, $json, (New-Object System.Text.UTF8Encoding($false)))
