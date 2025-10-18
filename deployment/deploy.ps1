# Deploy the Azure Container Apps (ACA) using Bicep.
# Replace the values of the variables with your own values.

$RESOURCE_GROUP="caig"
$REGION="eastus"

Write-Host "az group create ..."
az group create --name $RESOURCE_GROUP --location $REGION

Write-Host "az deployment group create with bicep ..."
az deployment group create `
    --resource-group $RESOURCE_GROUP `
    --template-file caig.bicep `
    --parameters caig.bicepparam `
    --only-show-errors
