param([string]$Json)
# KhoaVeyonSeat: chay trong phien dang nhap cua hoc sinh. Hien bang "May nay cua ai" (noi dung doc tu file json UTF-8).
# Dang chay roi thi ban moi chi can ghi lai file json, ban cu tu doc lai va doi noi dung.
$ErrorActionPreference = 'SilentlyContinue'
$created = $false
$mx = New-Object System.Threading.Mutex($true, 'Local\KhoaVeyonSeat', [ref]$created)
if (-not $created) { exit }
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public class KvDpiSeat { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }'
[KvDpiSeat]::SetProcessDPIAware() | Out-Null
function Read-Cfg {
    try { return (Get-Content -LiteralPath $Json -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}
$script:stamp = ''
$script:mode = 'big'
$script:since = Get-Date
$script:cfg = $null
$form = New-Object System.Windows.Forms.Form
$form.FormBorderStyle = 'None'
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.StartPosition = 'Manual'
$form.BackColor = [System.Drawing.Color]::FromArgb(30, 64, 175)
$l3 = New-Object System.Windows.Forms.Label
$l3.Dock = 'Bottom'; $l3.TextAlign = 'MiddleCenter'; $l3.ForeColor = [System.Drawing.Color]::FromArgb(219, 234, 254)
$l1 = New-Object System.Windows.Forms.Label
$l1.Dock = 'Top'; $l1.TextAlign = 'MiddleCenter'; $l1.ForeColor = [System.Drawing.Color]::FromArgb(219, 234, 254)
$l2 = New-Object System.Windows.Forms.Label
$l2.Dock = 'Fill'; $l2.TextAlign = 'MiddleCenter'; $l2.ForeColor = [System.Drawing.Color]::White
$form.Controls.Add($l2); $form.Controls.Add($l1); $form.Controls.Add($l3)
function Set-Layout {
    $wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
    if ($script:mode -eq 'big') {
        $form.Size = New-Object System.Drawing.Size(820, 320)
        $form.Location = New-Object System.Drawing.Point(($wa.Left + [int](($wa.Width - 820) / 2)), ($wa.Top + [int](($wa.Height - 320) / 2)))
        $l1.Height = 70; $l3.Height = 70
        $l1.Font = New-Object System.Drawing.Font('Segoe UI', 20)
        $l3.Font = New-Object System.Drawing.Font('Segoe UI', 18)
        $sz = 44; if ($l2.Text.Length -gt 22) { $sz = 30 }; if ($l2.Text.Length -gt 60) { $sz = 22 }
        $l2.Font = New-Object System.Drawing.Font('Segoe UI', $sz, [System.Drawing.FontStyle]::Bold)
    } else {
        $form.Size = New-Object System.Drawing.Size(300, 92)
        $form.Location = New-Object System.Drawing.Point(($wa.Right - 316), ($wa.Top + 12))
        $l1.Height = 22; $l3.Height = 20
        $l1.Font = New-Object System.Drawing.Font('Segoe UI', 8)
        $l3.Font = New-Object System.Drawing.Font('Segoe UI', 8)
        $sz = 15; if ($l2.Text.Length -gt 20) { $sz = 11 }
        $l2.Font = New-Object System.Drawing.Font('Segoe UI', $sz, [System.Drawing.FontStyle]::Bold)
    }
}
function Dismiss {
    if ($script:mode -eq 'big' -and $script:cfg -and $script:cfg.keep) { $script:mode = 'label'; Set-Layout } else { if ($script:mode -eq 'big') { $form.Close() } }
}
$form.Add_Click({ Dismiss }); $l1.Add_Click({ Dismiss }); $l2.Add_Click({ Dismiss }); $l3.Add_Click({ Dismiss })
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 1500
$timer.Add_Tick({
    $c = Read-Cfg
    if ($c -eq $null) { return }
    if ($c.clear) { $form.Close(); return }
    if ($c.stamp -ne $script:stamp) {
        $script:stamp = $c.stamp; $script:cfg = $c
        $l1.Text = [string]$c.title; $l2.Text = [string]$c.name; $l3.Text = [string]$c.detail
        $script:since = Get-Date
        if ([int]$c.seconds -gt 0) { $script:mode = 'big' } else { $script:mode = 'label' }
        Set-Layout
        $form.Show(); $form.TopMost = $true
    } elseif ($script:mode -eq 'big' -and $script:cfg) {
        if (((Get-Date) - $script:since).TotalSeconds -ge [int]$script:cfg.seconds) {
            if ($script:cfg.keep) { $script:mode = 'label'; Set-Layout } else { $form.Close() }
        }
    }
    if ($script:mode -eq 'label') { $form.TopMost = $true }
})
$form.Add_Shown({ $form.Activate() })
$form.Opacity = 0.97
$c0 = Read-Cfg
if ($c0 -eq $null -or $c0.clear) { exit }
$script:stamp = $c0.stamp; $script:cfg = $c0
$l1.Text = [string]$c0.title; $l2.Text = [string]$c0.name; $l3.Text = [string]$c0.detail
if ([int]$c0.seconds -gt 0) { $script:mode = 'big' } else { $script:mode = 'label' }
Set-Layout
$timer.Start()
[System.Windows.Forms.Application]::Run($form)
