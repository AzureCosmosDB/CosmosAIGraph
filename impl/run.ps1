Set-Location .\app
$AppArgList = ".\webapp.ps1"
$SvcArgList = ".\websvc.ps1"
.\venv\Scripts\activate
Start-Process -FilePath PowerShell -ArgumentList $SvcArgList -NoNewWindow
Start-Process -FilePath PowerShell -ArgumentList $AppArgList