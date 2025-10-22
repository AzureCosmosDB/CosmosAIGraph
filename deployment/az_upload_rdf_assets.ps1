# Upload RDF and ontology assets to Azure Blob Storage
# This script should be run after the Bicep deployment completes
# to populate the storage container with the necessary assets.
#
# Usage:
#   .\az_upload_rdf_assets.ps1 -ResourceGroup <rg-name> -StorageAccountName <storage-name> -ContainerName <container-name>
#
# Chris Joakim, Microsoft, 2025

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$StorageAccountName,
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerName = "data",
    
    [Parameter(Mandatory=$false)]
    [string]$SourceRdfDir = "..\impl\graph_app\rdf",
    
    [Parameter(Mandatory=$false)]
    [string]$SourceOntologiesDir = "..\impl\graph_app\ontologies"
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Uploading RDF and Ontology Assets to Azure Blob" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Resource Group:      $ResourceGroup" -ForegroundColor Yellow
Write-Host "Storage Account:     $StorageAccountName" -ForegroundColor Yellow
Write-Host "Container:           $ContainerName" -ForegroundColor Yellow
Write-Host "Source RDF Dir:      $SourceRdfDir" -ForegroundColor Yellow
Write-Host "Source Ontology Dir: $SourceOntologiesDir" -ForegroundColor Yellow
Write-Host ""

# Get storage account key
Write-Host "Retrieving storage account key..." -ForegroundColor Green
$storageKey = az storage account keys list `
    --resource-group $ResourceGroup `
    --account-name $StorageAccountName `
    --query "[0].value" `
    --output tsv

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to retrieve storage account key" -ForegroundColor Red
    exit 1
}

Write-Host "Storage key retrieved successfully" -ForegroundColor Green

# Upload RDF files if directory exists
if (Test-Path $SourceRdfDir) {
    Write-Host ""
    Write-Host "Uploading RDF files from $SourceRdfDir..." -ForegroundColor Green
    
    $rdfFiles = Get-ChildItem -Path $SourceRdfDir -File -Recurse -Include *.ttl,*.nt,*.rdf,*.owl
    Write-Host "Found $($rdfFiles.Count) RDF files to upload" -ForegroundColor Cyan
    
    foreach ($file in $rdfFiles) {
        $relativePath = $file.FullName.Substring((Resolve-Path $SourceRdfDir).Path.Length + 1)
        $blobName = "rdf/$relativePath" -replace '\\', '/'
        
        Write-Host "  Uploading: $($file.Name) -> $blobName" -ForegroundColor Gray
        
        az storage blob upload `
            --account-name $StorageAccountName `
            --account-key $storageKey `
            --container-name $ContainerName `
            --name $blobName `
            --file $file.FullName `
            --overwrite true `
            --output none
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  WARNING: Failed to upload $($file.Name)" -ForegroundColor Yellow
        }
    }
    
    Write-Host "RDF files upload complete" -ForegroundColor Green
} else {
    Write-Host "WARNING: RDF directory not found: $SourceRdfDir" -ForegroundColor Yellow
}

# Upload ontology files if directory exists
if (Test-Path $SourceOntologiesDir) {
    Write-Host ""
    Write-Host "Uploading ontology files from $SourceOntologiesDir..." -ForegroundColor Green
    
    $ontologyFiles = Get-ChildItem -Path $SourceOntologiesDir -File -Recurse -Include *.ttl,*.owl,*.rdf
    Write-Host "Found $($ontologyFiles.Count) ontology files to upload" -ForegroundColor Cyan
    
    foreach ($file in $ontologyFiles) {
        $relativePath = $file.FullName.Substring((Resolve-Path $SourceOntologiesDir).Path.Length + 1)
        $blobName = "ontologies/$relativePath" -replace '\\', '/'
        
        Write-Host "  Uploading: $($file.Name) -> $blobName" -ForegroundColor Gray
        
        az storage blob upload `
            --account-name $StorageAccountName `
            --account-key $storageKey `
            --container-name $ContainerName `
            --name $blobName `
            --file $file.FullName `
            --overwrite true `
            --output none
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  WARNING: Failed to upload $($file.Name)" -ForegroundColor Yellow
        }
    }
    
    Write-Host "Ontology files upload complete" -ForegroundColor Green
} else {
    Write-Host "WARNING: Ontologies directory not found: $SourceOntologiesDir" -ForegroundColor Yellow
}

# List uploaded blobs for verification
Write-Host ""
Write-Host "Listing uploaded blobs..." -ForegroundColor Green
az storage blob list `
    --account-name $StorageAccountName `
    --account-key $storageKey `
    --container-name $ContainerName `
    --query "[].{Name:name, Size:properties.contentLength}" `
    --output table

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Upload Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Blob URLs will be in format:" -ForegroundColor Yellow
Write-Host "https://$StorageAccountName.blob.core.windows.net/$ContainerName/<path>/<filename>" -ForegroundColor Gray
Write-Host ""
Write-Host "Update your environment variables to point to these URLs:" -ForegroundColor Yellow
Write-Host "  CAIG_GRAPH_SOURCE_PATH=https://$StorageAccountName.blob.core.windows.net/$ContainerName/rdf/<filename>.nt" -ForegroundColor Gray
Write-Host "  CAIG_GRAPH_SOURCE_OWL_FILENAME=https://$StorageAccountName.blob.core.windows.net/$ContainerName/ontologies/<filename>.owl" -ForegroundColor Gray
Write-Host ""
