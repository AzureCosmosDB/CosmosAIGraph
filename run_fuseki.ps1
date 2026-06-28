# Alternative launcher: runs the graph and web microservices with the graph_app
# configured to use the external Apache Jena Fuseki sidecar backend.
#
# This is a backward-compatible alternative to run.ps1, which uses the default
# in-process, in-memory Jena graph. The original run.ps1 is unchanged.
#
# Prerequisite: Docker Desktop running (for the Fuseki container).
# Chris Joakim, Aleksey Savateyev

$env:CAIG_GRAPH_BACKEND = "fuseki"
if (-not $env:CAIG_FUSEKI_DATASET_URL) {
    $env:CAIG_FUSEKI_DATASET_URL = "http://localhost:3030/caig"
}
# Credentials the graph_app uses to authenticate write operations (SPARQL update
# and Graph Store Protocol uploads) against the Fuseki sidecar. These must match
# the container's ADMIN_PASSWORD (see impl\fuseki\fuseki.ps1).
if (-not $env:CAIG_FUSEKI_USER) {
    $env:CAIG_FUSEKI_USER = "admin"
}
if (-not $env:CAIG_FUSEKI_PASSWORD) {
    $env:CAIG_FUSEKI_PASSWORD = "admin"
}

# Start the Apache Jena Fuseki sidecar container (idempotent).
& "$PSScriptRoot\impl\fuseki\fuseki.ps1"

Set-Location .\impl\graph_app
$GraphArgList = "-NoExit .\graph_app.ps1"
Start-Process -FilePath PowerShell -ArgumentList $GraphArgList

Set-Location ..\web_app
$WebArgList = ".\web_app.ps1"
Start-Process -FilePath PowerShell -ArgumentList $WebArgList -NoNewWindow

Set-Location ..\..
