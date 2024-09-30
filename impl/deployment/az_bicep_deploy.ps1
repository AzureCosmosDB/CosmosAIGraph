

$RESOURCE_GROUP="caigaca11"
$REGION="eastus"

echo "az group create ..."
az group create --name $RESOURCE_GROUP --location $REGION

echo "az deployment group create with bicep ..."
az deployment group create `
    --resource-group $RESOURCE_GROUP `
    --template-file caig.bicep `
    --parameters caig.bicepparam `
    --only-show-errors
