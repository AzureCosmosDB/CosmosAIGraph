
using './caig.bicep'

param acaEnvironmentName = readEnvironmentVariable('CAIG_ACA_ENVIRONMENT_NAME')
param azureOpenaiCompletionsDep = readEnvironmentVariable('CAIG_AZURE_OPENAI_COMPLETIONS_DEP')
param azureOpenaiEmbeddingsDep = readEnvironmentVariable('CAIG_AZURE_OPENAI_EMBEDDINGS_DEP')
param azureOpenaiKey = readEnvironmentVariable('CAIG_AZURE_OPENAI_KEY')
param azureOpenaiUrl = readEnvironmentVariable('CAIG_AZURE_OPENAI_URL')
param azureRegion = readEnvironmentVariable('CAIG_AZURE_REGION')
param configContainer = readEnvironmentVariable('CAIG_CONFIG_CONTAINER')
param conversationsContainer = readEnvironmentVariable('CAIG_CONVERSATIONS_CONTAINER')
param cosmosdbNosqlAcct = readEnvironmentVariable('CAIG_COSMOSDB_NOSQL_ACCT')
param cosmosdbNosqlKey = readEnvironmentVariable('CAIG_COSMOSDB_NOSQL_KEY')
param cosmosdbNosqlRg = readEnvironmentVariable('CAIG_COSMOSDB_NOSQL_RG')
param cosmosdbNosqlUri = readEnvironmentVariable('CAIG_COSMOSDB_NOSQL_URI')
param definedAuthUsers = readEnvironmentVariable('CAIG_DEFINED_AUTH_USERS')
//param encryptionSymmetricKey = readEnvironmentVariable('CAIG_ENCRYPTION_SYMMETRIC_KEY')
param feedbackContainer = readEnvironmentVariable('CAIG_FEEDBACK_CONTAINER')
param graphNamespace = readEnvironmentVariable('CAIG_GRAPH_NAMESPACE')
param graphServiceName = readEnvironmentVariable('CAIG_GRAPH_SERVICE_NAME')
param graphServicePort = readEnvironmentVariable('CAIG_GRAPH_SERVICE_PORT')
//param graphServiceUrl = readEnvironmentVariable('CAIG_GRAPH_SERVICE_URL')
param graphSourceContainer = readEnvironmentVariable('CAIG_GRAPH_SOURCE_CONTAINER')
param graphSourceDb = readEnvironmentVariable('CAIG_GRAPH_SOURCE_DB')
param graphSourceOwlFilename = readEnvironmentVariable('CAIG_GRAPH_SOURCE_OWL_FILENAME')
param graphSourcePath = readEnvironmentVariable('CAIG_GRAPH_SOURCE_PATH')
param graphSourceType = readEnvironmentVariable('CAIG_GRAPH_SOURCE_TYPE')
param laWorkspaceName = readEnvironmentVariable('CAIG_LA_WORKSPACE_NAME')
param logLevel = readEnvironmentVariable('CAIG_LOG_LEVEL')
param websvcAuthHeader = readEnvironmentVariable('CAIG_WEBSVC_AUTH_HEADER')
param websvcAuthValue = readEnvironmentVariable('CAIG_WEBSVC_AUTH_VALUE')
param webAppName = readEnvironmentVariable('CAIG_WEB_APP_NAME')

// Graph backend selection. Default 'in_memory' (in-process Jena, no Fuseki).
// Set CAIG_GRAPH_BACKEND=fuseki to deploy the Apache Jena Fuseki Container App
// as the secondary backend option.
param graphBackend = readEnvironmentVariable('CAIG_GRAPH_BACKEND', 'in_memory')
param fusekiServiceName = readEnvironmentVariable('CAIG_FUSEKI_SERVICE_NAME', 'fuseki')
param fusekiAdminPassword = readEnvironmentVariable('CAIG_FUSEKI_ADMIN_PASSWORD', 'admin')

// Apache Jena MCP server (deployed only when graphBackend == 'fuseki').
// The deploy script builds the image with `az acr build` from the separate
// github.com/alekseys/mcp-jena repo and sets these values automatically.
param mcpServerName = readEnvironmentVariable('CAIG_MCP_SERVER_NAME', 'mcp-jena')
param mcpServerImage = readEnvironmentVariable('CAIG_MCP_SERVER_IMAGE', 'mcp-jena:latest')
param mcpApiKey = readEnvironmentVariable('CAIG_MCP_API_KEY', '')
param acrLoginServer = readEnvironmentVariable('CAIG_ACR_LOGIN_SERVER', '')
param acrUsername = readEnvironmentVariable('CAIG_ACR_USERNAME', '')
param acrPassword = readEnvironmentVariable('CAIG_ACR_PASSWORD', '')
