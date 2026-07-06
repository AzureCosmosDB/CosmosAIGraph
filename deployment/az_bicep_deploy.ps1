# Deploy the Azure Container Apps (ACA) using Bicep.
# Replace the values of the variables with your own values.
# This script now also uploads RDF/ontology assets to the provisioned storage account.

$RESOURCE_GROUP="<YOUR_RESOURCE_GROUP_NAME>"
$REGION="<YOUR_REGION>"

# --- Deployment infrastructure settings (Bicep inputs; NOT read by local execution,
#     so they live here rather than in set-caig-deploy-env.ps1) ---
$ACA_ENVIRONMENT_NAME = "caig-aca-env"   # ACA managed environment to create
$LA_WORKSPACE_NAME    = "caig-law"       # Log Analytics workspace to create
$COSMOSDB_NOSQL_RG    = $RESOURCE_GROUP  # RG of your EXISTING Cosmos DB account (change if different)
$DEFINED_AUTH_USERS   = ""               # comma-separated ACA users (optional)
$GRAPH_SERVICE_NAME   = "caig-graph"     # ACA app name for the graph service
$WEB_APP_NAME         = "caig-web"       # ACA app name for the web app

# --- Graph backend (deployment-specific option, like $RESOURCE_GROUP / $REGION above) ---
# 'in_memory' (default): deploy the web + graph Container Apps only.
# 'fuseki'             : additionally deploy the Apache Jena Fuseki triple store and
#                        the MCP server Container Apps.
$GRAPH_BACKEND        = "in_memory"
$FUSEKI_SERVICE_NAME  = "fuseki"     # ACA app name for Fuseki    (used when 'fuseki')
$MCP_SERVER_NAME      = "mcp-jena"   # ACA app name for MCP server (used when 'fuseki')

# Optional: pin secrets to stable values across redeploys. If left unset, the script
# auto-generates strong random values (the Fuseki password is internal; the MCP API
# key is printed at the end so you can configure Foundry IQ).
# $env:CAIG_FUSEKI_ADMIN_PASSWORD = "<your-fuseki-admin-password>"
# $env:CAIG_MCP_API_KEY           = "<your-mcp-api-key>"

# Publish the deployment settings to the environment variables that caig.bicepparam reads.
$env:CAIG_ACA_ENVIRONMENT_NAME = $ACA_ENVIRONMENT_NAME
$env:CAIG_AZURE_REGION         = $REGION
$env:CAIG_COSMOSDB_NOSQL_RG    = $COSMOSDB_NOSQL_RG
$env:CAIG_LA_WORKSPACE_NAME    = $LA_WORKSPACE_NAME
$env:CAIG_DEFINED_AUTH_USERS   = $DEFINED_AUTH_USERS
$env:CAIG_GRAPH_SERVICE_NAME   = $GRAPH_SERVICE_NAME
$env:CAIG_WEB_APP_NAME         = $WEB_APP_NAME
$env:CAIG_GRAPH_BACKEND        = $GRAPH_BACKEND
$env:CAIG_FUSEKI_SERVICE_NAME  = $FUSEKI_SERVICE_NAME
$env:CAIG_MCP_SERVER_NAME      = $MCP_SERVER_NAME

# MCP server repo, built server-side with `az acr build` (no Docker / docker login /
# clone) when $GRAPH_BACKEND = 'fuseki'.
$MCP_JENA_REPO = "https://github.com/alekseys/mcp-jena.git"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "CAIG Bicep Deployment" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Creating resource group..." -ForegroundColor Green
# Optional RG tags (e.g. internal security-policy exemptions such as
# 'SecurityControl=Ignore') come from the gitignored env script via CAIG_RG_TAGS,
# so the value stays out of the public repo. Applied at creation, before any resources.
if ([string]::IsNullOrWhiteSpace($env:CAIG_RG_TAGS)) {
    az group create --name $RESOURCE_GROUP --location $REGION
} else {
    az group create --name $RESOURCE_GROUP --location $REGION --tags ($env:CAIG_RG_TAGS -split '\s+')
}

