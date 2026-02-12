$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m PyInstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name "LineForge" `
  --add-binary ".\bin\potrace.exe;bin" `
  app.py


Write-Host "Built: .\dist\LineForge.exe"
