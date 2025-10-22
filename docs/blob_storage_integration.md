# Azure Blob Storage Integration for RDF/Ontology Assets

## Overview

This update enhances the CosmosAIGraph solution to host RDF and ontology assets in Azure Blob Storage rather than embedding them in Docker images. This provides better security, smaller images, and easier asset management.

## Changes Made

### 1. Docker Build Context Updates

**Files Modified:**
- `impl/graph_app/.dockerignore`
- `impl/web_app/.dockerignore`

**Changes:**
- Added exclusions for `ontologies/` and `rdf/` directories
- These directories are no longer copied into Docker images during build

**Benefits:**
- Reduced Docker image size
- Faster build times
- Sensitive ontology definitions kept separate from application code

### 2. Java Runtime Enhancements

**Files Modified:**
- `impl/graph_app/src/main/java/com/microsoft/cosmosdb/caig/util/FileUtil.java`
- `impl/graph_app/src/main/java/com/microsoft/cosmosdb/caig/graph/AppGraphBuilder.java`

**Changes:**

#### FileUtil.java
- Updated `readUnicode()` method to detect and handle both local file paths and HTTPS URLs
- Added `readFromFile()` private method for local file reading
- Added `readFromUrl()` private method for HTTP/HTTPS URL fetching (e.g., Azure Blob Storage)
- Includes proper timeout configuration (30s connect, 60s read)
- Comprehensive error logging