# Build the MCP server image and wire up its config (Fuseki backend only).
if ($GRAPH_BACKEND -eq 'fuseki') {
    # 0. Auto-generate a strong Fuseki admin password when unset (avoids the weak
    #    'admin' default). It is shared by the Fuseki container (ADMIN_PASSWORD),
    #    the graph app (CAIG_FUSEKI_PASSWORD), and the MCP server (JENA_PASSWORD),
    #    all set from the single fusekiAdminPassword Bicep parameter.
    if ([string]::IsNullOrWhiteSpace($env:CAIG_FUSEKI_ADMIN_PASSWORD)) {
        $env:CAIG_FUSEKI_ADMIN_PASSWORD = [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24)).ToLower()
        Write-Host ""
        Write-Host "Generated Fuseki admin password (internal only; graph app + MCP share it)." -ForegroundColor Yellow
    }

    # 1. Auto-generate a strong MCP API key if the caller didn't supply one.
    if ([string]::IsNullOrWhiteSpace($env:CAIG_MCP_API_KEY)) {
        $env:CAIG_MCP_API_KEY = [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()
        Write-Host ""
        Write-Host "Generated MCP API key (save this - Foundry IQ uses it as the bearer token):" -ForegroundColor Yellow
        Write-Host "  $($env:CAIG_MCP_API_KEY)" -ForegroundColor Yellow
    }

    # 2. Ensure an Azure Container Registry (idempotent). The name is derived
    #    deterministically from the resource group + subscription so re-runs reuse it.
    if ([string]::IsNullOrWhiteSpace($env:CAIG_ACR_NAME)) {
        $subId = az account show --query id -o tsv
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $hash = [Convert]::ToHexString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes("$RESOURCE_GROUP$subId"))).ToLower()
        $env:CAIG_ACR_NAME = "caig" + $hash.Substring(0, 12)
    }
    $acrName = $env:CAIG_ACR_NAME
    Write-Host ""
    Write-Host "Ensuring Azure Container Registry '$acrName' ..." -ForegroundColor Green
    az acr create --resource-group $RESOURCE_GROUP --name $acrName --sku Basic --admin-enabled true --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: az acr create failed" -ForegroundColor Red; exit 1 }

    # 3. Build the image directly from the Git repo, server-side (uses your az login).
    Write-Host "Building MCP image from $MCP_JENA_REPO via ACR Tasks ..." -ForegroundColor Green
    az acr build --registry $acrName --image mcp-jena:latest $MCP_JENA_REPO --only-show-errors
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: az acr build failed" -ForegroundColor Red; exit 1 }

    # 4. Export the image + registry credentials for the Bicep parameters.
    $env:CAIG_ACR_LOGIN_SERVER = az acr show --name $acrName --query loginServer -o tsv
    $env:CAIG_MCP_SERVER_IMAGE = "$($env:CAIG_ACR_LOGIN_SERVER)/mcp-jena:latest"
    $env:CAIG_ACR_USERNAME = az acr credential show --name $acrName --query username -o tsv
    $env:CAIG_ACR_PASSWORD = az acr credential show --name $acrName --query "passwords[0].value" -o tsv
    Write-Host "MCP image built: $($env:CAIG_MCP_SERVER_IMAGE)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Deploying Bicep template..." -ForegroundColor Green
$deploymentOutput = az deployment group create `
    --name caig-deploy `
    --resource-group $RESOURCE_GROUP `
    --template-file caig.bicep `
    --parameters caig.bicepparam `
    --only-show-errors `
    --output json | ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Deployment failed" -ForegroundColor Red
    exit 1
}

Write-Host "Deployment completed successfully" -ForegroundColor Green

# Extract storage account name from deployment outputs
$storageAccountName = $deploymentOutput.properties.outputs.storageAccountName.value
$storageContainerName = $deploymentOutput.properties.outputs.storageContainerName.value

Write-Host ""
Write-Host "Storage Account: $storageAccountName" -ForegroundColor Yellow
Write-Host "Container Name: $storageContainerName" -ForegroundColor Yellow

# Surface the MCP server endpoint + API key when the Fuseki backend is used.
$mcpEndpoint = $deploymentOutput.properties.outputs.mcpServerEndpoint.value
if ($mcpEndpoint) {
    Write-Host ""
    Write-Host "MCP server (Foundry IQ Knowledge Source):" -ForegroundColor Yellow
    Write-Host "  Endpoint : $mcpEndpoint" -ForegroundColor Gray
    Write-Host "  API key  : $($env:CAIG_MCP_API_KEY)" -ForegroundColor Gray
    Write-Host "  Configure Foundry IQ with this URL and the API key as the bearer token." -ForegroundColor Gray
}

