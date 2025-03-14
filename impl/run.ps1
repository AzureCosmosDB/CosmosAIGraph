Set-Location .\graph_app
$GraphArgList = ".\graph_app.ps1"
Start-Process -FilePath PowerShell -ArgumentList $GraphArgList

Set-Location ..\web_app
$WebArgList = ".\web_app.ps1"
Start-Process -FilePath PowerShell -ArgumentList $WebArgList -NoNewWindow

Set-Location ..