#### AppGraphBuilder.java
- Enhanced `populateFromRdfFile()` to support HTTPS URLs for RDF content
- Enhanced `initializeModel()` to support HTTPS URLs for OWL ontology files
- Detects URL scheme (http:// or https://) and loads content accordingly
- Falls back gracefully to local file loading for development scenarios

**Benefits:**
- Seamless support for both local development (file paths) and production (blob URLs)
- No code changes required when switching between environments
- Automatic content type detection based on file extension (.ttl, .nt, .rdf, .owl)

### 3. Python Runtime Enhancements

**Files Modified:**
- `impl/web_app/src/util/fs.py`

**Changes:**
- Updated `FS.read()` method to detect and handle both local file paths and HTTPS URLs
- Added `_read_from_url()` private method using httpx library
- 60-second timeout for URL fetching
- Comprehensive error logging with HTTPError handling

**Benefits:**
- Consistent behavior with Java implementation
- OntologyService automatically supports blob URLs without modifications
- web_app.py BOM/SPARQL endpoints work with both local and remote ontology files

### 4. Infrastructure as Code (Bicep)

**Files Modified:**
- `deployment/caig.bicep`

**Changes:**
- Added storage account resource (`storageAccount`) with Standard_LRS SKU
- Added blob service resource (`blobService`)
- Added blob container resource (`blobContainer`) with public blob access
- Added parameters: `storageAccountName`, `storageContainerName`
- Added outputs: `storageAccountName`, `storageAccountId`, `storageBlobEndpoint`, `storageContainerName`, `storageContainerUrl`, `graphServiceFqdn`, `webAppFqdn`

**Storage Configuration:**
- Account name uses `uniqueString(resourceGroup().id)` for uniqueness: `caigstore<hash>`
- Container name defaults to `data`
- Public blob access enabled (read-only, no listing)
- TLS 1.2 minimum, HTTPS-only traffic
- Hot access tier for optimal performance

**Benefits:**
- Single Bicep deployment provisions all necessary resources
- Storage account automatically named to avoid conflicts
- Outputs provide necessary information for subsequent scripts

### 5. Deployment Scripts

**Files Created:**
- `deployment/az_upload_rdf_assets.ps1`

**Files Modified:**
- `deployment/az_bicep_deploy.ps1`

**Changes:**

#### az_upload_rdf_assets.ps1 (New)
- PowerShell script to upload RDF and ontology files to Azure Blob Storage
- Parameters: ResourceGroup, StorageAccountName, ContainerName, source directories
- Recursively uploads files from `data/rdf/` and `data/ontologies/` (or custom paths)
- Supports .ttl, .nt, .rdf, .owl file types
- Maintains directory structure in blob storage (e.g., `rdf/<file>`, `ontologies/<file>`)
- Lists uploaded blobs for verification
- Provides example blob URLs for environment variable configuration

#### az_bicep_deploy.ps1 (Updated)
- Captures deployment outputs (storage account name, container name)
- Automatically invokes `az_upload_rdf_assets.ps1` after successful deployment
- Provides user guidance for updating environment variables
- Enhanced console output with color-coded status messages

**Benefits:**
- Single-command deployment workflow
- Automatic asset upload after provisioning
- Clear guidance for post-deployment configuration

### 6. Documentation Updates

**Files Modified:**
- `docs/environment_variables.md`

**Changes:**
- Updated descriptions for `CAIG_GRAPH_SOURCE_PATH` and `CAIG_GRAPH_SOURCE_OWL_FILENAME`
- Added new section: "Azure Blob Storage for RDF/Ontology Assets"
- Documented dual support (local paths vs HTTPS URLs)
- Provided deployment process overview
- Included example blob URLs
- Referenced new deployment scripts

**Benefits:**
- Clear documentation of new capabilities
- Examples for both development and production configurations
- Step-by-step deployment guidance

## Environment Variable Configuration

### Development (Local Files)

```bash
# Single files
CAIG_GRAPH_SOURCE_TYPE=rdf_file
CAIG_GRAPH_SOURCE_PATH=rdf/libraries-graph.nt
CAIG_GRAPH_SOURCE_OWL_FILENAME=ontologies/extracted_ontology.ttl

# Directory of files (loads all .ttl, .nt, .rdf, .owl files)
CAIG_GRAPH_SOURCE_TYPE=rdf_file
CAIG_GRAPH_SOURCE_PATH=rdf/
CAIG_GRAPH_SOURCE_OWL_FILENAME=ontologies/extracted_ontology.ttl
```

### Production (Azure Blob Storage)

```bash
# Single file URLs
CAIG_GRAPH_SOURCE_TYPE=rdf_file
CAIG_GRAPH_SOURCE_PATH=https://caigstore<unique-id>.blob.core.windows.net/data/rdf/libraries-graph.nt
CAIG_GRAPH_SOURCE_OWL_FILENAME=https://caigstore<unique-id>.blob.core.windows.net/data/ontologies/extracted_ontology.ttl

# Directory URL (loads all RDF files with the given prefix)
CAIG_GRAPH_SOURCE_TYPE=rdf_file
CAIG_GRAPH_SOURCE_PATH=https://caigstore<unique-id>.blob.core.windows.net/data/rdf/
CAIG_GRAPH_SOURCE_OWL_FILENAME=https://caigstore<unique-id>.blob.core.windows.net/data/ontologies/extracted_ontology.ttl
```

## Deployment Workflow

1. **Prepare Environment**
   - Ensure Azure CLI is installed and authenticated
   - Update `deployment/caig.bicepparam` with your configuration values

2. **Run Deployment Script**
   ```powershell
   cd deployment
   # Single file deployment
   .\az_bicep_deploy.ps1 -resourceGroupName "rg-caig-demo" -location "eastus" -storageAccountName "caigstore<unique-id>"
   
   # Or configure for directory-based loading
   # Set CAIG_GRAPH_SOURCE_PATH to directory URL after deployment
   ```

3. **Script Actions**
   - Creates resource group
   - Deploys Bicep template (storage, ACA environment, container apps)
   - Extracts storage account name from outputs
   - Uploads RDF/ontology assets to blob container

4. **Update Environment Variables**
   - Note the storage account name from deployment output
   - Update `CAIG_GRAPH_SOURCE_PATH` and `CAIG_GRAPH_SOURCE_OWL_FILENAME` to use blob URLs
   - Redeploy container apps or update via Azure Portal

5. **Verify**
   - Check container app logs to confirm assets are loaded from blob URLs
   - Test graph queries to ensure data is accessible

## Migration from Local Files

If you're currently using local file paths:

1. Deploy the updated Bicep template to provision storage
2. Run `az_upload_rdf_assets.ps1` to upload existing assets
3. Update environment variables to point to blob URLs
4. Restart container apps (if already deployed)

No code changes required - the runtime automatically detects URL schemes!

## Security Considerations

- **Public Blob Access**: The container is configured for public blob access (read-only)
- **No SAS Tokens Required**: Public blobs are accessible via HTTPS without authentication
- **Network Security**: Consider using Private Endpoints for enhanced security in production
- **Container Images**: RDF/ontology assets no longer present in images, reducing attack surface

## Performance

- **HTTP Fetch**: Initial load fetches assets from blob storage (adds ~100-500ms depending on file size and region)
- **Caching**: Consider implementing application-level caching for repeated access
- **Network**: Co-locate storage account in same region as container apps for optimal performance

## Troubleshooting

### Issue: "Failed to load RDF content from URL"
- **Check**: Verify blob URL is correct and publicly accessible
- **Test**: Try accessing URL in browser or via `curl`
- **Logs**: Review container app logs for detailed error messages

### Issue: "Storage account name conflict"
- **Solution**: The Bicep template uses `uniqueString()` to avoid conflicts
- **Manual Override**: Specify `storageAccountName` parameter in bicepparam file

### Issue: Assets not uploaded
- **Check**: Verify source directories exist: `data/rdf/`, `data/ontologies/`
- **Permissions**: Ensure Azure CLI has contributor access to storage account
- **Retry**: Run `az_upload_rdf_assets.ps1` manually with explicit parameters

## Future Enhancements

- **Private Endpoints**: Add support for private blob access via managed identity
- **CDN Integration**: Optional Azure CDN for global distribution and caching
- **Versioning**: Implement blob versioning for asset change tracking
- **Monitoring**: Add Application Insights instrumentation for blob fetch performance

## References

- Bicep Template: `deployment/caig.bicep`
- Upload Script: `deployment/az_upload_rdf_assets.ps1`
- Deployment Script: `deployment/az_bicep_deploy.ps1`
- Documentation: `docs/environment_variables.md`
- Java FileUtil: `impl/graph_app/src/main/java/com/microsoft/cosmosdb/caig/util/FileUtil.java`
- Python FS: `impl/web_app/src/util/fs.py`
