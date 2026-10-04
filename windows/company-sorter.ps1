# 会社用フォルダに入ったファイルを、名前に含まれるサブフォルダ名を見て自動で振り分けるスクリプト(Windows用)
#
# 例: 会社用\260821_フェザー安全剃刀….dwg  ->  会社用\フェザー\260821_フェザー安全剃刀….dwg
# どのサブフォルダ名も含まないファイルは会社用に残します。
#
# 普段は「setup-company-sorter.bat」で設定し、あとはパソコン起動時に裏で自動的に動きます。
#   -Install    見張りを設定して、パソコン起動時に自動で動くようにする
#   -Uninstall  見張りを止めて、設定を消す
#   -Folder     見張るフォルダ(省略時は C:\Users\<名前>\会社用)
#   -Once       1回だけ振り分けて終わる(確認用)

param(
    [string]$Folder,
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Once
)

$ErrorActionPreference = 'Stop'

$AppDir = Join-Path $env:LOCALAPPDATA 'CompanySorter'
$ConfigPath = Join-Path $AppDir 'config.json'
$LogPath = Join-Path $AppDir '振り分け記録.txt'
$ShortcutName = '会社用の自動振り分け.lnk'
$IntervalSeconds = 5
# 作業中の一時ファイルやダウンロード途中のファイルは動かさない
$SkipExt = '.tmp .crdownload .part .partial .download .lnk .url' -split ' '

function Get-Normalized([string]$s) {
    # 全角・半角や大文字・小文字の違いを無視して比べる
    return $s.Normalize([Text.NormalizationForm]::FormKC).ToLowerInvariant()
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

function Write-Log([string]$message) {
    $line = '{0}  {1}' -f (Get-Date -Format 'yyyy/MM/dd HH:mm:ss'), $message
    try { Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 } catch { }
    Write-Host $line
}

function Test-FileReady([IO.FileInfo]$file, [hashtable]$lastSizes) {
    # コピーや保存の途中で動かさないよう、大きさが前回と同じで、ほかのアプリが使っていないときだけ動かす
    $key = $file.FullName
    $prev = $lastSizes[$key]
    $lastSizes[$key] = $file.Length
    if ($null -eq $prev -or $prev -ne $file.Length) { return $false }
    try {
        $stream = [IO.File]::Open($file.FullName, 'Open', 'Read', 'None')
        $stream.Close()
        return $true
    } catch {
        return $false
    }
}

function Invoke-Sort([string]$target, [hashtable]$lastSizes, [bool]$skipReadyCheck) {
    $folders = @(Get-ChildItem -LiteralPath $target -Directory | Where-Object {
        -not ($_.Attributes -band [IO.FileAttributes]::Hidden)
    })
    if ($folders.Count -eq 0) { return }

    $files = @(Get-ChildItem -LiteralPath $target -File | Where-Object {
        -not $_.Name.StartsWith('.') -and
        -not $_.Name.StartsWith('~$') -and
        -not ($_.Attributes -band [IO.FileAttributes]::Hidden) -and
        -not ($SkipExt -contains $_.Extension.ToLower()) -and
        -not (@('desktop.ini', 'thumbs.db') -contains $_.Name.ToLower())
    })

    foreach ($f in $files) {
        $name = Get-Normalized $f.BaseName
        # 「AI」と「AI戦略」のように両方当てはまるときは、長い名前のフォルダを選ぶ
        $match = $folders |
            Where-Object { $name.Contains((Get-Normalized $_.Name)) } |
            Sort-Object { $_.Name.Length } -Descending |
            Select-Object -First 1
        if (-not $match) { continue }
        if (-not $skipReadyCheck -and -not (Test-FileReady $f $lastSizes)) { continue }

        $dest = Get-UniquePath (Join-Path $match.FullName $f.Name)
        try {
            Move-Item -LiteralPath $f.FullName -Destination $dest
            $lastSizes.Remove($f.FullName)
            Write-Log ("{0}  ->  {1}\{2}" -f $f.Name, $match.Name, (Split-Path $dest -Leaf))
        } catch {
            Write-Log ("移動できませんでした: {0}  ({1})" -f $f.Name, $_.Exception.Message)
        }
    }
}

function Get-PowerShellPath {
    return Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
}

function Stop-RunningSorter {
    $self = $PID
    Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" |
        Where-Object { $_.CommandLine -like '*company-sorter.ps1*' -and $_.ProcessId -ne $self } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Invoke-Install([string]$target) {
    if (-not (Test-Path -LiteralPath $target -PathType Container)) {
        Write-Host "会社用フォルダが見つかりません: $target"
        Write-Host '先に会社用フォルダをデスクトップからこの場所へ移してください。'
        exit 1
    }

    # ウイルスバスターなどに止められない場所かを、試しにファイルを作って確かめる
    $probe = Join-Path $target ('.write-test-' + [guid]::NewGuid().ToString('N'))
    try {
        Set-Content -LiteralPath $probe -Value 'test'
        Remove-Item -LiteralPath $probe -Force
    } catch {
        Write-Host "このフォルダにはファイルを書き込めませんでした: $target"
        Write-Host 'ウイルス対策ソフトに守られている場所かもしれません。デスクトップやドキュメントの外へ移してください。'
        exit 1
    }

    Stop-RunningSorter
    if (-not (Test-Path -LiteralPath $AppDir)) { New-Item -ItemType Directory -Path $AppDir | Out-Null }
    $scriptPath = Join-Path $AppDir 'company-sorter.ps1'
    if ($PSCommandPath -ne $scriptPath) { Copy-Item -LiteralPath $PSCommandPath -Destination $scriptPath -Force }
    ConvertTo-Json -InputObject @{ folder = $target } | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

    $arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
    $startup = [Environment]::GetFolderPath('Startup')
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Join-Path $startup $ShortcutName))
    $lnk.TargetPath = Get-PowerShellPath
    $lnk.Arguments = $arguments
    $lnk.WindowStyle = 7
    $lnk.Description = '会社用フォルダのファイルを自動で振り分けます'
    $lnk.Save()

    Start-Process -FilePath (Get-PowerShellPath) -ArgumentList $arguments -WindowStyle Hidden
    Write-Log "見張りを開始しました: $target"
    Write-Host ''
    Write-Host '設定が終わりました。これからは会社用フォルダにファイルを入れると、数秒で振り分けられます。'
    Write-Host 'パソコンを再起動しても自動で動きます。'
}

