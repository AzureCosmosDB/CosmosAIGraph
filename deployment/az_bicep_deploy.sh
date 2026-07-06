#!/bin/bash

# Deploy the Azure Container Apps (ACA) using Bicep.
# Replace the values of the variables with your own values.

RESOURCE_GROUP="<YOUR_RESOURCE_GROUP_NAME>"
REGION="<YOUR_REGION>"

# --- Deployment infrastructure settings (Bicep inputs; NOT read by local execution,
#     so they live here rather than in a user env script) ---
ACA_ENVIRONMENT_NAME="caig-aca-env"    # ACA managed environment to create
LA_WORKSPACE_NAME="caig-law"           # Log Analytics workspace to create
COSMOSDB_NOSQL_RG="$RESOURCE_GROUP"    # RG of your EXISTING Cosmos DB account (change if different)
DEFINED_AUTH_USERS=""                  # comma-separated ACA users (optional)
GRAPH_SERVICE_NAME="caig-graph"        # ACA app name for the graph service
WEB_APP_NAME="caig-web"                # ACA app name for the web app

# --- Graph backend (deployment-specific option, like RESOURCE_GROUP / REGION above) ---
# 'in_memory' (default): deploy the web + graph Container Apps only.
# 'fuseki'             : additionally deploy the Apache Jena Fuseki triple store and
#                        the MCP server Container Apps.
GRAPH_BACKEND="in_memory"
FUSEKI_SERVICE_NAME="fuseki"    # ACA app name for Fuseki    (used when 'fuseki')
MCP_SERVER_NAME="mcp-jena"     # ACA app name for MCP server (used when 'fuseki')

# Optional: pin secrets to stable values across redeploys. If left unset, the script
# auto-generates strong random values (the Fuseki password is internal; the MCP API
# key is printed at the end so you can configure Foundry IQ).
# export CAIG_FUSEKI_ADMIN_PASSWORD="<your-fuseki-admin-password>"
# export CAIG_MCP_API_KEY="<your-mcp-api-key>"

# Publish the deployment settings to the environment variables that caig.bicepparam reads.
export CAIG_ACA_ENVIRONMENT_NAME="$ACA_ENVIRONMENT_NAME"
export CAIG_AZURE_REGION="$REGION"
export CAIG_COSMOSDB_NOSQL_RG="$COSMOSDB_NOSQL_RG"
export CAIG_LA_WORKSPACE_NAME="$LA_WORKSPACE_NAME"
export CAIG_DEFINED_AUTH_USERS="$DEFINED_AUTH_USERS"
export CAIG_GRAPH_SERVICE_NAME="$GRAPH_SERVICE_NAME"
export CAIG_WEB_APP_NAME="$WEB_APP_NAME"
export CAIG_GRAPH_BACKEND="$GRAPH_BACKEND"
export CAIG_FUSEKI_SERVICE_NAME="$FUSEKI_SERVICE_NAME"
export CAIG_MCP_SERVER_NAME="$MCP_SERVER_NAME"

# MCP server repo, built server-side with `az acr build` (no Docker / docker login /
# clone) when GRAPH_BACKEND = 'fuseki'.
MCP_JENA_REPO="https://github.com/alekseys/mcp-jena.git"

echo "az group create ..."
# Optional RG tags (e.g. internal security-policy exemptions such as
# 'SecurityControl=Ignore') come from the gitignored env script via CAIG_RG_TAGS,
# so the value stays out of the public repo. Applied at creation, before any resources.
if [ -z "$CAIG_RG_TAGS" ]; then
    az group create --name "$RESOURCE_GROUP" --location "$REGION"
else
    az group create --name "$RESOURCE_GROUP" --location "$REGION" --tags $CAIG_RG_TAGS
fi

