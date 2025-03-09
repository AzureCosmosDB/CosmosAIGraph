
# PowerShell and az script to enable/disable local auth on a
# CosmosDB account to enable/disable Azure Portal and key use.
# Ensure that there is a tmp folder in the current directory.
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

Write-Host "az cosmosdb show ..."
az cosmosdb show -g $resource_group -n $cosmos_account > $tmp_dir\cosmosdb-show.json

Write-Host "done; see the output file in the tmp directory."
