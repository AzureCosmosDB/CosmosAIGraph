# CosmosAIGraph: deployment

Azure Container App deployment scripts

## Links

- https://learn.microsoft.com/en-us/cli/azure/
- https://learn.microsoft.com/en-us/azure/container-apps/tutorial-deploy-first-app-cli



## az CLI

```
> az --version

> az upgrade  (if necessary)

> az login

> az account set --subscription $Env:AZURE_SUBSCRIPTION_ID

> az extension add --name containerapp --upgrade

> az extension list

> az provider register --namespace Microsoft.App

> az provider register --namespace Microsoft.OperationalInsights

> az provider list
```

## Bicep

- https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview?tabs=bicep
- https://learn.microsoft.com/en-us/azure/templates/microsoft.app/containerapps?pivots=deployment-language-bicep#bicep-resource-definition
- https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/parameter-files?tabs=JSON#parameters-file
- https://azureis.fun/posts/Using-Configuration-File-With-Azure-Bicep
- https://learn.microsoft.com/en-us/azure/templates/microsoft.operationalinsights/workspaces?pivots=deployment-language-bicep
- https://learn.microsoft.com/en-us/azure/templates/microsoft.resources/resourcegroups?pivots=deployment-language-bicep
- https://dev.to/willvelida/creating-and-provisioning-azure-container-apps-with-bicep-4gfb
- https://learn.microsoft.com/en-us/azure/templates/microsoft.web/2021-03-01/kubeenvironments?pivots=deployment-language-bicep
- https://learn.microsoft.com/en-us/azure/templates/microsoft.app/managedenvironments?pivots=deployment-language-bicep
- https://learn.microsoft.com/en-us/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli

```
> az bicep version
A new Bicep release is available: v0.24.24. Upgrade now by running "az bicep upgrade".
Bicep CLI version 0.14.46 (ef2ceb1a0e)

> az bicep upgrade
Installing Bicep CLI v0.24.24...
The configuration value of bicep.use_binary_from_path has been set to 'false'.
Successfully installed Bicep CLI to "C:\Users\chjoakim\.azure\bin\bicep.exe".

> az bicep version
Bicep CLI version 0.24.24 (5646341b0c)

az group create --name exampleRG --location eastus
az deployment group create --resource-group exampleRG --template-file main.bicep



az deployment create --template-file main.bicep --parameters main.parameters.json --location SouthCentralUS --parameters environmentName=$env:AZURE_ENV_NAME location=$env:AZURE_LOCATION principalId=$env:AZURE_PRINCIPAL_ID

az deployment create --template-file caig-law.bicep --parameters main.parameters.json --location SouthCentralUS --parameters environmentName=$env:AZURE_ENV_NAME location=$env:AZURE_LOCATION principalId=$env:AZURE_PRINCIPAL_ID
```