# Upload RDF and ontology assets
Write-Host ""
Write-Host "Uploading RDF and ontology assets..." -ForegroundColor Green
& .\az_upload_rdf_assets.ps1 `
    -ResourceGroup $RESOURCE_GROUP `
    -StorageAccountName $storageAccountName `
    -ContainerName $storageContainerName

# --- Point the graph app at the (private) blob assets via a read-only SAS ---
# The storage account is private, so the graph app fetches its ontology/RDF over an
# authenticated SAS URL. The uploaded blob name equals the local relative path (see
# az_upload_rdf_assets.ps1), so the URL is <blobBase>/<relative-path>?<SAS>. The graph
# app tolerates an unreachable source at first startup (empty model), so updating these
# env vars now triggers a new revision that loads the real data.
$fileBasedTypes = @('rdf_file', 'json_docs_file')
$owlRel  = $env:CAIG_GRAPH_SOURCE_OWL_FILENAME
$pathRel = $env:CAIG_GRAPH_SOURCE_PATH
$rewriteOwl  = $owlRel  -and ($owlRel  -notmatch '^https?://')
$rewritePath = $pathRel -and ($pathRel -notmatch '^https?://') -and ($env:CAIG_GRAPH_SOURCE_TYPE -in $fileBasedTypes)

if ($rewriteOwl -or $rewritePath) {
    Write-Host ""
    Write-Host "Wiring the graph app to the private blob assets via a read-only SAS..." -ForegroundColor Green

    $storageKey = (az storage account keys list -g $RESOURCE_GROUP -n $storageAccountName --query "[0].value" -o tsv)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($storageKey)) {
        Write-Host "ERROR: could not read the storage account key" -ForegroundColor Red; exit 1
    }
    $storageKey = $storageKey.Trim()
    $sasExpiry = (Get-Date).ToUniversalTime().AddYears(1).ToString("yyyy-MM-ddTHH:mmZ")
    $sasToken = (az storage container generate-sas -n $storageContainerName --account-name $storageAccountName --account-key $storageKey --permissions r --expiry $sasExpiry --https-only -o tsv)
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($sasToken)) {
        Write-Host "ERROR: could not generate the SAS token" -ForegroundColor Red; exit 1
    }
    $sasToken = $sasToken.Trim()

    $blobBase = "https://$storageAccountName.blob.core.windows.net/$storageContainerName"
    if ($rewriteOwl) {
        $env:CAIG_GRAPH_SOURCE_OWL_FILENAME = "$blobBase/${owlRel}?$sasToken"
    }
    if ($rewritePath) {
        $env:CAIG_GRAPH_SOURCE_PATH = "$blobBase/${pathRel}?$sasToken"
    }

    Write-Host "Redeploying so the graph app loads the assets from blob storage..." -ForegroundColor Green
    # Re-run the Bicep deployment (not 'az containerapp update') so the SAS URLs are read
    # from the environment by the Bicep engine. This avoids putting the SAS token's '&'
    # characters on a command line, which breaks az.cmd on Windows.
    az deployment group create --name caig-deploy --resource-group $RESOURCE_GROUP --template-file caig.bicep --parameters caig.bicepparam --only-show-errors --output none
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: redeploy to apply the SAS blob URLs failed" -ForegroundColor Red; exit 1
    }
    Write-Host "Graph app redeployed - it will load the model from blob storage." -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. The graph app was automatically pointed at the RDF/ontology assets in blob" -ForegroundColor White
Write-Host "   storage via a 1-year read-only SAS; its newest revision loads them." -ForegroundColor White
Write-Host "2. Open the web app and check graph health (FQDNs from the deployment outputs):" -ForegroundColor White
Write-Host "     Web:   https://$($deploymentOutput.properties.outputs.webAppFqdn.value)" -ForegroundColor Gray
Write-Host "     Graph: https://$($deploymentOutput.properties.outputs.graphServiceFqdn.value)/liveness" -ForegroundColor Gray
Write-Host ""

