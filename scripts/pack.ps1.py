param()
Push-Location "$PSScriptRoot\.."
if (!(Test-Path dist)) { New-Item -ItemType Directory dist | Out-Null }
& ".\venv\Scripts\python.exe" ".\scripts\context_pack.py"
Pop-Location
