# ダウンロードフォルダのファイルを種類ごとのサブフォルダに振り分けるスクリプト(Windows用)
#
# 普段は同じフォルダの「organize-downloads.bat」をダブルクリックして使います。
#   -Folder <パス>  整理するフォルダ(省略時はダウンロードフォルダ)
#   -Run            確認なしで実際に移動する
#   -Undo           直前の整理を元に戻す

param(
    [string]$Folder,
    [switch]$Run,
    [switch]$Undo
)

$ErrorActionPreference = 'Stop'

$Categories = [ordered]@{
    '画像'           = '.jpg .jpeg .png .gif .bmp .webp .heic .svg .tif .tiff .ico'
    '動画'           = '.mp4 .mov .avi .mkv .wmv .webm .m4v'
    '音楽'           = '.mp3 .wav .aac .flac .m4a .ogg .wma'
    '文書'           = '.pdf .doc .docx .txt .rtf .odt .md'
    '表計算'         = '.xls .xlsx .xlsm .csv .ods'
    'プレゼン'       = '.ppt .pptx .odp'
    '圧縮ファイル'   = '.zip .rar .7z .tar .gz .bz2 .xz .lzh'
    'インストーラー' = '.exe .msi .msix .appx .iso'
    'プログラム'     = '.py .js .ts .html .htm .css .json .java .c .cpp .sh .bat .ps1'
}
$Other = 'その他'
# ダウンロード途中のファイルは動かさない
$Skip = '.crdownload .part .partial .tmp .download' -split ' '
$LogName = '.organize_log.json'

function Get-DownloadsFolder {
    try {
        $path = (New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path
        if ($path -and (Test-Path -LiteralPath $path)) { return $path }
    } catch { }
    return Join-Path $env:USERPROFILE 'Downloads'
}

function Get-Category([string]$ext) {
    $ext = $ext.ToLower()
    foreach ($name in $Categories.Keys) {
        if (($Categories[$name] -split ' ') -contains $ext) { return $name }
    }
    return $Other
}

function Get-UniquePath([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $path }
    $dir = Split-Path $path -Parent
    $stem = [IO.Path]::GetFileNameWithoutExtension($path)
    $ext = [IO.Path]::GetExtension($path)
    $n = 1
    while ($true) {
        $candidate = Join-Path $dir "$stem ($n)$ext"
        if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }
        $n++
    }
}

function Invoke-Organize([string]$target, [bool]$run) {
    $files = @(Get-ChildItem -LiteralPath $target -File | Where-Object {
        -not $_.Name.StartsWith('.') -and
        -not ($_.Attributes -band [IO.FileAttributes]::Hidden) -and
        -not ($Skip -contains $_.Extension.ToLower())
    } | Sort-Object Name)

    if ($files.Count -eq 0) {
        Write-Host '整理するファイルがありません。'
        return
    }

    $plan = foreach ($f in $files) {
        $category = Get-Category $f.Extension
        [pscustomobject]@{
            Source   = $f.FullName
            Category = $category
            Dest     = Get-UniquePath (Join-Path (Join-Path $target $category) $f.Name)
        }
    }
    foreach ($p in $plan) {
        Write-Host ("{0}  ->  {1}\{2}" -f (Split-Path $p.Source -Leaf), $p.Category, (Split-Path $p.Dest -Leaf))
    }
    Write-Host ''
    Write-Host ("{0} 個のファイルを上のように振り分けます。" -f $files.Count)

    if (-not $run) {
        $answer = Read-Host '実行しますか? (Y/N)'
        if ($answer -notmatch '^[yYｙＹ]') {
            Write-Host '中止しました。ファイルは動かしていません。'
            return
        }
    }

    $moves = New-Object System.Collections.ArrayList
    foreach ($p in $plan) {
        $dir = Split-Path $p.Dest -Parent
        if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
        # 実行直前に同名ファイルができていた場合に備えて取り直す
        $dest = Get-UniquePath $p.Dest
        try {
            Move-Item -LiteralPath $p.Source -Destination $dest
            [void]$moves.Add([pscustomobject]@{ from = $p.Source; to = $dest })
        } catch {
            Write-Host ("移動できませんでした(使用中かもしれません): {0}" -f (Split-Path $p.Source -Leaf))
        }
    }

    $logPath = Join-Path $target $LogName
    ConvertTo-Json -InputObject @($moves) | Set-Content -LiteralPath $logPath -Encoding UTF8
    try { (Get-Item -LiteralPath $logPath -Force).Attributes += 'Hidden' } catch { }

    Write-Host ''
    Write-Host ("{0} 個のファイルを移動しました。元に戻すには「undo-organize.bat」を実行してください。" -f $moves.Count)
}

function Invoke-Undo([string]$target) {
    $logPath = Join-Path $target $LogName
    if (-not (Test-Path -LiteralPath $logPath)) {
        Write-Host '元に戻す記録がありません。'
        return
    }
    # Windows PowerShell 5.1 は配列を1個のまとまりで返すので foreach で展開する
    $moves = @()
    foreach ($m in (Get-Content -LiteralPath $logPath -Raw -Encoding UTF8 | ConvertFrom-Json)) { $moves += $m }
    [array]::Reverse($moves)
    foreach ($m in $moves) {
        if ((Test-Path -LiteralPath $m.to) -and -not (Test-Path -LiteralPath $m.from)) {
            Move-Item -LiteralPath $m.to -Destination $m.from
            Write-Host ("{0}  ->  元の場所" -f (Split-Path $m.to -Leaf))
        } else {
            Write-Host ("スキップ: {0}" -f $m.to)
        }
    }
    foreach ($dir in ($moves | ForEach-Object { Split-Path $_.to -Parent } | Sort-Object -Unique)) {
        if ((Test-Path -LiteralPath $dir) -and -not (Get-ChildItem -LiteralPath $dir -Force)) {
            Remove-Item -LiteralPath $dir
        }
    }
    Remove-Item -LiteralPath $logPath -Force
    Write-Host '元に戻しました。'
}

if (-not $Folder) { $Folder = Get-DownloadsFolder }
if (-not (Test-Path -LiteralPath $Folder -PathType Container)) {
    Write-Host "フォルダが見つかりません: $Folder"
    exit 1
}
Write-Host "対象フォルダ: $Folder"
Write-Host ''

if ($Undo) { Invoke-Undo $Folder } else { Invoke-Organize $Folder $Run.IsPresent }
