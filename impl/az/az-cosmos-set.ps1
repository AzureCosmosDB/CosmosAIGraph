
# PowerShell and az script to enable Cosmos DB NoSQL API
# key-based access as well as public network access.
# See Internal Azure Policy changes at https://aka.ms/AzMngEnvChanges 
# Chris Joakim, Microsoft, 2025

$resource_group=$env:CAIG_COSMOSDB_NOSQL_RG
$cosmos_account=$env:CAIG_COSMOSDB_NOSQL_ACCT

Write-Host "resource_group: $resource_group"
Write-Host "cosmos_account: $cosmos_account"

$tmp_dir = ".\tmp\"

# Create the tmp directory if it does not exist
if (-not(Test-Path $tmp_dir -PathType Container)) {
    New-Item -path $tmp_dir -ItemType Directory
}

Write-Host "az cosmosdb show before changes..."
az cosmosdb show -g $resource_group -n $cosmos_account > tmp\cosmosdb-show-before.json

Write-Host "applying cosmosdb changes..."
az resource update `
    --resource-type "Microsoft.DocumentDB/databaseAccounts" `
    --resource-group $resource_group `
    --name $cosmos_account `
    --set properties.disableLocalAuth=false `
    --set properties.publicNetworkAccess=Enabled > tmp\cosmosdb-set.json

Write-Host "az cosmosdb show after changes..."
az cosmosdb show -g $resource_group -n $cosmos_account > tmp\cosmosdb-show-after.json

Write-Host "done; see the output files in the tmp directory."

