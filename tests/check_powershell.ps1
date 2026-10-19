# Kiểm tra CÚ PHÁP (không chạy) mọi script PowerShell của dự án. Thoát với mã 1 nếu có lỗi.
$root = Split-Path -Parent $PSScriptRoot
$bad = 0

function Test-Source([string]$name, [string]$text) {
    $tokens = $null; $errs = $null
    [void][System.Management.Automation.Language.Parser]::ParseInput($text, [ref]$tokens, [ref]$errs)
    if ($errs -and $errs.Count -gt 0) {
        foreach ($e in $errs) { Write-Host ("LỖI {0}:{1}  {2}" -f $name, $e.Extent.StartLineNumber, $e.Message) }
        return 1
    }
    Write-Host "OK   $name"
    return 0
}

foreach ($f in Get-ChildItem -Path (Join-Path $root 'scripts') -Filter *.ps1) {
    $bad += Test-Source $f.Name ([IO.File]::ReadAllText($f.FullName))
}

# KhoaVeyonServices.bat: phần sau dòng #PS1START là PowerShell (được nạp bằng iex khi chạy)
foreach ($f in Get-ChildItem -Path (Join-Path $root 'payload') -Filter *.bat -ErrorAction SilentlyContinue) {
    $t = [IO.File]::ReadAllText($f.FullName)
    $i = $t.IndexOf('#PS1' + 'START')
    if ($i -ge 0) { $bad += Test-Source ($f.Name + ' (PowerShell nhúng)') $t.Substring($i) }
    # Khối cài dịch vụ KhoaVeyonAutoLog (giữa #KVSVCSTART và #KVSVCEND): PowerShell + mã C# của dịch vụ
    $a = $t.IndexOf('#KVSVC' + 'START'); $b = $t.IndexOf('#KVSVC' + 'END')
    if ($a -ge 0 -and $b -gt $a) {
        $blk = $t.Substring($a, $b - $a)
        $bad += Test-Source ($f.Name + ' (cài dịch vụ AutoLog)') $blk
        # Trên Windows: biên dịch thử mã C# bằng đúng csc.exe mà -install dùng
        $csc = if ($env:WINDIR) { Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe' } else { '' }
        $m = [regex]::Match($blk, "(?s)\`$csSource = @'\r?\n(.*?)\r?\n'@")
        if ($csc -and (Test-Path -LiteralPath $csc) -and $m.Success) {
            $cs  = Join-Path ([IO.Path]::GetTempPath()) 'kv_autolog_check.cs'
            $exe = Join-Path ([IO.Path]::GetTempPath()) 'kv_autolog_check.exe'
            Set-Content -LiteralPath $cs -Value $m.Groups[1].Value -Encoding UTF8
            $o = & $csc /nologo /target:winexe /r:System.ServiceProcess.dll /r:System.Web.Extensions.dll "/out:$exe" $cs 2>&1
            if ($LASTEXITCODE -ne 0) { $o | ForEach-Object { Write-Host "LỖI C# $_" }; $bad++ } else { Write-Host "OK   $($f.Name) (C# dịch vụ AutoLog biên dịch được)" }
            Remove-Item -LiteralPath $cs, $exe -Force -ErrorAction SilentlyContinue
        } elseif (-not $m.Success) { Write-Host "LỖI $($f.Name): không tìm thấy mã C# của dịch vụ AutoLog"; $bad++ }
    }
}

if ($bad -gt 0) { Write-Host "Có $bad file lỗi cú pháp"; exit 1 }
Write-Host 'Tất cả script PowerShell đều đúng cú pháp'
