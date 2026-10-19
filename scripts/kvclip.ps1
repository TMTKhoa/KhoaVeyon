# KhoaVeyonClip: chay trong phien dang nhap cua hoc sinh (powershell -STA). Don clipboard lien tuc de chan sao chep-dan
# trong gio thi. Dung khi file kvclip.stop xuat hien canh script nay.
$ErrorActionPreference = 'SilentlyContinue'
$created = $false
$mx = New-Object System.Threading.Mutex($true, 'Local\KhoaVeyonClip', [ref]$created)
if (-not $created) { exit }
Add-Type -AssemblyName System.Windows.Forms
$flag = Join-Path $PSScriptRoot 'kvclip.stop'
Remove-Item -LiteralPath $flag -ErrorAction SilentlyContinue
while (-not (Test-Path -LiteralPath $flag)) {
    try { [System.Windows.Forms.Clipboard]::Clear() } catch {}
    Start-Sleep -Milliseconds 400
}
Remove-Item -LiteralPath $flag -ErrorAction SilentlyContinue
