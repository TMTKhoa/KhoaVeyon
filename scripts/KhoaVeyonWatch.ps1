param(
    [string]$ListDir = 'C:\cmd',
    [string]$Out = 'C:\Users\Public\KhoaVeyonEvidence',
    [int]$RepeatSec = 10,
    [int]$MaxShots = 5,
    [int]$NotifyStudent = 0
)
# NotifyStudent=1: sau khi MAY GIAO VIEN DA NHAN anh vi pham (co bien nhan <anh>.jpg.ok do may giao vien ghi),
# hien bang thong bao cho hoc sinh biet minh vua vi pham va da duoc bao cho giao vien. Chua co bien nhan thi khong bao.
# KhoaVeyonWatch: chay trong phien dang nhap cua hoc sinh. Khi cua so tren cung la trang web khong co trong
# AllowPage.xlsx hoac ung dung khong co trong KeepAppList.xlsx thi chup man hinh (khong ghi phim go, khong ghi noi dung go).
$ErrorActionPreference = 'SilentlyContinue'
$created = $false
$mx = New-Object System.Threading.Mutex($true, 'Local\KhoaVeyonWatch', [ref]$created)
if (-not $created) { exit }
New-Item -ItemType Directory -Path $Out -Force | Out-Null
$stopFile = Join-Path $Out 'stop.flag'
# Thu muc nay co the bi khoa khong cho hoc sinh xoa file (chong xoa bang chung), nen script KHONG tu xoa gi o day.
# Lenh dung: may giao vien ghi/cham stop.flag. Chi coi la "dung" neu stop.flag moi hon luc script bat dau,
# nhu vay stop.flag cu con sot lai khong lam lan bat sau tu thoat ngay.
$startTime = Get-Date
function StopRequested {
    if (-not (Test-Path -LiteralPath $stopFile)) { return $false }
    try { return (Get-Item -LiteralPath $stopFile).LastWriteTime -ge $startTime } catch { return $true }
}
$pc = $env:COMPUTERNAME; $user = $env:USERNAME
$csv = Join-Path $Out 'evidence.csv'
$wlog = Join-Path $Out 'watch.log'
function Log($m) { try { Add-Content -LiteralPath $wlog -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $m) } catch {} }
Add-Type -AssemblyName System.Windows.Forms, System.Drawing, UIAutomationClient, UIAutomationTypes
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class KvW {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
'@
[void][KvW]::SetProcessDPIAware()

function Read-ColumnA($file) {
    $out = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path -LiteralPath $file)) { Log "File not found: $file"; return @() }
    Add-Type -AssemblyName System.IO.Compression
    $fs  = [IO.File]::Open($file, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::ReadWrite)
    $zip = New-Object IO.Compression.ZipArchive($fs, [IO.Compression.ZipArchiveMode]::Read)
    try {
        $shared = @()
        $e = $zip.GetEntry('xl/sharedStrings.xml')
        if ($e) {
            $r = New-Object IO.StreamReader($e.Open())
            $x = New-Object Xml.XmlDocument
            $x.LoadXml($r.ReadToEnd()); $r.Close()
            foreach ($si in $x.SelectNodes('//*[local-name()="si"]')) {
                $shared += (($si.SelectNodes('.//*[local-name()="t"]') | ForEach-Object { $_.InnerText }) -join '')
            }
        }
        $e = $zip.GetEntry('xl/worksheets/sheet1.xml')
        if (-not $e) {
            $e = $zip.Entries | Where-Object { $_.FullName -like 'xl/worksheets/sheet*.xml' } | Sort-Object FullName | Select-Object -First 1
        }
        if (-not $e) { Log "No worksheet found in $file"; return @() }
        $r = New-Object IO.StreamReader($e.Open())
        $x = New-Object Xml.XmlDocument
        $x.LoadXml($r.ReadToEnd()); $r.Close()
        foreach ($c in $x.SelectNodes('//*[local-name()="c"]')) {
            if ($c.GetAttribute('r') -notmatch '^A\d+$') { continue }
            $t = $c.GetAttribute('t'); $val = $null
            if ($t -eq 's') {
                $v = $c.SelectSingleNode('*[local-name()="v"]')
                if ($v) { $val = $shared[[int]$v.InnerText] }
            } elseif ($t -eq 'inlineStr') {
                $val = ($c.SelectNodes('.//*[local-name()="t"]') | ForEach-Object { $_.InnerText }) -join ''
            } else {
                $v = $c.SelectSingleNode('*[local-name()="v"]')
                if ($v) { $val = $v.InnerText }
            }
            if ($val) { $out.Add($val.Trim()) }
        }
    } finally { $zip.Dispose(); $fs.Dispose() }
    return $out.ToArray()
}

