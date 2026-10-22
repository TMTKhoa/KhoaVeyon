﻿﻿﻿﻿﻿﻿﻿﻿# KhoaVeyonStudent.ps1: trợ lý nhỏ trên máy học sinh (giơ tay, nộp bài, nhận tin nhắn của giáo viên).
# Dịch vụ KhoaVeyonAutoLog chạy tệp này ẩn trong phiên của học sinh, mỗi phiên một bản. Không ghi phím, không chụp màn hình.
# Dữ liệu trao đổi nằm ở %ProgramData%\KhoaVeyon:  inbox\ (giáo viên gửi tới), outbox\ (gửi về giáo viên), submit\ (bài nộp).
# Muốn tắt trợ lý trên máy này: tạo tệp %ProgramData%\KhoaVeyon\tray.off. Nhật ký lỗi: %ProgramData%\KhoaVeyon\student.log
$ErrorActionPreference = 'Stop'
$Root   = Join-Path $env:ProgramData 'KhoaVeyon'
$Inbox  = Join-Path $Root 'inbox'
$Outbox = Join-Path $Root 'outbox'
$Submit = Join-Path $Root 'submit'
$LogFile = Join-Path $Root 'student.log'
function Log([string]$m) { try { Add-Content -LiteralPath $LogFile -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $m) -Encoding UTF8 } catch {} }

