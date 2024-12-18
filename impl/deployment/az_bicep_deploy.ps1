# Deploy the Azure Container App (ACA) using Bicep.
# Chris Joakim, Microsoft

$RESOURCE_GROUP="caigaca25vcore"
$REGION="eastus"

Write-Host "az group create ..."
az group create --name $RESOURCE_GROUP --location $REGION

Write-Host "az deployment group create with bicep ..."
az deployment group create `
    --resource-group $RESOURCE_GROUP `
    --template-file caig.bicep `
    --parameters caig.bicepparam `
    --only-show-errors
