# Fetch the Azure Container App (ACA) log files.
# Replace the values of the variables with your own values.

$RESOURCE_GROUP="<RESOURCE_GROUP_NAME>"
$REGION="<AZURE_REGION>"

Write-Host "fetching caig-web logs ..."
az containerapp logs show --name caig-web --resource-group $RESOURCE_GROUP --type console --format $FORMAT --tail 300 > tmp\caig-web-console.log
az containerapp logs show --name caig-web --resource-group $RESOURCE_GROUP --type system  --format $FORMAT --tail 300 > tmp\caig-web-system.log

Write-Host "fetching caig-graph logs ..."
az containerapp logs show --name caig-graph --resource-group $RESOURCE_GROUP --type console --format $FORMAT --tail 300 > tmp\caig-graph-console.log
az containerapp logs show --name caig-graph --resource-group $RESOURCE_GROUP --type system  --format $FORMAT --tail 300 > tmp\caig-graph-system.log
