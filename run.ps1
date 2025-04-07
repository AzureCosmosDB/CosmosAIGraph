Set-Location .\impl\graph_app
$GraphArgList = "-NoExit .\graph_app.ps1"
Start-Process -FilePath PowerShell -ArgumentList $GraphArgList

Set-Location ..\web_app
$WebArgList = ".\web_app.ps1"
Start-Process -FilePath PowerShell -ArgumentList $WebArgList -NoNewWindow

Set-Location ..