$browsers = @('chrome','msedge','firefox','brave','opera','coccoc','vivaldi')
$protect = @('explorer','cmd','conhost','powershell','pwsh','veyon-server','veyon-worker','veyon-service','veyon-master',
             'applicationframehost','shellexperiencehost','startmenuexperiencehost','searchhost','textinputhost',
             'systemsettings','sihost','ctfmon','dwm','lockapp','searchapp')
$allowDomains = @(); $keepNames = @(); $keepPaths = @()
$aiDomains = @(); $aiApps = @('chatgpt','claude','copilot','perplexity','deepseek')
function Load-Lists {
    $d1 = @(); $n1 = @(); $p1 = @()
    foreach ($i in @(Read-ColumnA (Join-Path $ListDir 'AllowPage.xlsx'))) {
        $d = (($i.ToLower() -replace '^[a-z]+://', '') -replace '[/?#:].*$', '') -replace '^www\.', ''
        if ($d -match '^[a-z0-9-]+(\.[a-z0-9-]+)+$') { $d1 += $d }
    }
    foreach ($k in @(Read-ColumnA (Join-Path $ListDir 'KeepAppList.xlsx'))) {
        $k = [Environment]::ExpandEnvironmentVariables($k).Trim('"')
        if ($k -match '\\') { $p1 += $k.TrimEnd('\') }
        elseif ($k) { $n1 += ($k -replace '\.exe$', '').ToLower() }
    }
    $script:allowDomains = $d1; $script:keepNames = $n1; $script:keepPaths = $p1
    # BlockAIList.xlsx: trang AI (chi lay dong la ten mien, bo qua dong co duong dan)
    $a1 = @()
    foreach ($i in @(Read-ColumnA (Join-Path $ListDir 'BlockAIList.xlsx'))) {
        $s = (([string]$i).ToLower().Trim() -replace '^[a-z]+://', '') -replace '[?#].*$', ''
        $s = $s.TrimEnd('/') -replace '^www\.', ''
        if ($s -match '^[a-z0-9-]+(\.[a-z0-9-]+)+$') { $a1 += $s }
    }
    $script:aiDomains = $a1
}
function Site-IsAi($h) {
    foreach ($d in $aiDomains) { if ($h -eq $d -or $h.EndsWith('.' + $d)) { return $true } }
    return $false
}
function Site-Allowed($h) {
    foreach ($d in $allowDomains) { if ($h -eq $d -or $h.EndsWith('.' + $d)) { return $true } }
    return $false
}
function App-Allowed($n, $path) {
    if ($keepNames -contains $n) { return $true }
    if ($path) { foreach ($kp in $keepPaths) { if ($path -like "$kp*") { return $true } } }
    return $false
}
# Tra ve ten mien dang mo, '' neu la trang noi bo (newtab...), $null neu khong doc duoc thanh dia chi
function Get-BrowserHost($hwnd) {
    try {
        $root = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
        $cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
        foreach ($e in $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)) {
            $vp = $null
            if ($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$vp)) {
                $v = ([string]$vp.Current.Value).Trim().ToLower()
                if ($v -match '^(chrome|edge|about|brave|opera|vivaldi)://') { return '' }
                if ($v -match '^(https?://)?([a-z0-9-]+\.)+[a-z0-9-]{2,}(:\d+)?([/?#].*)?$') {
                    return (($v -replace '^[a-z]+://', '') -replace '[/?#:].*$', '') -replace '^www\.', ''
                }
            }
        }
    } catch {}
    return $null
}
# Nhat ky 5 phut gan nhat (ung dung / tieu de cua so dang o truoc), di kem moi anh vi pham de giao vien biet em vua lam gi. Khong ghi phim go.
$hist = New-Object System.Collections.ArrayList
function Note-Active($proc, $title) {
    $now = Get-Date
    if ($hist.Count -gt 0 -and $hist[$hist.Count - 1].p -eq $proc -and $hist[$hist.Count - 1].w -eq $title) { $hist[$hist.Count - 1].e = $now }
    else { [void]$hist.Add([pscustomobject]@{ p = $proc; w = $title; s = $now; e = $now }) }
    while ($hist.Count -gt 0 -and ($now - $hist[0].e).TotalSeconds -gt 300) { $hist.RemoveAt(0) }
    if ($hist.Count -gt 200) { $hist.RemoveRange(0, $hist.Count - 200) }
}
function Recent-Log {
    $out = @()
    $from = $hist.Count - 30; if ($from -lt 0) { $from = 0 }
    for ($i = $from; $i -lt $hist.Count; $i++) {
        $x = $hist[$i]
        $w = [string]$x.w; if ($w.Length -gt 100) { $w = $w.Substring(0, 100) }
        $out += [ordered]@{ p = $x.p; w = $w; t = $x.s.ToString('HH:mm:ss'); d = [int][Math]::Max(1, ($x.e - $x.s).TotalSeconds) }
    }
    return ,$out
}
# Bao NGAY cho may giao vien (khong cho den lan hoi tiep theo): tha mot file nho vao hop thu di cua tro ly hoc sinh, dich vu gui trong ~2 giay.
function Push-Signal($kind, $name) {
    try {
        $ob = 'C:\ProgramData\KhoaVeyon\outbox'
        if (Test-Path -LiteralPath $ob) {
            $f = Join-Path $ob ('viol-' + [DateTime]::UtcNow.Ticks + '.json')
            [IO.File]::WriteAllText($f, (@{ t = 'viol'; type = $kind; name = $name } | ConvertTo-Json -Compress), (New-Object Text.UTF8Encoding($false)))
        }
    } catch {}
}
function Take-Shot($kind, $name, $title) {
    try {
        $now = Get-Date
        $safe = ($name -replace '[^a-z0-9.-]', '_')
        $file = Join-Path $Out ('{0}_{1}_{2}_{3}.jpg' -f $pc, $now.ToString('yyyyMMdd-HHmmss'), $kind, $safe)
        $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
        $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
        $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Jpeg)
        $g.Dispose(); $bmp.Dispose()
        # File .json di kem anh: may giao vien doc file nay de biet ten may, noi dung vi pham, ngay gio (ghi xong anh moi ghi json)
        $meta = [ordered]@{ pc = $pc; user = $user; type = $kind; name = $name; window = $title; date = $now.ToString('yyyy-MM-dd'); time = $now.ToString('HH:mm:ss'); file = (Split-Path $file -Leaf); recent = (Recent-Log) }
        $jf = [IO.Path]::ChangeExtension($file, '.json')
        # Ghi thang file .json (khong dung .tmp + doi ten, vi doi ten can quyen xoa ma thu muc nay co the da khoa).
        # Anh luon duoc luu xong truoc, roi moi ghi .json, nen khi may giao vien thay .json thi anh da day du.
        [IO.File]::WriteAllText($jf, ($meta | ConvertTo-Json -Compress -Depth 5), (New-Object Text.UTF8Encoding($true)))
        [void]$script:unsent.Add([pscustomobject]@{ Jpg = $file; At = (Get-Date) }); $script:resendTries = 0; $script:lastResend = Get-Date
        Push-Signal $kind $name
        return $file
    } catch { Log "Shot failed: $_" }
    return $null
}