# Build the MCP server image and wire up its config (Fuseki backend only).
if [ "$GRAPH_BACKEND" = "fuseki" ]; then
    # 0. Auto-generate a strong Fuseki admin password when unset (avoids the weak
    #    'admin' default). It is shared by the Fuseki container (ADMIN_PASSWORD),
    #    the graph app (CAIG_FUSEKI_PASSWORD), and the MCP server (JENA_PASSWORD),
    #    all set from the single fusekiAdminPassword Bicep parameter.
    if [ -z "$CAIG_FUSEKI_ADMIN_PASSWORD" ]; then
        export CAIG_FUSEKI_ADMIN_PASSWORD="$(openssl rand -hex 24)"
        echo ""
        echo "Generated Fuseki admin password (internal only; graph app + MCP share it)."
    fi

    # 1. Auto-generate a strong MCP API key if the caller didn't supply one.
    if [ -z "$CAIG_MCP_API_KEY" ]; then
        export CAIG_MCP_API_KEY="$(openssl rand -hex 32)"
        echo ""
        echo "Generated MCP API key (save this - Foundry IQ uses it as the bearer token):"
        echo "  $CAIG_MCP_API_KEY"
    fi

    # 2. Ensure an Azure Container Registry (idempotent). The name is derived
    #    deterministically from the resource group + subscription, fresh each run, so
    #    switching RESOURCE_GROUP always targets the matching registry (no stale caching).
    SUB_ID="$(az account show --query id -o tsv)"
    HASH="$(printf '%s' "${RESOURCE_GROUP}${SUB_ID}" | sha256sum | cut -c1-12)"
    ACR_NAME="caig${HASH}"
    echo ""
    echo "Ensuring Azure Container Registry '$ACR_NAME' ..."
    az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --admin-enabled true --only-show-errors || { echo "ERROR: az acr create failed"; exit 1; }

    # 3. Build the image directly from the Git repo, server-side (uses your az login).
    #    Skip the build if the image already exists in the ACR (re-runs are fast and
    #    don't queue on ACR Tasks agents). Set CAIG_MCP_FORCE_BUILD=1 to force a rebuild.
    if [ -z "$CAIG_MCP_FORCE_BUILD" ] && az acr repository show --name "$ACR_NAME" --image mcp-jena:latest --only-show-errors -o none 2>/dev/null; then
        echo "MCP image already present in ACR - skipping build (set CAIG_MCP_FORCE_BUILD=1 to rebuild)."
    else
        echo "Building MCP image from $MCP_JENA_REPO via ACR Tasks ..."
        az acr build --registry "$ACR_NAME" --image mcp-jena:latest "$MCP_JENA_REPO" --only-show-errors || { echo "ERROR: az acr build failed"; exit 1; }
    fi

    # 4. Export the image + registry credentials for the Bicep parameters.
    export CAIG_ACR_LOGIN_SERVER="$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)"
    export CAIG_MCP_SERVER_IMAGE="${CAIG_ACR_LOGIN_SERVER}/mcp-jena:latest"
    export CAIG_ACR_USERNAME="$(az acr credential show --name "$ACR_NAME" --query username -o tsv)"
    export CAIG_ACR_PASSWORD="$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)"
    echo "MCP image built: $CAIG_MCP_SERVER_IMAGE"
fi

echo "az deployment group create with bicep ..."
az deployment group create \
    --name caig-deploy \
    --resource-group "$RESOURCE_GROUP" \
    --template-file caig.bicep \
    --parameters caig.bicepparam \
    --only-show-errors \
    --output none || { echo "ERROR: Deployment failed"; exit 1; }

echo "Deployment completed successfully"

# --- Grant the Container Apps' managed identities access to Azure OpenAI (RBAC) ---
# The Azure OpenAI / AI Services resource is provisioned OUTSIDE this template and may
# have key-based auth disabled (403 AuthenticationTypeDisabled). The apps authenticate
# with their system-assigned managed identity via Microsoft Entra ID; the app code
# (ai_service.py) prefers RBAC and only falls back to CAIG_AZURE_OPENAI_KEY. Grant each
# identity the built-in 'Cognitive Services OpenAI User' data-plane role.
WEB_PRINCIPAL_ID="$(az deployment group show -g "$RESOURCE_GROUP" -n caig-deploy --query 'properties.outputs.webAppPrincipalId.value' -o tsv)"
GRAPH_PRINCIPAL_ID="$(az deployment group show -g "$RESOURCE_GROUP" -n caig-deploy --query 'properties.outputs.graphServicePrincipalId.value' -o tsv)"

# Resolve the Azure OpenAI resource id from its endpoint host (resource name = first
# label of the host, e.g. https://alesai.services.ai.azure.com -> 'alesai').
AOAI_NAME="$(printf '%s' "$CAIG_AZURE_OPENAI_URL" | sed -E 's#^https?://##; s#\..*##')"
AOAI_RESOURCE_ID="$(az cognitiveservices account list --query "[?name=='$AOAI_NAME'].id | [0]" -o tsv)"
if [ -z "$AOAI_RESOURCE_ID" ]; then
    echo "WARNING: could not locate Azure OpenAI resource '$AOAI_NAME' in this subscription."
    echo "         Grant 'Cognitive Services OpenAI User' to the app identities manually."
else
    echo "Granting 'Cognitive Services OpenAI User' on '$AOAI_NAME' to the app identities..."
    for PRINCIPAL_ID in "$WEB_PRINCIPAL_ID" "$GRAPH_PRINCIPAL_ID"; do
        [ -z "$PRINCIPAL_ID" ] && continue
        az role assignment create \
            --assignee-object-id "$PRINCIPAL_ID" \
            --assignee-principal-type ServicePrincipal \
            --role "Cognitive Services OpenAI User" \
            --scope "$AOAI_RESOURCE_ID" \
            --only-show-errors --output none
    done
    echo "Role assignments applied (allow ~1-2 min for RBAC propagation)."
