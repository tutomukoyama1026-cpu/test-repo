@echo off
powershell -NoProfile -Command "Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA CompanySorter) -Filter *.txt | ForEach-Object { notepad $_.FullName }"