function Invoke-Uninstall {
    Stop-RunningSorter
    $lnkPath = Join-Path ([Environment]::GetFolderPath('Startup')) $ShortcutName
    if (Test-Path -LiteralPath $lnkPath) { Remove-Item -LiteralPath $lnkPath -Force }
    if (Test-Path -LiteralPath $ConfigPath) { Remove-Item -LiteralPath $ConfigPath -Force }
    $installed = Join-Path $AppDir 'company-sorter.ps1'
    if (Test-Path -LiteralPath $installed) { Remove-Item -LiteralPath $installed -Force }
    Write-Host '自動振り分けを止めました。会社用フォルダのファイルはそのままです。'
}

if ($Uninstall) { Invoke-Uninstall; exit 0 }

if (-not $Folder -and (Test-Path -LiteralPath $ConfigPath)) {
    $Folder = (Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json).folder
}
if (-not $Folder) { $Folder = Join-Path $env:USERPROFILE '会社用' }

if ($Install) { Invoke-Install $Folder; exit 0 }

if (-not (Test-Path -LiteralPath $Folder -PathType Container)) {
    Write-Host "フォルダが見つかりません: $Folder"
    exit 1
}

if ($Once) {
    Invoke-Sort $Folder @{} $true
    exit 0
}

# 2つ同時に動かないようにする
$mutex = New-Object Threading.Mutex($false, 'Local\CompanySorter')
if (-not $mutex.WaitOne(0)) { exit 0 }

$lastSizes = @{}
while ($true) {
    try {
        if (Test-Path -LiteralPath $Folder -PathType Container) { Invoke-Sort $Folder $lastSizes $false }
    } catch {
        Write-Log ("エラー: {0}" -f $_.Exception.Message)
    }
    Start-Sleep -Seconds $IntervalSeconds
}