fi

# --- Grant the same managed identities data-plane access to Cosmos DB (RBAC) ---
# cosmos_nosql_service.py uses the identical RBAC-first / key-fallback pattern. Cosmos
# NoSQL DATA-plane access needs a Cosmos-SPECIFIC role assignment (az cosmosdb sql role
# assignment), NOT the control-plane 'az role assignment'. Role definition id
# 00000000-0000-0000-0000-000000000002 is the built-in 'Cosmos DB Built-in Data
# Contributor' (read+write; the app writes to the conversations/feedback containers).
COSMOS_DATA_CONTRIBUTOR_ROLE_ID="00000000-0000-0000-0000-000000000002"
COSMOS_ACCT="$CAIG_COSMOSDB_NOSQL_ACCT"
if [ -z "$COSMOS_ACCT" ]; then
    COSMOS_ACCT="$(printf '%s' "$CAIG_COSMOSDB_NOSQL_URI" | sed -E 's#^https?://##; s#\..*##')"
fi
if [ -z "$COSMOS_ACCT" ] || [ -z "$CAIG_COSMOSDB_NOSQL_RG" ]; then
    echo "WARNING: Cosmos DB account/RG unknown; skipping data-plane role assignment."
    echo "         Set CAIG_COSMOSDB_NOSQL_ACCT / CAIG_COSMOSDB_NOSQL_RG, or assign the"
    echo "         'Cosmos DB Built-in Data Contributor' role to the app identities manually."
else
    echo "Granting 'Cosmos DB Built-in Data Contributor' on '$COSMOS_ACCT' to the app identities..."
    for PRINCIPAL_ID in "$WEB_PRINCIPAL_ID" "$GRAPH_PRINCIPAL_ID"; do
        [ -z "$PRINCIPAL_ID" ] && continue
        # az cosmosdb sql role assignment create is NOT idempotent (it mints a new GUID
        # each run), so skip when an equivalent assignment already exists.
        EXISTING="$(az cosmosdb sql role assignment list --account-name "$COSMOS_ACCT" --resource-group "$CAIG_COSMOSDB_NOSQL_RG" --query "[?principalId=='$PRINCIPAL_ID' && contains(roleDefinitionId, '$COSMOS_DATA_CONTRIBUTOR_ROLE_ID')] | [0].id" -o tsv)"
        if [ -z "$EXISTING" ]; then
            az cosmosdb sql role assignment create \
                --account-name "$COSMOS_ACCT" \
                --resource-group "$CAIG_COSMOSDB_NOSQL_RG" \
                --scope "/" \
                --principal-id "$PRINCIPAL_ID" \
                --role-definition-id "$COSMOS_DATA_CONTRIBUTOR_ROLE_ID" \
                --only-show-errors --output none
        fi
    done
    echo "Cosmos DB role assignments applied (allow ~1-2 min for RBAC propagation)."
fi

# Read deployment outputs (via az --query, no jq dependency).
STORAGE_ACCOUNT="$(az deployment group show -g "$RESOURCE_GROUP" -n caig-deploy --query 'properties.outputs.storageAccountName.value' -o tsv)"
STORAGE_CONTAINER="$(az deployment group show -g "$RESOURCE_GROUP" -n caig-deploy --query 'properties.outputs.storageContainerName.value' -o tsv)"
WEB_FQDN="$(az deployment group show -g "$RESOURCE_GROUP" -n caig-deploy --query 'properties.outputs.webAppFqdn.value' -o tsv)"
GRAPH_FQDN="$(az deployment group show -g "$RESOURCE_GROUP" -n caig-deploy --query 'properties.outputs.graphServiceFqdn.value' -o tsv)"
MCP_ENDPOINT="$(az deployment group show -g "$RESOURCE_GROUP" -n caig-deploy --query 'properties.outputs.mcpServerEndpoint.value' -o tsv)"

echo ""
echo "Storage Account: $STORAGE_ACCOUNT"
echo "Container Name:  $STORAGE_CONTAINER"

# Surface the MCP server endpoint + API key when the Fuseki backend is used.
if [ -n "$MCP_ENDPOINT" ]; then
    echo ""
    echo "MCP server (Foundry IQ Knowledge Source):"
    echo "  Endpoint : $MCP_ENDPOINT"
    echo "  API key  : $CAIG_MCP_API_KEY"
    echo "  Configure Foundry IQ with this URL and the API key as the bearer token."
fi

