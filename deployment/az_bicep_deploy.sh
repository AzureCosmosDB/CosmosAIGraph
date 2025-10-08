#!/bin/bash

# Deploy the Azure Container Apps (ACA) using Bicep.
# Replace the values of the variables with your own values.

RESOURCE_GROUP="<YOUR_RESOURCE_GROUP_NAME>"
REGION="<YOUR_REGION>"

echo "az group create ..."
az group create --name "$RESOURCE_GROUP" --location "$REGION"

echo "az deployment group create with bicep ..."
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file caig.bicep \
    --parameters caig.bicepparam \
    --only-show-errors