# J.A.R.V.I.S. PowerShell Interactive Controller
$Host.UI.RawUI.WindowTitle = "J.A.R.V.I.S. PowerShell Controller"
$ROOT = $PSScriptRoot
Set-Location $ROOT

$PY = if (Test-Path "$ROOT\.venv\Scripts\python.exe") { "$ROOT\.venv\Scripts\python.exe" } else { "python" }

& $PY terminal.py