# ---------- Thong bao cho hoc sinh (chi khi NotifyStudent=1) ----------
# Bang thong bao chay trong runspace rieng (STA) de vong giam sat khong bi dung trong luc bang dang hien.
$popupCode = {
    param($head, $body, $secs)
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    $f = New-Object System.Windows.Forms.Form
    $f.FormBorderStyle = 'None'; $f.TopMost = $true; $f.ShowInTaskbar = $false; $f.StartPosition = 'Manual'
    $f.BackColor = [System.Drawing.Color]::FromArgb(183, 28, 28); $f.Padding = New-Object System.Windows.Forms.Padding(18, 14, 18, 14)
    $wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
    $f.Size = New-Object System.Drawing.Size([Math]::Min(640, $wa.Width - 40), 190)
    $f.Location = New-Object System.Drawing.Point(($wa.Left + [int](($wa.Width - $f.Width) / 2)), ($wa.Top + 24))
    $lb = New-Object System.Windows.Forms.Label
    $lb.Dock = 'Fill'; $lb.ForeColor = [System.Drawing.Color]::White; $lb.Text = $body
    $lb.Font = New-Object System.Drawing.Font('Segoe UI', 12)
    $lh = New-Object System.Windows.Forms.Label
    $lh.Dock = 'Top'; $lh.Height = 40; $lh.ForeColor = [System.Drawing.Color]::White; $lh.Text = $head
    $lh.Font = New-Object System.Drawing.Font('Segoe UI', 15, [System.Drawing.FontStyle]::Bold)
    $f.Controls.Add($lb); $f.Controls.Add($lh)
    $t = New-Object System.Windows.Forms.Timer; $t.Interval = [Math]::Max(3, $secs) * 1000
    $t.add_Tick({ $t.Stop(); $f.Close() })
    $f.add_Click({ $f.Close() }); $lb.add_Click({ $f.Close() }); $lh.add_Click({ $f.Close() })
    $f.add_Shown({ $t.Start() })
    [void]$f.ShowDialog()
    $t.Dispose(); $f.Dispose()
}
$popupPS = $null; $popupAR = $null
# Tra ve $false neu bang truoc con dang hien (goi lai o vong sau)
function Show-Notice($head, $body) {
    if ($script:popupPS) {
        if (-not $script:popupAR.IsCompleted) { return $false }
        try { [void]$script:popupPS.EndInvoke($script:popupAR) } catch {}
        try { $script:popupPS.Runspace.Dispose(); $script:popupPS.Dispose() } catch {}
        $script:popupPS = $null
    }
    try {
        $rs = [RunspaceFactory]::CreateRunspace(); $rs.ApartmentState = 'STA'; $rs.ThreadOptions = 'ReuseThread'; $rs.Open()
        $ps = [PowerShell]::Create(); $ps.Runspace = $rs
        [void]$ps.AddScript($popupCode).AddArgument($head).AddArgument($body).AddArgument(10)
        $script:popupAR = $ps.BeginInvoke(); $script:popupPS = $ps
    } catch { Log "Notice failed: $_" }
    return $true
}
function Notice-Text($kind, $name, $at) {
    $what = switch ($kind) { 'site' { "trang web không được phép: $name" } 'ai' { "công cụ AI: $name" } default { "ứng dụng không được phép: $name" } }
    return ("Bạn vừa mở $what`r`n`r`nMàn hình lúc {0} đã được chụp lại và đã gửi cho giáo viên.`r`nHãy quay lại bài học." -f $at.ToString('HH:mm:ss'))
}
$pending = New-Object System.Collections.Generic.List[object]   # anh dau tien cua moi lan vi pham, cho bien nhan
$noticeLast = @{}                                                # "loai|ten" -> lan bao gan nhat (khong bao lai trong 60 giay)
function Process-Receipts {
    foreach ($it in $pending.ToArray()) {
        $ok = $it.Jpg + '.ok'
        if (Test-Path -LiteralPath $ok) {
            $k = $it.Kind + '|' + $it.Name
            if ($noticeLast.ContainsKey($k) -and ((Get-Date) - $noticeLast[$k]).TotalSeconds -lt 60) {
                Remove-Item -LiteralPath $ok -Force; [void]$pending.Remove($it); continue
            }
            if (-not (Show-Notice 'ĐÃ GHI NHẬN VI PHẠM' (Notice-Text $it.Kind $it.Name $it.At))) { return }   # bang truoc chua tat
            $noticeLast[$k] = Get-Date
            Remove-Item -LiteralPath $ok -Force; [void]$pending.Remove($it)
            Log ("Notice shown to student: {0} {1}" -f $it.Kind, $it.Name)
            return   # moi vong toi da mot bang
        } elseif (((Get-Date) - $it.At).TotalMinutes -ge 10) {
            [void]$pending.Remove($it)   # may giao vien khong nhan (chuong trinh dang tat...): khong bao, vi chua gui that
        }
    }
}
# Bien nhan cua cac anh khong cho bao (anh chup lai, hoac tu lan chay truoc): xoa cho gon
function Clear-OldReceipts {
    $want = @($pending | ForEach-Object { [IO.Path]::GetFileName($_.Jpg) + '.ok' })
    Get-ChildItem -LiteralPath $Out -Filter '*.jpg.ok' -File | Where-Object { $want -notcontains $_.Name -and ((Get-Date) - $_.LastWriteTime).TotalSeconds -ge 30 } |
        Remove-Item -Force
}