try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [System.Windows.Forms.Application]::EnableVisualStyles()

    $created = $false
    $mutex = New-Object System.Threading.Mutex($true, 'Local\KhoaVeyonStudentHelper', [ref]$created)
    if (-not $created) { exit }
    foreach ($d in @($Root, $Inbox, $Outbox, $Submit)) { if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null } }

    $sid = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
    $Heartbeat = Join-Path $Root ("tray-{0}.alive" -f $sid)
    $ScriptPath = $MyInvocation.MyCommand.Path
    $script:StartStamp = (Get-Item -LiteralPath $ScriptPath).LastWriteTimeUtc.Ticks
    $script:raised = $false
    $script:blockForms = @()
    $script:blockClocks = @()
    $script:allowClose = $false
    $script:lastBeat = [DateTime]::MinValue
    $utf8 = New-Object System.Text.UTF8Encoding($false)

    # ---------- gửi sự kiện về giáo viên (dịch vụ đọc outbox rồi gửi trong vài giây) ----------
    function Send-Event($obj) {
        $json = $obj | ConvertTo-Json -Compress
        $name = ([DateTime]::UtcNow.Ticks).ToString() + '-' + (Get-Random -Maximum 99999)
        $tmp = Join-Path $Outbox ($name + '.tmp')
        [System.IO.File]::WriteAllText($tmp, $json, $utf8)
        Move-Item -LiteralPath $tmp -Destination (Join-Path $Outbox ($name + '.json')) -Force
    }

    # ---------- hộp thông báo của giáo viên ----------
    function Show-Message([string]$title, [string]$text, [int]$seconds) {
        $f = New-Object System.Windows.Forms.Form
        $f.Text = 'Thông báo từ giáo viên'
        $f.TopMost = $true
        $f.StartPosition = 'CenterScreen'
        $f.FormBorderStyle = 'FixedDialog'
        $f.MinimizeBox = $false; $f.MaximizeBox = $false
        $f.ClientSize = New-Object System.Drawing.Size(560, 270)
        $f.BackColor = [System.Drawing.Color]::White
        $lt = New-Object System.Windows.Forms.Label
        $lt.Text = $title
        $lt.Font = New-Object System.Drawing.Font('Segoe UI', 16, [System.Drawing.FontStyle]::Bold)
        $lt.ForeColor = [System.Drawing.Color]::FromArgb(30, 64, 175)
        $lt.SetBounds(20, 16, 520, 38)
        $lm = New-Object System.Windows.Forms.Label
        $lm.Text = $text
        $lm.Font = New-Object System.Drawing.Font('Segoe UI', 13)
        $lm.SetBounds(20, 62, 520, 144)
        $b = New-Object System.Windows.Forms.Button
        $b.Text = 'Đã hiểu'
        $b.Font = New-Object System.Drawing.Font('Segoe UI', 11)
        $b.SetBounds(220, 216, 120, 38)
        $b.Add_Click({ $f.Close() }.GetNewClosure())
        $f.AcceptButton = $b
        $f.Controls.AddRange(@($lt, $lm, $b))
        if ($seconds -gt 0) {
            $t = New-Object System.Windows.Forms.Timer
            $t.Interval = [Math]::Max(1000, $seconds * 1000)
            $t.Add_Tick({ $t.Stop(); $f.Close() }.GetNewClosure())
            $t.Start()
        }
        try { [System.Media.SystemSounds]::Asterisk.Play() } catch {}
        $f.Show()
        $f.Activate()
    }

    # ---------- câu đố nhanh ----------
    $script:quizForm = $null; $script:quizId = ''; $script:quizTimer = $null
    function Close-Quiz {
        if ($script:quizTimer) { try { $script:quizTimer.Stop(); $script:quizTimer.Dispose() } catch {}; $script:quizTimer = $null }
        if ($script:quizForm) { try { $script:quizForm.Close() } catch {}; $script:quizForm = $null }
    }
    function Show-Quiz($msg) {
        Close-Quiz
        $script:quizId = [string]$msg.id
        $opts = @($msg.opts)
        $f = New-Object System.Windows.Forms.Form
        $f.Text = 'Câu đố nhanh'
        $f.TopMost = $true; $f.StartPosition = 'CenterScreen'; $f.FormBorderStyle = 'FixedDialog'
        $f.MinimizeBox = $false; $f.MaximizeBox = $false; $f.ControlBox = $false
        $f.BackColor = [System.Drawing.Color]::White
        $h = 120 + 56 * $opts.Count + 40
        $f.ClientSize = New-Object System.Drawing.Size(600, $h)
        $lq = New-Object System.Windows.Forms.Label
        $lq.Text = [string]$msg.q
        $lq.Font = New-Object System.Drawing.Font('Segoe UI', 15, [System.Drawing.FontStyle]::Bold)
        $lq.ForeColor = [System.Drawing.Color]::FromArgb(30, 64, 175)
        $lq.SetBounds(20, 14, 560, 96)
        $f.Controls.Add($lq)
        $ls = New-Object System.Windows.Forms.Label
        $ls.Font = New-Object System.Drawing.Font('Segoe UI', 11)
        $ls.ForeColor = [System.Drawing.Color]::FromArgb(100, 100, 100)
        $ls.SetBounds(20, ($h - 36), 560, 26)
        $f.Controls.Add($ls)
        $btns = @()
        for ($i = 0; $i -lt $opts.Count; $i++) {
            $b = New-Object System.Windows.Forms.Button
            $b.Text = ([string][char](65 + $i)) + '.  ' + [string]$opts[$i]
            $b.Font = New-Object System.Drawing.Font('Segoe UI', 13)
            $b.TextAlign = 'MiddleLeft'
            $b.FlatStyle = 'Flat'
            $b.BackColor = [System.Drawing.Color]::FromArgb(239, 246, 255)
            $b.SetBounds(20, (116 + 56 * $i), 560, 48)
            $b.Tag = $i
            $b.Add_Click({ param($s, $e)
                $idx = [int]$s.Tag
                Send-Event @{ t = 'quiz'; id = $script:quizId; a = $idx }
                foreach ($x in $script:quizBtns) { $x.BackColor = [System.Drawing.Color]::FromArgb(239, 246, 255) }
                $s.BackColor = [System.Drawing.Color]::FromArgb(187, 247, 208)
                $script:quizLbl.Text = 'Đã gửi đáp án. Bạn có thể đổi đáp án đến khi hết giờ.'
            })
            $f.Controls.Add($b); $btns += $b
        }
        $script:quizBtns = $btns; $script:quizLbl = $ls
        $secs = [int]$msg.secs
        if ($secs -gt 0) {
            $script:quizEnd = [DateTime]::Now.AddSeconds($secs)
            $script:quizTimer = New-Object System.Windows.Forms.Timer
            $script:quizTimer.Interval = 500
            $script:quizTimer.Add_Tick({
                $left = [int][Math]::Ceiling(($script:quizEnd - [DateTime]::Now).TotalSeconds)
                if ($left -le 0) { Close-Quiz } else { if ($script:quizLbl.Text -notlike 'Đã gửi*') { $script:quizLbl.Text = 'Còn ' + $left + ' giây' } }
            })
            $script:quizTimer.Start()
        } else { $ls.Text = 'Chọn một đáp án' }
        $script:quizForm = $f
        try { [System.Media.SystemSounds]::Asterisk.Play() } catch {}
        $f.Show(); $f.Activate()
    }
    function End-Quiz($msg) {
        if ([string]$msg.id -ne $script:quizId) { return }
        Close-Quiz
        if ($msg.reveal -eq $true -and [int]$msg.correct -ge 0) {
            $mine = [int]$msg.mine
            if ($mine -lt 0) { Show-Message 'Kết quả câu đố' ('Đáp án đúng: ' + [string][char](65 + [int]$msg.correct)) 8 }
            elseif ($mine -eq [int]$msg.correct) { Show-Message 'Chính xác!' ('Đáp án ' + [string][char](65 + $mine) + ' là đúng.') 6 }
            else { Show-Message 'Chưa đúng' ('Đáp án đúng là ' + [string][char](65 + [int]$msg.correct) + '.') 8 }
        }
    }

    # ---------- chiếu bài của một học sinh cho cả lớp ----------
    $script:showForm = $null; $script:showTimer = $null; $script:showAllow = $false
    function Close-Show {
        if ($script:showTimer) { try { $script:showTimer.Stop(); $script:showTimer.Dispose() } catch {}; $script:showTimer = $null }
        if ($script:showForm) { $script:showAllow = $true; try { $script:showForm.Close() } catch {}; $script:showForm = $null; $script:showAllow = $false }
    }
    function Snap-Screen($msg) {
        $id = [string]$msg.id
        if ($id -notmatch '^[0-9a-f]{8}$') { return }
        $dir = Join-Path $Root 'share'
        if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Get-ChildItem -LiteralPath $dir -Filter '*.jpg' -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt (Get-Date).AddHours(-2) } | Remove-Item -Force -ErrorAction SilentlyContinue
        $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $full = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
        $g = [System.Drawing.Graphics]::FromImage($full)
        try { $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $full.Size) } finally { $g.Dispose() }
        $tw = [Math]::Min(1600, $b.Width); $th = [int]($tw * $b.Height / [Math]::Max(1, $b.Width))
        $small = New-Object System.Drawing.Bitmap($tw, $th)
        $g2 = [System.Drawing.Graphics]::FromImage($small)
        try { $g2.InterpolationMode = 'HighQualityBicubic'; $g2.DrawImage($full, 0, 0, $tw, $th) } finally { $g2.Dispose(); $full.Dispose() }
        try {
            $ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
            $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]72)
            $tmp = Join-Path $dir ($id + '.tmp')
            $small.Save($tmp, $jpgCodec, $ep)
            Move-Item -LiteralPath $tmp -Destination (Join-Path $dir ($id + '.jpg')) -Force
        } finally { $small.Dispose() }
        Send-Event @{ t = 'snap'; id = $id }
    }
    function Show-Shared($msg) {
        $id = [string]$msg.id
        if ($id -notmatch '^[0-9a-f]{8}$') { return }
        $p = Join-Path (Join-Path $Root 'show') ($id + '.jpg')
        if (-not (Test-Path -LiteralPath $p)) { return }
        Close-Show
        $bytes = [System.IO.File]::ReadAllBytes($p)
        $ms = New-Object System.IO.MemoryStream(, $bytes)
        $img = [System.Drawing.Image]::FromStream($ms)
        $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $f = New-Object System.Windows.Forms.Form
        $f.FormBorderStyle = 'None'; $f.StartPosition = 'Manual'; $f.Bounds = $b
        $f.TopMost = $true; $f.ShowInTaskbar = $false; $f.BackColor = [System.Drawing.Color]::Black
        $pb = New-Object System.Windows.Forms.PictureBox
        $pb.Dock = 'Fill'; $pb.SizeMode = 'Zoom'; $pb.Image = $img
        $cap = New-Object System.Windows.Forms.Label
        $cap.Text = ([string]$msg.cap) + '   (cả lớp cùng xem, thầy/cô sẽ tắt sau)'
        $cap.Dock = 'Top'; $cap.Height = 38; $cap.TextAlign = 'MiddleCenter'
        $cap.Font = New-Object System.Drawing.Font('Segoe UI', 13, [System.Drawing.FontStyle]::Bold)
        $cap.ForeColor = [System.Drawing.Color]::White; $cap.BackColor = [System.Drawing.Color]::FromArgb(30, 64, 175)
        $f.Controls.Add($pb); $f.Controls.Add($cap)
        $f.Add_FormClosing({ param($s, $e) if (-not $script:showAllow) { $e.Cancel = $true } })
        $script:showForm = $f
        $secs = [int]$msg.secs
        if ($secs -gt 0) {
            $script:showTimer = New-Object System.Windows.Forms.Timer
            $script:showTimer.Interval = $secs * 1000
            $script:showTimer.Add_Tick({ Close-Show })
            $script:showTimer.Start()
        }
        $f.Show(); $f.Activate()
    }

    # ---------- mở trang web / nhận tài liệu ----------
    function Open-Url($msg) {
        $u = [string]$msg.url
        if ($u -notmatch '^https?://[^\s<>"'']{3,500}$') { return }
        Start-Process $u
    }
    function Receive-Handout($msg) {
        $id = [string]$msg.id
        if ($id -notmatch '^[0-9a-f]{10,24}$') { return }
        $src = Join-Path (Join-Path $Root 'handout') $id
        if (-not (Test-Path -LiteralPath $src)) { return }
        $label = ([string]$msg.label) -replace '[\\/:*?"<>|]', ' '
        if (-not $label.Trim()) { $label = 'Tai lieu cua thay co' }
        $dst = Join-Path ([Environment]::GetFolderPath('Desktop')) $label.Trim()
        if (-not (Test-Path -LiteralPath $dst)) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }
        $first = $null
        foreach ($n in @($msg.files)) {
            $n = [System.IO.Path]::GetFileName([string]$n)
            if (-not $n) { continue }
            $p = Join-Path $src $n
            if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination (Join-Path $dst $n) -Force; if (-not $first) { $first = Join-Path $dst $n } }
        }
        Show-Message 'Giáo viên gửi tài liệu' ('Đã chép vào thư mục "' + $label.Trim() + '" trên màn hình nền.') 8
        if ($msg.open -eq 'first' -and $first) { Start-Process -FilePath $first }
        elseif ($msg.open -ne 'none') { Start-Process -FilePath 'explorer.exe' -ArgumentList ('"' + $dst + '"') }
    }

    # ---------- khóa màn hình kèm lời nhắn (mềm: chỉ che màn hình, giáo viên gửi lệnh mở để tắt) ----------
    function Show-Block($msg) {
        Close-Block
        $forms = @(); $clocks = @()
        $text = [string]$msg.text
        $styled = ([string]$msg.c1) -ne ''
        $white = [System.Drawing.Color]::White
        foreach ($s in [System.Windows.Forms.Screen]::AllScreens) {
            $f = New-Object System.Windows.Forms.Form
            $f.FormBorderStyle = 'None'
            $f.StartPosition = 'Manual'
            $f.Bounds = $s.Bounds
            $f.TopMost = $true
            $f.ShowInTaskbar = $false
            $f.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 42)
            $W = $s.Bounds.Width; $H = $s.Bounds.Height
            $u = [Math]::Max(1.0, $H / 1080.0)
            if ($styled) {
                # nền (ảnh hoặc màu chuyển sắc) vẽ sẵn, chữ là các nhãn trong suốt phía trên
                $bmp = New-Object System.Drawing.Bitmap([Math]::Max(1, [int]($W / 2)), [Math]::Max(1, [int]($H / 2)))
                $g = [System.Drawing.Graphics]::FromImage($bmp)
                try {
                    $rect = New-Object System.Drawing.Rectangle(0, 0, $bmp.Width, $bmp.Height)
                    $bgFile = ''
                    if ([string]$msg.bg -match '^[0-9a-f]{16}$') { $bgFile = Join-Path (Join-Path $Root 'wall') ([string]$msg.bg + '.jpg') }
                    if ($bgFile -and (Test-Path -LiteralPath $bgFile)) {
                        $img = [System.Drawing.Image]::FromFile($bgFile)
                        try {
                            $sc = [Math]::Max($bmp.Width / $img.Width, $bmp.Height / $img.Height)
                            $iw = $img.Width * $sc; $ih = $img.Height * $sc
                            $g.DrawImage($img, [single](($bmp.Width - $iw) / 2), [single](($bmp.Height - $ih) / 2), [single]$iw, [single]$ih)
                        } finally { $img.Dispose() }
                        $a = [int]([Math]::Min(80, [Math]::Max(0, [int]$msg.dim)) * 255 / 100)
                        $ov = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb($a, 0, 0, 0))
                        $g.FillRectangle($ov, $rect); $ov.Dispose()
                    } else {
                        $lg = New-Object System.Drawing.Drawing2D.LinearGradientBrush($rect, (Get-Color ([string]$msg.c1) '#0f172a'), (Get-Color ([string]$msg.c2) '#1e293b'), 45.0)
                        $g.FillRectangle($lg, $rect); $lg.Dispose()
                    }
                } finally { $g.Dispose() }
                $f.BackgroundImage = $bmp
                $f.BackgroundImageLayout = 'Stretch'
            }
            $mk = {
                param($txt, $size, $bold, $x, $y, $w, $h)
                $l = New-Object System.Windows.Forms.Label
                $l.Text = $txt; $l.ForeColor = $white; $l.BackColor = [System.Drawing.Color]::Transparent
                $l.Font = New-Object System.Drawing.Font('Segoe UI', [single]($size * $u), $(if ($bold) { [System.Drawing.FontStyle]::Bold } else { [System.Drawing.FontStyle]::Regular }), [System.Drawing.GraphicsUnit]::Pixel)
                $l.TextAlign = 'MiddleCenter'
                $l.SetBounds([int]$x, [int]$y, [int]$w, [int]$h)
                $f.Controls.Add($l)
                return $l
            }
            if ($styled) {
                $t = ([string]$msg.icon + ' ' + [string]$msg.title).Trim()
                [void](& $mk $t 64 $true 0 ($H * 0.16) $W (110 * $u))
                [void](& $mk $text 44 $false ($W * 0.1) ($H * 0.34) ($W * 0.8) ($H * 0.34))
                if ([string]$msg.name -or [int]$msg.no -gt 0) {
                    $nm = [string]$msg.name; if ([int]$msg.no -gt 0) { $nm = ($nm + '  ·  Máy số ' + [int]$msg.no).Trim(' ', '·') }
                    [void](& $mk $nm 36 $true 0 ($H * 0.76) $W (70 * $u))
                }
                if ($msg.clock -eq $true) {
                    $c = & $mk ([DateTime]::Now.ToString('HH:mm')) 48 $true ($W - 260 * $u) (30 * $u) (230 * $u) (80 * $u)
                    $clocks += $c
                }
            } else {
                $l = New-Object System.Windows.Forms.Label
                $l.Text = $text; $l.ForeColor = $white
                $l.Font = New-Object System.Drawing.Font('Segoe UI', 32, [System.Drawing.FontStyle]::Bold)
                $l.TextAlign = 'MiddleCenter'; $l.Dock = 'Fill'
                $f.Controls.Add($l)
            }
            $f.Add_FormClosing({ param($sender, $e) if (-not $script:allowClose) { $e.Cancel = $true } })
            $f.Show()
            $forms += $f
        }
        $script:blockForms = $forms
        $script:blockClocks = $clocks
    }
    function Close-Block {
        $script:allowClose = $true
        foreach ($f in $script:blockForms) { try { $f.Close() } catch {} }
        $script:blockForms = @()
        $script:allowClose = $false
    }

    # ---------- nộp bài ----------
    $MaxFiles = 200; $MaxBytes = 200MB; $MaxOne = 24MB
    function Submit-Items($items) {
        # items: danh sách @{src=...; rel=...}
        if ($items.Count -eq 0) { return }
        $tot = 0L
        foreach ($i in $items) { $tot += (Get-Item -LiteralPath $i.src).Length }
        $big = @($items | Where-Object { (Get-Item -LiteralPath $_.src).Length -gt $MaxOne })
        if ($items.Count -gt $MaxFiles -or $tot -gt $MaxBytes -or $big.Count -gt 0) {
            [void][System.Windows.Forms.MessageBox]::Show("Bài nộp quá lớn (tối đa 200 tệp, 200 MB, mỗi tệp tối đa 24 MB). Hãy nén lại hoặc chọn ít tệp hơn.", 'Nộp bài', 'OK', 'Warning')
            return
        }
        $id = Get-Date -Format 'yyyyMMdd-HHmmss'
        $dest = Join-Path $Submit $id
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
        foreach ($i in $items) {
            $to = Join-Path $dest $i.rel
            $dir = Split-Path -Parent $to
            if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
            Copy-Item -LiteralPath $i.src -Destination $to -Force
        }
        Send-Event @{ t = 'submit'; id = $id; files = $items.Count; bytes = $tot }
        [void][System.Windows.Forms.MessageBox]::Show(("Đã nộp {0} tệp cho giáo viên." -f $items.Count), 'Nộp bài', 'OK', 'Information')
    }
    function Submit-Files {
        $dlg = New-Object System.Windows.Forms.OpenFileDialog
        $dlg.Multiselect = $true
        $dlg.Title = 'Chọn các tệp cần nộp'
        if ($dlg.ShowDialog($script:float) -ne 'OK') { return }
        $items = @()
        foreach ($p in $dlg.FileNames) { $items += @{ src = $p; rel = (Split-Path -Leaf $p) } }
        Submit-Items $items
    }
    function Submit-Folder {
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = 'Chọn thư mục bài làm cần nộp'
        if ($dlg.ShowDialog($script:float) -ne 'OK') { return }
        $root = $dlg.SelectedPath.TrimEnd('\')
        $name = Split-Path -Leaf $root
        $items = @()
        foreach ($f in (Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue)) {
            $items += @{ src = $f.FullName; rel = (Join-Path $name $f.FullName.Substring($root.Length).TrimStart('\')) }
        }
        Submit-Items $items
    }

    # ---------- giơ tay ----------
    # cài đặt do giáo viên gửi (hiện chỉ có: cho phép giơ tay hay không), nhớ lại qua lần khởi động
    $CfgFile = Join-Path $Root 'student.cfg.json'
    $script:handOn = $true
    $script:actOn = $true
    $script:liveUntil = [DateTime]::MinValue; $script:liveSec = 5; $script:lastThumb = [DateTime]::MinValue
    try { if (Test-Path -LiteralPath $CfgFile) { $c0 = Get-Content -LiteralPath $CfgFile -Raw -Encoding UTF8 | ConvertFrom-Json; if ($c0.hand -eq $false) { $script:handOn = $false }; if ($c0.act -eq $false) { $script:actOn = $false } } } catch { }
    function Update-Pill {
        $eye = if ($script:liveUntil -gt [DateTime]::Now) { [string][char]0x25CF + ' ' } else { '' }   # chấm tròn báo "giáo viên đang xem màn hình"
        if (-not $script:handOn) { $script:float.BackColor = [System.Drawing.Color]::FromArgb(37, 99, 235); $script:pill.Text = $eye + 'Nộp bài'; return }
        if ($script:raised) { $script:float.BackColor = [System.Drawing.Color]::FromArgb(234, 88, 12); $script:pill.Text = $eye + [string][char]0x270B + ' Đang giơ tay' }
        else { $script:float.BackColor = [System.Drawing.Color]::FromArgb(37, 99, 235); $script:pill.Text = $eye + [string][char]0x270B + ' Giơ tay' }
    }
    function Toggle-Hand {
        if (-not $script:handOn) { return }
        $script:raised = -not $script:raised
        Send-Event @{ t = 'hand'; on = $script:raised }
        Update-Pill
    }

    # ---------- nút nổi nhỏ ở góc màn hình + menu ----------
    $script:float = New-Object System.Windows.Forms.Form
    $script:float.FormBorderStyle = 'None'
    $script:float.ShowInTaskbar = $false
    $script:float.TopMost = $true
    $script:float.StartPosition = 'Manual'
    $script:float.Size = New-Object System.Drawing.Size(118, 32)
    $wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
    $script:float.Location = New-Object System.Drawing.Point(($wa.Right - 132), ($wa.Bottom - 46))
    $script:float.Opacity = 0.88
    $script:pill = New-Object System.Windows.Forms.Label
    $script:pill.Dock = 'Fill'
    $script:pill.TextAlign = 'MiddleCenter'
    $script:pill.ForeColor = [System.Drawing.Color]::White
    $script:pill.Font = New-Object System.Drawing.Font('Segoe UI', 10, [System.Drawing.FontStyle]::Bold)
    $script:pill.Cursor = [System.Windows.Forms.Cursors]::Hand
    $script:float.Controls.Add($script:pill)
    Update-Pill

    $menu = New-Object System.Windows.Forms.ContextMenuStrip
    $miHand = $menu.Items.Add('Giơ tay hỏi thầy/cô')
    $miOk = $menu.Items.Add('Em hiểu rồi')
    $miLost = $menu.Items.Add('Em chưa hiểu')
    $script:react = ''
    function Set-React([string]$v) {
        $script:react = $v
        $miOk.Text = $(if ($v -eq 'ok') { [string][char]0x2714 + ' Em hiểu rồi' } else { 'Em hiểu rồi' })
        $miLost.Text = $(if ($v -eq 'lost') { [string][char]0x2714 + ' Em chưa hiểu' } else { 'Em chưa hiểu' })
    }
    $miOk.Add_Click({ try { Set-React 'ok'; Send-Event @{ t = 'react'; v = 'ok' } } catch { Log ('react: ' + $_.Exception.Message) } })
    $miLost.Add_Click({ try { Set-React 'lost'; Send-Event @{ t = 'react'; v = 'lost' } } catch { Log ('react: ' + $_.Exception.Message) } })
    $miFiles = $menu.Items.Add('Nộp tệp...')
    $miFolder = $menu.Items.Add('Nộp thư mục...')
    $miHand.Visible = $script:handOn
    $miHand.Add_Click({ try { Toggle-Hand } catch { Log ('hand: ' + $_.Exception.Message) } })
    $miFiles.Add_Click({ try { Submit-Files } catch { Log ('submit files: ' + $_.Exception.Message) } })
    $miFolder.Add_Click({ try { Submit-Folder } catch { Log ('submit folder: ' + $_.Exception.Message) } })

    # bấm = mở menu, kéo = di chuyển nút
    $script:drag = $null
    $script:moved = $false
    $script:pill.Add_MouseDown({ param($s, $e) if ($e.Button -eq 'Left') { $script:drag = [System.Windows.Forms.Cursor]::Position; $script:moved = $false } })
    $script:pill.Add_MouseMove({ param($s, $e)
        if ($script:drag -ne $null -and $e.Button -eq 'Left') {
            $p = [System.Windows.Forms.Cursor]::Position
            $dx = $p.X - $script:drag.X; $dy = $p.Y - $script:drag.Y
            if ([Math]::Abs($dx) + [Math]::Abs($dy) -gt 5) {
                $script:moved = $true
                $script:float.Location = New-Object System.Drawing.Point(($script:float.Location.X + $dx), ($script:float.Location.Y + $dy))
                $script:drag = $p
            }
        } })
    $script:pill.Add_MouseUp({ param($s, $e)
        if ($e.Button -eq 'Left' -and -not $script:moved) {
            $miHand.Text = if ($script:raised) { 'Hạ tay xuống' } else { 'Giơ tay hỏi thầy/cô' }
            $menu.Show([System.Windows.Forms.Cursor]::Position)
        }
        $script:drag = $null })

    # ---------- hình nền theo tiết (vẽ ngay trên máy, kèm số máy và tên em ngồi) ----------
    Add-Type -Namespace KV -Name Wp -MemberDefinition '[System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)] public static extern int SystemParametersInfo(int a, int b, string c, int d);'
    $WallDir  = Join-Path $env:LOCALAPPDATA 'KhoaVeyon'
    $WallOrig = Join-Path $WallDir 'wall-orig.txt'
    $WallPol  = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Policies\ActiveDesktop'
    function Set-WallLock([bool]$on) {
        try {
            if ($on) {
                if (-not (Test-Path $WallPol)) { New-Item -Path $WallPol -Force | Out-Null }
                Set-ItemProperty -Path $WallPol -Name NoChangingWallPaper -Value 1 -Type DWord
            } elseif (Test-Path $WallPol) { Remove-ItemProperty -Path $WallPol -Name NoChangingWallPaper -ErrorAction SilentlyContinue }
        } catch { Log ('wall lock: ' + $_.Exception.Message) }
    }
    function Set-Wall([string]$path) {
        $k = 'HKCU:\Control Panel\Desktop'
        Set-ItemProperty -Path $k -Name WallpaperStyle -Value '10'
        Set-ItemProperty -Path $k -Name TileWallpaper -Value '0'
        [KV.Wp]::SystemParametersInfo(20, 0, $path, 3) | Out-Null
    }
    function Get-Color([string]$hex, [string]$fallback) {
        try { return [System.Drawing.ColorTranslator]::FromHtml($hex) } catch { return [System.Drawing.ColorTranslator]::FromHtml($fallback) }
    }
    function Show-Wallpaper($msg) {
        if (-not (Test-Path -LiteralPath $WallDir)) { New-Item -ItemType Directory -Path $WallDir -Force | Out-Null }
        if (-not (Test-Path -LiteralPath $WallOrig)) {   # nhớ hình nền gốc của em một lần duy nhất
            $cur = (Get-ItemProperty 'HKCU:\Control Panel\Desktop').WallPaper
            [System.IO.File]::WriteAllText($WallOrig, [string]$cur, $utf8)
        }
        Set-WallLock $false
        $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $W = [Math]::Max(800, $b.Width); $H = [Math]::Max(600, $b.Height)
        $bmp = New-Object System.Drawing.Bitmap($W, $H)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        try {
            $g.SmoothingMode = 'AntiAlias'; $g.TextRenderingHint = 'AntiAliasGridFit'
            $rect = New-Object System.Drawing.Rectangle(0, 0, $W, $H)
            $bgFile = ''
            if ([string]$msg.bg -match '^[0-9a-f]{16}$') { $bgFile = Join-Path (Join-Path $Root 'wall') ([string]$msg.bg + '.jpg') }
            if ($bgFile -and (Test-Path -LiteralPath $bgFile)) {
                $img = [System.Drawing.Image]::FromFile($bgFile)
                try {
                    $sc = [Math]::Max($W / $img.Width, $H / $img.Height)
                    $iw = $img.Width * $sc; $ih = $img.Height * $sc
                    $g.DrawImage($img, [single](($W - $iw) / 2), [single](($H - $ih) / 2), [single]$iw, [single]$ih)
                } finally { $img.Dispose() }
                $a = [int]([Math]::Min(80, [Math]::Max(0, [int]$msg.dim)) * 255 / 100)
                $ov = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb($a, 0, 0, 0))
                $g.FillRectangle($ov, $rect); $ov.Dispose()
            } else {
                $lg = New-Object System.Drawing.Drawing2D.LinearGradientBrush($rect, (Get-Color ([string]$msg.c1) '#1d4ed8'), (Get-Color ([string]$msg.c2) '#0ea5e9'), 45.0)
                $g.FillRectangle($lg, $rect); $lg.Dispose()
            }
            $white = [System.Drawing.Brushes]::White
            $sf = New-Object System.Drawing.StringFormat
            $sf.Alignment = 'Center'; $sf.LineAlignment = 'Center'
            $unit = [Math]::Max(1, $H / 1080.0)
            $fT = New-Object System.Drawing.Font('Segoe UI', [single](60 * $unit), [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
            $fS = New-Object System.Drawing.Font('Segoe UI', [single](34 * $unit), [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
            $cy = $H * 0.30
            if ([string]$msg.title) { $g.DrawString([string]$msg.title, $fT, $white, (New-Object System.Drawing.RectangleF(0, [single]($cy - 70 * $unit), $W, [single](140 * $unit))), $sf) }
            if ([string]$msg.sub) { $g.DrawString([string]$msg.sub, $fS, $white, (New-Object System.Drawing.RectangleF(0, [single]($cy + 70 * $unit), $W, [single](70 * $unit))), $sf) }
            if ([int]$msg.no -gt 0 -or [string]$msg.name) {   # thẻ tên: góc dưới bên phải, không che biểu tượng bên trái
                $fN = New-Object System.Drawing.Font('Segoe UI', [single](46 * $unit), [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
                $fM = New-Object System.Drawing.Font('Segoe UI', [single](28 * $unit), [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
                $cw = 520 * $unit; $ch = 150 * $unit
                $cx = $W - $cw - 60 * $unit; $cyy = $H - $ch - 110 * $unit
                $card = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(150, 0, 0, 0))
                $g.FillRectangle($card, [single]$cx, [single]$cyy, [single]$cw, [single]$ch); $card.Dispose()
                if ([string]$msg.name) { $g.DrawString([string]$msg.name, $fN, $white, (New-Object System.Drawing.RectangleF([single]$cx, [single]$cyy, [single]$cw, [single]($ch * 0.62))), $sf) }
                if ([int]$msg.no -gt 0) { $g.DrawString(('Máy số ' + [int]$msg.no), $fM, $white, (New-Object System.Drawing.RectangleF([single]$cx, [single]($cyy + $ch * 0.58), [single]$cw, [single]($ch * 0.38))), $sf) }
            }
        } finally { $g.Dispose() }
        $out = Join-Path $WallDir 'wall.png'
        $tmp = Join-Path $WallDir 'wall.tmp.png'
        $bmp.Save($tmp, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
        Move-Item -LiteralPath $tmp -Destination $out -Force
        Set-Wall $out
        if ($msg.lock -eq $true) { Set-WallLock $true }
    }
    function Restore-Wallpaper {
        Set-WallLock $false
        if (Test-Path -LiteralPath $WallOrig) {
            $o = [System.IO.File]::ReadAllText($WallOrig, $utf8).Trim()
            Set-Wall $o   # chuỗi rỗng nghĩa là nền trơn như ban đầu
            Remove-Item -LiteralPath $WallOrig -Force -ErrorAction SilentlyContinue
        }
    }

    # ---------- báo cửa sổ đang ở trước cho trang Monitor (chỉ khi đổi, tối thiểu 10 giây một lần; máy giáo viên không phải hỏi) ----------
    Add-Type -Namespace KV -Name Fg -MemberDefinition '[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern System.IntPtr GetForegroundWindow(); [System.Runtime.InteropServices.DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(System.IntPtr h, out uint pid); [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)] public static extern int GetWindowText(System.IntPtr h, System.Text.StringBuilder s, int n);'
    $script:lastAct = ''; $script:lastActAt = [DateTime]::MinValue
    function Report-Activity {
        if (-not $script:actOn) { return }
        $now = [DateTime]::Now
        if (($now - $script:lastActAt).TotalSeconds -lt 10) { return }
        $h = [KV.Fg]::GetForegroundWindow()
        $sb = New-Object System.Text.StringBuilder 256
        [void][KV.Fg]::GetWindowText($h, $sb, 256)
        $procId = 0
        [void][KV.Fg]::GetWindowThreadProcessId($h, [ref]$procId)
        $pn = ''
        try { $pn = (Get-Process -Id $procId -ErrorAction Stop).ProcessName.ToLower() } catch { }
        if (-not $pn -or $pn -eq 'idle') { return }
        $w = $sb.ToString(); if ($w.Length -gt 100) { $w = $w.Substring(0, 100) }
        $key = $pn + '|' + $w
        if ($key -ne $script:lastAct -or ($now - $script:lastActAt).TotalSeconds -ge 90) {
            Send-Event @{ t = 'act'; p = $pn; w = $w }
            $script:lastAct = $key; $script:lastActAt = $now
        }
    }

    # ---------- ảnh màn hình thu nhỏ cho trang Monitor (chụp và nén ngay trên máy học sinh, chỉ khi giáo viên bật xem) ----------
    $jpgCodec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' } | Select-Object -First 1
    function Send-Thumb {
        $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $full = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
        $g = [System.Drawing.Graphics]::FromImage($full)
        try { $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $full.Size) } finally { $g.Dispose() }
        $tw = 384; $th = [int]($tw * $b.Height / [Math]::Max(1, $b.Width))
        $small = New-Object System.Drawing.Bitmap($tw, $th)
        $g2 = [System.Drawing.Graphics]::FromImage($small)
        try { $g2.InterpolationMode = 'HighQualityBicubic'; $g2.DrawImage($full, 0, 0, $tw, $th) } finally { $g2.Dispose(); $full.Dispose() }
        $b64 = ''
        try {
            foreach ($q in 55, 42, 32, 24) {
                $ms = New-Object System.IO.MemoryStream
                $ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
                $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]$q)
                $small.Save($ms, $jpgCodec, $ep)
                $b64 = [Convert]::ToBase64String($ms.ToArray()); $ms.Dispose()
                if ($b64.Length -le 13500) { break }   # tệp sự kiện tối đa 16 KB
            }
        } finally { $small.Dispose() }
        if ($b64.Length -gt 0 -and $b64.Length -le 14500) { Send-Event @{ t = 'thumb'; d = $b64 } }
    }

    # ---------- đồng hồ đếm ngược toàn lớp (góc trên giữa màn hình, nhỏ, luôn nổi) ----------
    $script:timerForm = $null; $script:timerEnd = [DateTime]::MinValue; $script:timerLabel = ''
    function Stop-Timer { if ($script:timerForm) { try { $script:timerForm.Close() } catch { }; $script:timerForm = $null }; $script:timerEnd = [DateTime]::MinValue }
    function Start-Timer([int]$secs, [string]$label) {
        Stop-Timer
        $f = New-Object System.Windows.Forms.Form
        $f.FormBorderStyle = 'None'; $f.TopMost = $true; $f.ShowInTaskbar = $false; $f.StartPosition = 'Manual'
        $f.BackColor = [System.Drawing.Color]::FromArgb(30, 64, 175); $f.Opacity = 0.92
        $f.Size = New-Object System.Drawing.Size(220, 64)
        $wa = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
        $f.Location = New-Object System.Drawing.Point(($wa.Left + [int](($wa.Width - 220) / 2)), ($wa.Top + 8))
        $l = New-Object System.Windows.Forms.Label
        $l.Dock = 'Fill'; $l.TextAlign = 'MiddleCenter'; $l.ForeColor = [System.Drawing.Color]::White
        $l.Font = New-Object System.Drawing.Font('Segoe UI', 22, [System.Drawing.FontStyle]::Bold)
        $f.Controls.Add($l)
        $f.Tag = $l
        $f.Show()
        $script:timerForm = $f; $script:timerLabel = $label
        $script:timerEnd = [DateTime]::Now.AddSeconds([Math]::Max(5, [Math]::Min(10800, $secs)))
    }
    function Tick-Timer {
        if ($script:timerEnd -eq [DateTime]::MinValue -or -not $script:timerForm) { return }
        $left = [int][Math]::Ceiling(($script:timerEnd - [DateTime]::Now).TotalSeconds)
        $lb = $script:timerForm.Tag
        if ($left -le 0) {
            $lab = $script:timerLabel
            Stop-Timer
            Show-Message ([string][char]0x23F0 + ' Hết giờ!') $(if ($lab) { $lab } else { 'Đã hết thời gian.' }) 15
            return
        }
        $lb.Text = ('{0:00}:{1:00}' -f [int][Math]::Floor($left / 60), ($left % 60))
        if ($left -le 60) { $script:timerForm.BackColor = [System.Drawing.Color]::FromArgb(185, 28, 28) }
        $script:timerForm.TopMost = $true
    }

    $clockTimer = New-Object System.Windows.Forms.Timer
    $clockTimer.Interval = 500
    $clockTimer.Add_Tick({ try { Tick-Timer } catch { } })
    $clockTimer.Start()

    # ---------- đọc hộp thư đến mỗi 1,5 giây ----------
    function Read-Inbox {
        foreach ($f in (Get-ChildItem -LiteralPath $Inbox -Filter '*.json' -ErrorAction SilentlyContinue | Sort-Object Name)) {
            $msg = $null
            try { $msg = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json } catch { }
            if ($msg -eq $null) {
                if (([DateTime]::Now - $f.LastWriteTime).TotalSeconds -gt 5) { Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue }
                continue
            }
            Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue
            try {
                switch ([string]$msg.type) {
                    'msg'      { Show-Message ([string]$msg.title) ([string]$msg.text) ([int]$msg.seconds) }
                    'block'    { Show-Block $msg }
                    'config'   {
                        if ($msg.act -ne $null) { $script:actOn = ($msg.act -eq $true) }
                        if ($msg.live -ne $null) {   # xem màn hình thu nhỏ: chỉ chạy khi giáo viên đang mở trang Monitor, tự dừng sau ttl giây nếu không được gia hạn
                            $ls = [int]$msg.live
                            if ($ls -gt 0) { $script:liveSec = [Math]::Max(2, [Math]::Min(60, $ls)); $script:liveUntil = [DateTime]::Now.AddSeconds([Math]::Max(30, [Math]::Min(300, [int]$msg.ttl))) }
                            else { $script:liveUntil = [DateTime]::MinValue }
                            Update-Pill
                        }
                        if ($msg.hand -ne $null -or $msg.act -ne $null) {
                            if ($msg.hand -ne $null) { $script:handOn = ($msg.hand -eq $true) }
                            [System.IO.File]::WriteAllText($CfgFile, (@{ hand = $script:handOn; act = $script:actOn } | ConvertTo-Json -Compress), $utf8)
                            $miHand.Visible = $script:handOn
                            if (-not $script:handOn -and $script:raised) { $script:raised = $false; Send-Event @{ t = 'hand'; on = $false } }
                            Update-Pill
                        }
                    }
                    'clear'    { Close-Block }
                    'wallpaper' { if ($msg.restore -eq $true) { Restore-Wallpaper } else { Show-Wallpaper $msg } }
                    'timer'    { if ($msg.cancel -eq $true) { Stop-Timer } else { Start-Timer ([int]$msg.secs) ([string]$msg.label) } }
                    'reactclear' { Set-React '' }
                    'quiz'     { Show-Quiz $msg }
                    'snap'     { Snap-Screen $msg }
                    'show'     { Show-Shared $msg }
                    'showclear' { Close-Show }
                    'quizend'  { End-Quiz $msg }
                    'open'     { Open-Url $msg }
                    'handout'  { Receive-Handout $msg }
                    'handclear' { $script:raised = $false; Update-Pill }
                    'collect'  { Show-Message 'Giáo viên yêu cầu nộp bài' ([string]$msg.text) 0; Submit-Files }
                }
            } catch { Log ('inbox ' + $msg.type + ': ' + $_.Exception.Message) }
        }
    }
    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = 1500
    $timer.Add_Tick({
        try {
            $now = [DateTime]::Now
            if (($now - $script:lastBeat).TotalSeconds -ge 10) {
                [System.IO.File]::WriteAllText($Heartbeat, $now.ToString('s'))
                $script:lastBeat = $now
                # tệp này vừa được cập nhật (bản mới từ máy giáo viên): thoát, dịch vụ sẽ chạy lại bản mới trong ít giây
                if ((Get-Item -LiteralPath $ScriptPath).LastWriteTimeUtc.Ticks -ne $script:StartStamp) { [System.Windows.Forms.Application]::Exit(); return }
            }
            Read-Inbox
            try { Report-Activity } catch { }
            if ($script:liveUntil -gt $now -and ($now - $script:lastThumb).TotalSeconds -ge $script:liveSec) { $script:lastThumb = $now; try { Send-Thumb } catch { Log ('thumb: ' + $_.Exception.Message) } }
            elseif ($script:liveUntil -ne [DateTime]::MinValue -and $script:liveUntil -le $now) { $script:liveUntil = [DateTime]::MinValue; Update-Pill }
            foreach ($f in $script:blockForms) { try { $f.TopMost = $true; $f.Activate() } catch {} }
            foreach ($c in $script:blockClocks) { try { $c.Text = $now.ToString('HH:mm') } catch {} }
        } catch { Log ('tick: ' + $_.Exception.Message) }
    })
    $timer.Start()
    Log ('started, session ' + $sid)
    [System.Windows.Forms.Application]::Run($script:float)
}
catch {
    Log ('fatal: ' + $_.Exception.Message)
}