# Upload RDF and ontology assets to the (private) storage account.
echo ""
echo "Uploading RDF and ontology assets..."
STORAGE_KEY="$(az storage account keys list -g "$RESOURCE_GROUP" -n "$STORAGE_ACCOUNT" --query '[0].value' -o tsv)"
if [ -n "$STORAGE_KEY" ]; then
    if [ -d "../impl/graph_app/rdf" ]; then
        az storage blob upload-batch --account-name "$STORAGE_ACCOUNT" --account-key "$STORAGE_KEY" \
            --destination "$STORAGE_CONTAINER" --destination-path rdf --source "../impl/graph_app/rdf" \
            --overwrite --only-show-errors --output none
    fi
    if [ -d "../impl/graph_app/ontologies" ]; then
        az storage blob upload-batch --account-name "$STORAGE_ACCOUNT" --account-key "$STORAGE_KEY" \
            --destination "$STORAGE_CONTAINER" --destination-path ontologies --source "../impl/graph_app/ontologies" \
            --overwrite --only-show-errors --output none
    fi
    echo "Asset upload complete."
else
    echo "WARNING: could not read the storage key; skipped asset upload."
fi

# --- Point the graph app at the (private) blob assets via a read-only SAS ---
# The uploaded blob name equals the local relative path, so the URL is
# <blobBase>/<relative-path>?<SAS>. The graph app tolerates an unreachable source at
# first startup (empty model), so updating these env vars triggers a new revision
# that loads the real data.
REWRITE_OWL=false
REWRITE_PATH=false
case "$CAIG_GRAPH_SOURCE_OWL_FILENAME" in
    ""|http://*|https://*) ;;
    *) REWRITE_OWL=true ;;
esac
if [ "$CAIG_GRAPH_SOURCE_TYPE" = "rdf_file" ] || [ "$CAIG_GRAPH_SOURCE_TYPE" = "json_docs_file" ]; then
    case "$CAIG_GRAPH_SOURCE_PATH" in
        ""|http://*|https://*) ;;
        *) REWRITE_PATH=true ;;
    esac
fi

if [ "$REWRITE_OWL" = true ] || [ "$REWRITE_PATH" = true ]; then
    echo ""
    echo "Wiring the graph app to the private blob assets via a read-only SAS..."
    [ -z "$STORAGE_KEY" ] && STORAGE_KEY="$(az storage account keys list -g "$RESOURCE_GROUP" -n "$STORAGE_ACCOUNT" --query '[0].value' -o tsv)"
    SAS_EXPIRY="$(date -u -d '+1 year' '+%Y-%m-%dT%H:%MZ' 2>/dev/null || date -u -v+1y '+%Y-%m-%dT%H:%MZ')"
    SAS_TOKEN="$(az storage container generate-sas -n "$STORAGE_CONTAINER" --account-name "$STORAGE_ACCOUNT" --account-key "$STORAGE_KEY" --permissions r --expiry "$SAS_EXPIRY" --https-only -o tsv)"
    if [ -z "$SAS_TOKEN" ]; then echo "ERROR: could not generate the SAS token"; exit 1; fi
    BLOB_BASE="https://${STORAGE_ACCOUNT}.blob.core.windows.net/${STORAGE_CONTAINER}"
    if [ "$REWRITE_OWL" = true ]; then
        export CAIG_GRAPH_SOURCE_OWL_FILENAME="${BLOB_BASE}/${CAIG_GRAPH_SOURCE_OWL_FILENAME}?${SAS_TOKEN}"
    fi
    if [ "$REWRITE_PATH" = true ]; then
        export CAIG_GRAPH_SOURCE_PATH="${BLOB_BASE}/${CAIG_GRAPH_SOURCE_PATH}?${SAS_TOKEN}"
    fi
    echo "Redeploying so the graph app loads the assets from blob storage..."
    # Re-run Bicep (not 'az containerapp update') so the SAS URLs are read from the
    # environment by the Bicep engine, avoiding '&' issues on the command line.
    az deployment group create --name caig-deploy --resource-group "$RESOURCE_GROUP" \
        --template-file caig.bicep --parameters caig.bicepparam --only-show-errors --output none \
        || { echo "ERROR: redeploy to apply the SAS blob URLs failed"; exit 1; }
    echo "Graph app redeployed - it will load the model from blob storage."
fi

echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "Next Steps:"
echo "1. The graph app was automatically pointed at the RDF/ontology assets in blob"
echo "   storage via a 1-year read-only SAS; its newest revision loads them."
echo "2. Open the web app and check graph health (FQDNs from the deployment outputs):"
echo "     Web:   https://${WEB_FQDN}"
echo "     Graph: https://${GRAPH_FQDN}/liveness"
echo ""