# Anh da chup nhung may giao vien chua lay: file .jpg van con trong thu muc (may giao vien lay xong se xoa). Con file thi cu bao lai
# (sau 4 giay, roi 10, roi 30 giay mot lan, toi da 10 phut) de anh toi tay giao vien ngay ca khi tin hieu dau bi mat. Moi lan chi gui MOT tin hieu cho ca danh sach.
$unsent = New-Object System.Collections.Generic.List[object]
$resendTries = 0; $lastResend = [datetime]::MinValue
function Resend-Unsent {
    for ($i = $unsent.Count - 1; $i -ge 0; $i--) {
        $it = $unsent[$i]
        if (-not (Test-Path -LiteralPath $it.Jpg) -or ((Get-Date) - $it.At).TotalSeconds -ge 600) { $unsent.RemoveAt($i) }
    }
    if ($unsent.Count -eq 0) { $script:resendTries = 0; return }
    $wait = 30; if ($script:resendTries -lt 3) { $wait = 4 } elseif ($script:resendTries -lt 8) { $wait = 10 }
    if (((Get-Date) - $script:lastResend).TotalSeconds -ge $wait) { Push-Signal 'retry' ''; $script:lastResend = Get-Date; $script:resendTries++ }
}

Load-Lists
Log ("Watch STARTED. Sites allowed: {0}; apps allowed: {1} names, {2} paths; AI sites: {3}" -f $allowDomains.Count, $keepNames.Count, $keepPaths.Count, $aiDomains.Count)
$lastHello = [datetime]::MinValue
$script:siteKey = ''; $script:siteVal = $null; $script:siteAt = [datetime]::MinValue
$lastLoad = Get-Date; $curKey = ''; $shots = 0; $lastShot = [datetime]::MinValue
$aliveFile = Join-Path $Out 'alive.txt'; $lastBeat = [datetime]::MinValue   # tín hiệu "đang chạy" để máy giáo viên biết giám sát còn sống
while (-not (StopRequested)) {
    try {
        if (((Get-Date) - $lastLoad).TotalSeconds -ge 30) { Load-Lists; $lastLoad = Get-Date; if ($NotifyStudent) { Clear-OldReceipts } }
        $h = [KvW]::GetForegroundWindow()
        $sb = New-Object System.Text.StringBuilder 256
        [void][KvW]::GetWindowText($h, $sb, 256)
        $title = $sb.ToString()
        $procId = 0
        [void][KvW]::GetWindowThreadProcessId($h, [ref]$procId)
        $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $n = ''; $path = $null
        if ($p) { $n = $p.ProcessName.ToLower(); try { $path = $p.Path } catch {} }
        if ($n -and ($n -ne 'idle')) { Note-Active $n $title }
        $kind = ''; $name = ''
        if ($n -and ($protect -notcontains $n) -and ($n -ne 'idle')) {
            if ($browsers -contains $n) {
                # doc thanh dia chi (UI Automation) ton thoi gian: chi doc lai khi doi cua so / tieu de, hoac sau 3 giay
                $bk = "$h|$title"
                if ($bk -ne $script:siteKey -or ((Get-Date) - $script:siteAt).TotalSeconds -ge 3) { $script:siteVal = Get-BrowserHost $h; $script:siteKey = $bk; $script:siteAt = Get-Date }
                $site = $script:siteVal
                if ($site -and (Site-IsAi $site)) { $kind = 'ai'; $name = $site }
                elseif ($site -and $allowDomains.Count -gt 0 -and -not (Site-Allowed $site)) { $kind = 'site'; $name = $site }
            } elseif ($aiApps -contains $n) {
                $kind = 'ai'; $name = $n
            } elseif (($keepNames.Count + $keepPaths.Count) -gt 0 -and -not (App-Allowed $n $path)) {
                $kind = 'app'; $name = $n
            }
        }
        if ($kind) {
            $key = "$kind|$name"
            if ($key -ne $curKey) { $curKey = $key; $shots = 0; $lastShot = [datetime]::MinValue }
            # anh dau chup ngay khi phat hien; anh thu hai sau 2 giay (luc dau trang co the chua tai xong, hoac hoc sinh dong tab rat nhanh), cac anh sau cach nhau RepeatSec
            $gap = $RepeatSec; if ($shots -eq 1) { $gap = [Math]::Min(2, $RepeatSec) }
            if ($shots -lt $MaxShots -and ((Get-Date) - $lastShot).TotalSeconds -ge $gap) {
                $shotFile = Take-Shot $kind $name $title
                if ($NotifyStudent -and $shotFile -and $shots -eq 0) {   # chi anh dau tien cua moi lan vi pham moi duoc bao
                    $pending.Add([pscustomobject]@{ Jpg = $shotFile; Kind = $kind; Name = $name; At = (Get-Date) })
                }
                $shots++; $lastShot = Get-Date
            }
        } else { $curKey = '' }
        if ($NotifyStudent -and $pending.Count -gt 0) { Process-Receipts }
        Resend-Unsent
    } catch { Log "Loop error: $_" }
    # "hello": bao may giao vien biet script nay tu day anh ve ngay khi co vi pham, nen may giao vien khong can quet lien tuc qua mang
    if (((Get-Date) - $lastHello).TotalSeconds -ge 240) { Push-Signal 'hello' ''; $lastHello = Get-Date }
    if (((Get-Date) - $lastBeat).TotalSeconds -ge 10) { try { Set-Content -LiteralPath $aliveFile -Value (Get-Date -Format s) } catch {}; $lastBeat = Get-Date }
    Start-Sleep -Milliseconds 300
}
Log 'Watch STOPPED'
