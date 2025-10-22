# Deploy the Azure Container Apps (ACA) using Bicep.
# Replace the values of the variables with your own values.
# This script now also uploads RDF/ontology assets to the provisioned storage account.

$RESOURCE_GROUP="<YOUR_RESOURCE_GROUP_NAME>"
$REGION="<YOUR_REGION>"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "CAIG Bicep Deployment" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Creating resource group..." -ForegroundColor Green
az group create --name $RESOURCE_GROUP --location $REGION

Write-Host ""
Write-Host "Deploying Bicep template..." -ForegroundColor Green
$deploymentOutput = az deployment group create `
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

# Upload RDF and ontology assets
Write-Host ""
Write-Host "Uploading RDF and ontology assets..." -ForegroundColor Green
& .\az_upload_rdf_assets.ps1 `
    -ResourceGroup $RESOURCE_GROUP `
    -StorageAccountName $storageAccountName `
    -ContainerName $storageContainerName

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Update your environment variables to use blob URLs:" -ForegroundColor White
Write-Host "   CAIG_GRAPH_SOURCE_PATH=https://$storageAccountName.blob.core.windows.net/$storageContainerName/rdf/<your-file>.nt" -ForegroundColor Gray
Write-Host "   CAIG_GRAPH_SOURCE_OWL_FILENAME=https://$storageAccountName.blob.core.windows.net/$storageContainerName/ontologies/<your-file>.owl" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Redeploy container apps with updated environment variables" -ForegroundColor White
Write-Host ""

