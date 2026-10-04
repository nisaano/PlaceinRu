$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& .\venv\Scripts\python.exe -X utf8 -B -m scripts.dev
exit $LASTEXITCODE
