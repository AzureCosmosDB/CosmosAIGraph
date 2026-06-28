# Starts the Apache Jena Fuseki sidecar as a local Docker container for the
# CosmosAIGraph graph_app "fuseki" backend.
#
# Idempotent: starts (or reuses) a container named 'caig-fuseki' that exposes
# the 'caig' dataset on http://localhost:3030/caig. The graph_app uploads the
# locally-assembled RDF model to this dataset at startup and then serves all
# SPARQL queries/updates from it.
#
# Usage:
#   .\fuseki.ps1
#   .\fuseki.ps1 -Port 3030 -AdminPassword mysecret
#
# Chris Joakim, Aleksey Savateyev

param(
    [string]$ContainerName = "caig-fuseki",
    [string]$Image         = "stain/jena-fuseki:latest",
    [int]   $Port          = 3030,
    [string]$AdminPassword = "admin"
)

$ErrorActionPreference = "Stop"

$existing = docker ps -a --filter "name=^/$ContainerName$" --format "{{.Names}}"
if ($existing -eq $ContainerName) {
    docker start $ContainerName | Out-Null
    Write-Host "Started existing Fuseki container '$ContainerName' on port $Port."
}
else {
    # Create the 'caig' dataset via the FUSEKI_DATASET_1 env var rather than a
    # mounted assembler file. Mounting a single file into /fuseki/configuration
    # makes Docker create that directory root-owned and non-writable, which makes
    # Fuseki fail to start (FusekiConfigException: Not writable) and return 503
    # for every request. The env-var approach matches docker-compose and ACA.
    docker run -d --name $ContainerName `
        -p "$($Port):3030" `
        -e "ADMIN_PASSWORD=$AdminPassword" `
        -e "FUSEKI_DATASET_1=caig" `
        $Image | Out-Null
    Write-Host "Started new Fuseki container '$ContainerName' on port $Port (dataset: caig)."
}

Write-Host "Fuseki UI:      http://localhost:$Port/"
Write-Host "Dataset URL:    http://localhost:$Port/caig"
