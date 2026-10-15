# Puts a "Nova Bot" shortcut on your Desktop and in the Start menu.
$root = Split-Path -Parent $PSScriptRoot
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $python = (Get-Command python.exe -ErrorAction Stop).Source
    $pythonw = Join-Path (Split-Path $python) "pythonw.exe"
}
$shell = New-Object -ComObject WScript.Shell
$places = @(
    [Environment]::GetFolderPath("Desktop"),
    (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs")
)
foreach ($dir in $places) {
    $lnk = $shell.CreateShortcut((Join-Path $dir "Nova Bot.lnk"))
    $lnk.TargetPath = $pythonw
    $lnk.Arguments = "`"$root\server.py`" --open"
    $lnk.WorkingDirectory = $root
    $lnk.IconLocation = "$root\app\nova-bot.ico"
    $lnk.Description = "Nova Bot - your own AI"
    $lnk.Save()
    Write-Host "Shortcut added: $dir\Nova Bot.lnk"
}
