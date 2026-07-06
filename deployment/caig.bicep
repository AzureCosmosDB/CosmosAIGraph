// This is the Bicep deployment script for the CosmosAIGraph
// Azure Container Apps (ACA) part of the solution.
// It will deploy the web application and supporting web services
// from public container images on DockerHub.
// Cosmos DB and OpenAI deployment is NOT handled by this script, only ACA.
// This version includes Azure Storage for hosting RDF/ontology assets.

param acaEnvironmentName string
param azureOpenaiCompletionsDep string
param azureOpenaiEmbeddingsDep string
param azureOpenaiKey string
param azureOpenaiUrl string
param azureRegion string
param configContainer string
param conversationsContainer string
param cosmosdbNosqlAcct string
param cosmosdbNosqlKey string
param cosmosdbNosqlRg string
param cosmosdbNosqlUri string
param definedAuthUsers string
//param encryptionSymmetricKey string
param feedbackContainer string
param graphNamespace string
param graphServiceName string
param graphServicePort string
param graphSourceContainer string
param graphSourceDb string
param graphSourceOwlFilename string
param graphSourcePath string
param graphSourceType string
param laWorkspaceName string
param logLevel string
// Graph backend: 'in_memory' (default, in-process Jena) or 'fuseki' (Apache Jena Fuseki sidecar)
param graphBackend string = 'in_memory'
// Admin-UI password for the internal-only Fuseki Container App (only used when graphBackend == 'fuseki').
// This guards the Fuseki admin UI / write endpoints; the graph app authenticates with it.
@secure()
param fusekiAdminPassword string = ''
// Name of the Apache Jena Fuseki Container App (deployed only when graphBackend == 'fuseki').
param fusekiServiceName string = 'fuseki'
// Apache Jena MCP server (https://github.com/alekseys/mcp-jena), deployed as its own
// ACA Container App when graphBackend == 'fuseki'. It exposes the Fuseki dataset over
// Streamable HTTP so Microsoft Foundry IQ can consume it as a Knowledge Source.
param mcpServerName string = 'mcp-jena'
// Container image for the MCP server. The deploy script builds this from the
// separate mcp-jena repo with `az acr build` and sets it to <acr>.azurecr.io/mcp-jena:latest.
param mcpServerImage string = 'mcp-jena:latest'
// API key that remote MCP clients (e.g. Foundry IQ) must present as a Bearer token
// or x-api-key header. The deploy script auto-generates a strong value if unset.
@secure()
param mcpApiKey string = ''
// Azure Container Registry that hosts the MCP image (set by the deploy script when
// graphBackend == 'fuseki'). When acrLoginServer is empty the MCP app pulls from a
// public registry and no pull credentials are configured.
param acrLoginServer string = ''
param acrUsername string = ''
@secure()
param acrPassword string = ''
param websvcAuthHeader string
param websvcAuthValue string
param webAppName string
// Container images for the graph and web apps. Default to the public images on the
// alexsavat Docker Hub namespace; override via CAIG_GRAPH_SERVICE_IMAGE / CAIG_WEB_APP_IMAGE
// (e.g. to an <acr>.azurecr.io/... image). When the image lives in the ACR, pull
// credentials are wired automatically from acrLoginServer/acrUsername/acrPassword.
param graphServiceImage string = 'alexsavat/caig_graph:latest'
param webAppImage string = 'alexsavat/caig_web:latest'
param storageAccountName string = 'caigstore${uniqueString(resourceGroup().id)}'
param storageContainerName string = 'data'


resource law 'Microsoft.OperationalInsights/workspaces@2020-03-01-preview' = {
  name: laWorkspaceName
  location: azureRegion
  properties: any({
    retentionInDays: 30
  })
}

// Storage account for hosting RDF/ontology assets
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: azureRegion
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    // Public blob access is disabled (more secure, and required by common Azure
    // Policies). RDF/ontology assets are read via authenticated URLs (see docs).
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

// Blob service for the storage account
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// Container for RDF and ontology assets
resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: storageContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource acaEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: acaEnvironmentName
  location: azureRegion 
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
    peerAuthentication: {
      mtls: {
        enabled: false
      }
    }
    zoneRedundant: false
  }
}

// Apache Jena Fuseki is deployed as its own internal-only ACA Container App
// (see the 'fuseki' resource below) when graphBackend == 'fuseki'. The graph
// Container App reaches it over the environment-internal ingress FQDN, which has
// the form <app-name>.internal.<defaultDomain>. Building the URL from the
// environment's defaultDomain avoids a conditional-resource reference from the
// always-deployed graph app.
var fusekiInternalFqdn = '${fusekiServiceName}.internal.${acaEnvironment.properties.defaultDomain}'
var fusekiDatasetUrl = graphBackend == 'fuseki' ? 'http://${fusekiInternalFqdn}/caig' : 'http://localhost:3030/caig'

// The graph/web images default to public Docker Hub (no pull creds needed). Pull creds
// are only wired when an image is overridden to one hosted in the ACR (acrLoginServer).
// acrRegistries/acrSecrets are defined further below (near the MCP resource).
var graphUsesAcr = !empty(acrLoginServer) && contains(graphServiceImage, acrLoginServer)
var webUsesAcr = !empty(acrLoginServer) && contains(webAppImage, acrLoginServer)

resource graph 'Microsoft.App/containerApps@2023-05-01' = {
  name: graphServiceName
  location: azureRegion
  properties: {
    environmentId: acaEnvironment.id
    configuration: {
      registries: graphUsesAcr ? acrRegistries : []
      secrets: graphUsesAcr ? acrSecrets : []
      ingress: {
        allowInsecure: true
        clientCertificateMode: 'ignore'
        targetPort: 8001
        external: true
        stickySessions: {
          affinity: 'none'
        }
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          image: graphServiceImage
          name: graphServiceName
          env: [
            {
              name: 'CAIG_ACA_ENVIRONMENT_NAME'
              value: acaEnvironmentName
            }
            {
              name: 'CAIG_AZURE_OPENAI_COMPLETIONS_DEP'
              value: azureOpenaiCompletionsDep
            }
            {
              name: 'CAIG_AZURE_OPENAI_EMBEDDINGS_DEP'
              value: azureOpenaiEmbeddingsDep
            }
            {
              name: 'CAIG_AZURE_OPENAI_KEY'
              value: azureOpenaiKey
            }
            {
              name: 'CAIG_AZURE_OPENAI_URL'
              value: azureOpenaiUrl
            }
            {
              name: 'CAIG_AZURE_REGION'
              value: azureRegion
            }
            {
              name: 'CAIG_CONFIG_CONTAINER'
              value: configContainer
            }
            {
              name: 'CAIG_CONVERSATIONS_CONTAINER'
              value: conversationsContainer
            }
            {
              name: 'CAIG_COSMOSDB_NOSQL_ACCT'
              value: cosmosdbNosqlAcct
            }
            {
              name: 'CAIG_COSMOSDB_NOSQL_KEY'
              value: cosmosdbNosqlKey
            }
            {
              name: 'CAIG_COSMOSDB_NOSQL_RG'
              value: cosmosdbNosqlRg
            }
            {
              name: 'CAIG_COSMOSDB_NOSQL_URI'
              value: cosmosdbNosqlUri
            }
            {
              name: 'CAIG_DEFINED_AUTH_USERS'
              value: definedAuthUsers
            }
            // {
            //   name: 'CAIG_ENCRYPTION_SYMMETRIC_KEY'
            //   value: encryptionSymmetricKey
            // }
            {
              name: 'CAIG_FEEDBACK_CONTAINER'
              value: feedbackContainer
            }
            {
              name: 'CAIG_GRAPH_NAMESPACE'
              value: graphNamespace
            }
            {
              name: 'CAIG_GRAPH_SERVICE_NAME'
              value: graphServiceName
            }
            {
              name: 'CAIG_GRAPH_SOURCE_CONTAINER'
              value: graphSourceContainer
            }
            {
              name: 'CAIG_GRAPH_SOURCE_DB'
              value: graphSourceDb
            }
            {
              name: 'CAIG_GRAPH_SOURCE_OWL_FILENAME'
              value: graphSourceOwlFilename
            }
            {
              name: 'CAIG_GRAPH_SOURCE_PATH'
              value: graphSourcePath
            }
            {
              name: 'CAIG_GRAPH_SOURCE_TYPE'
              value: graphSourceType
            }
            {
              name: 'CAIG_LA_WORKSPACE_NAME'
              value: laWorkspaceName
            }
            {
              name: 'CAIG_LOG_LEVEL'
              value: logLevel
            }
            {
              name: 'CAIG_WEBSVC_AUTH_HEADER'
              value: websvcAuthHeader
            }
            {
              name: 'CAIG_WEBSVC_AUTH_VALUE'
              value: websvcAuthValue
            }
            {
              name: 'CAIG_WEB_APP_NAME'
              value: webAppName
            }
            {
              name: 'CAIG_GRAPH_BACKEND'
              value: graphBackend
            }
            {
              name: 'CAIG_FUSEKI_DATASET_URL'
              value: fusekiDatasetUrl
            }
            {
              name: 'CAIG_FUSEKI_USER'
              value: 'admin'
            }
            {
              name: 'CAIG_FUSEKI_PASSWORD'
              value: empty(fusekiAdminPassword) ? 'admin' : fusekiAdminPassword
            }
          ]
          probes: [
            {
              type: 'liveness'
              failureThreshold: 5
              httpGet: {
                path: '/liveness'
                port:  8001
                scheme: 'http'
              }
              initialDelaySeconds: 60
              periodSeconds: 120
              successThreshold: 1
              timeoutSeconds: 10
            }
          ]
        }
      ]
      scale: {
        maxReplicas: 2
        minReplicas: 1
      }
      terminationGracePeriodSeconds: 30
    }
  }
}


resource web 'Microsoft.App/containerApps@2023-05-01' = {
  name: webAppName
  location: azureRegion
  properties: {
    environmentId: acaEnvironment.id
    configuration: {
      registries: webUsesAcr ? acrRegistries : []
      secrets: webUsesAcr ? acrSecrets : []
      ingress: {
        allowInsecure: true
        clientCertificateMode: 'ignore'
        targetPort: 8000
        external: true
        stickySessions: {
          affinity: 'none'
        }
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          image: webAppImage
          name: webAppName
          env: [
            {
              name: 'CAIG_GRAPH_SERVICE_URL'
              value: 'http://${graph.properties.configuration.ingress.fqdn}'
            }
            {
              name: 'CAIG_GRAPH_SERVICE_PORT'
              value: '80'
            }

            {
              name: 'CAIG_ACA_ENVIRONMENT_NAME'
              value: acaEnvironmentName
            }
            {
              name: 'CAIG_AZURE_OPENAI_COMPLETIONS_DEP'
              value: azureOpenaiCompletionsDep
            }
            {
              name: 'CAIG_AZURE_OPENAI_EMBEDDINGS_DEP'
              value: azureOpenaiEmbeddingsDep
            }
            {
              name: 'CAIG_AZURE_OPENAI_KEY'
              value: azureOpenaiKey
            }
            {
              name: 'CAIG_AZURE_OPENAI_URL'
              value: azureOpenaiUrl
            }
            {
              name: 'CAIG_AZURE_REGION'
              value: azureRegion
            }
            {
              name: 'CAIG_CONFIG_CONTAINER'
              value: configContainer
            }
            {
              name: 'CAIG_CONVERSATIONS_CONTAINER'
              value: conversationsContainer
            }
            {
              name: 'CAIG_COSMOSDB_NOSQL_ACCT'
              value: cosmosdbNosqlAcct
            }
            {
              name: 'CAIG_COSMOSDB_NOSQL_KEY'
              value: cosmosdbNosqlKey
            }
            {
              name: 'CAIG_COSMOSDB_NOSQL_RG'
              value: cosmosdbNosqlRg
            }
            {
              name: 'CAIG_COSMOSDB_NOSQL_URI'
              value: cosmosdbNosqlUri
            }
            {
              name: 'CAIG_DEFINED_AUTH_USERS'
              value: definedAuthUsers
            }
            // {
            //   name: 'CAIG_ENCRYPTION_SYMMETRIC_KEY'
            //   value: encryptionSymmetricKey
            // }
            {
              name: 'CAIG_FEEDBACK_CONTAINER'
              value: feedbackContainer
            }
            {
              name: 'CAIG_GRAPH_NAMESPACE'
              value: graphNamespace
            }
            {
              name: 'CAIG_GRAPH_SERVICE_NAME'
              value: graphServiceName
            }
            {
              name: 'CAIG_GRAPH_SOURCE_CONTAINER'
              value: graphSourceContainer
            }
            {
              name: 'CAIG_GRAPH_SOURCE_DB'
              value: graphSourceDb
            }
            {
              name: 'CAIG_GRAPH_SOURCE_OWL_FILENAME'
              value: graphSourceOwlFilename
            }
            {
              name: 'CAIG_GRAPH_SOURCE_PATH'
              value: graphSourcePath
            }
            {
              name: 'CAIG_GRAPH_SOURCE_TYPE'
              value: graphSourceType
            }
            {
              name: 'CAIG_LA_WORKSPACE_NAME'
              value: laWorkspaceName
            }
            {
              name: 'CAIG_LOG_LEVEL'
              value: logLevel
            }
            {
              name: 'CAIG_WEBSVC_AUTH_HEADER'
              value: websvcAuthHeader
            }
            {
              name: 'CAIG_WEBSVC_AUTH_VALUE'
              value: websvcAuthValue
            }
            {
              name: 'CAIG_WEB_APP_NAME'
              value: webAppName
            }
          ]
          probes: [
            {
              type: 'liveness'
              failureThreshold: 5
              httpGet: {
                path: '/liveness'
                port:  8000
                scheme: 'http'
              }
              initialDelaySeconds: 60
              periodSeconds: 120
              successThreshold: 1
              timeoutSeconds: 10
            }
          ]
        }
      ]
      scale: {
        maxReplicas: 2
        minReplicas: 1
      }
      terminationGracePeriodSeconds: 10
    }
  }
}

// Apache Jena Fuseki triple store, deployed as its own ACA Container App (the
// same way as the web and graph apps) when graphBackend == 'fuseki'. This is the
// secondary deployment option; the default 'in_memory' backend does not deploy it.
// Uses internal-only ingress so it is reachable by the graph Container App over
// the environment-internal network but NOT the public internet. The dataset is
// ephemeral and re-populated by graph_app at startup, so a single replica is
// required (all reads/writes must hit the same in-memory instance).
resource fuseki 'Microsoft.App/containerApps@2023-05-01' = if (graphBackend == 'fuseki') {
  name: fusekiServiceName
  location: azureRegion
  properties: {
    environmentId: acaEnvironment.id
    configuration: {
      ingress: {
        allowInsecure: true
        clientCertificateMode: 'ignore'
        targetPort: 3030
        external: false
        stickySessions: {
          affinity: 'none'
        }
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          image: 'stain/jena-fuseki:latest'
          name: fusekiServiceName
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'ADMIN_PASSWORD'
              value: empty(fusekiAdminPassword) ? 'admin' : fusekiAdminPassword
            }
            {
              name: 'FUSEKI_DATASET_1'
              value: 'caig'
            }
          ]
        }
      ]
      scale: {
        maxReplicas: 1
        minReplicas: 1
      }
      terminationGracePeriodSeconds: 30
    }
  }
}

// Apache Jena MCP server, deployed as its own ACA Container App (same pattern as
// web / graph / fuseki) when graphBackend == 'fuseki'. Exposes the Fuseki dataset
// over Streamable HTTP (POST /mcp, health at /health) so Microsoft Foundry IQ can
// use it as a Knowledge Source. External ingress on port 8080, secured by API_KEY.
// It reaches Fuseki over the environment-internal FQDN, not the public internet.
// Single replica so Streamable HTTP sessions are not split across instances.

// Private-registry (ACR) pull configuration, used by the MCP image (always) and by the
// graph/web images when they are overridden to an ACR-hosted image. Empty when no ACR.
var acrRegistries = empty(acrLoginServer) ? [] : [
  {
    server: acrLoginServer
    username: acrUsername
    passwordSecretRef: 'acr-password'
  }
]
var acrSecrets = empty(acrPassword) ? [] : [
  {
    name: 'acr-password'
    value: acrPassword
  }
]

resource mcp 'Microsoft.App/containerApps@2023-05-01' = if (graphBackend == 'fuseki') {
  name: mcpServerName
  location: azureRegion
  properties: {
    environmentId: acaEnvironment.id
    configuration: {
      registries: acrRegistries
      secrets: acrSecrets
      ingress: {
        allowInsecure: false
        clientCertificateMode: 'ignore'
        targetPort: 8080
        external: true
        stickySessions: {
          affinity: 'none'
        }
        transport: 'http'
      }
    }
    template: {
      containers: [
        {
          image: mcpServerImage
          name: mcpServerName
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'MCP_TRANSPORT'
              value: 'http'
            }
            {
              name: 'PORT'
              value: '8080'
            }
            {
              name: 'API_KEY'
              // Guard: this MCP app is on PUBLIC ingress, so it must have an API
              // key. The deploy scripts auto-generate one; if a direct `az
              // deployment` leaves it empty, accessing the (non-existent) property
              // below fails the deployment instead of exposing an unauthenticated
              // public endpoint. any(json('{}')) keeps it out of Bicep's static
              // property check so it fails at deploy time, not compile time.
              value: empty(mcpApiKey) ? any(json('{}')).CAIG_MCP_API_KEY_must_be_set_when_graphBackend_is_fuseki : mcpApiKey
            }
            {
              name: 'JENA_FUSEKI_URL'
              value: 'http://${fusekiInternalFqdn}'
            }
            {
              name: 'DEFAULT_DATASET'
              value: 'caig'
            }
            {
              name: 'JENA_USERNAME'
              value: 'admin'
            }
            {
              name: 'JENA_PASSWORD'
              value: empty(fusekiAdminPassword) ? 'admin' : fusekiAdminPassword
            }
          ]
          probes: [
            {
              type: 'liveness'
              failureThreshold: 5
              httpGet: {
                path: '/health'
                port: 8080
                scheme: 'http'
              }
              initialDelaySeconds: 20
              periodSeconds: 120
              successThreshold: 1
              timeoutSeconds: 10
            }
          ]
        }
      ]
      scale: {
        maxReplicas: 1
        minReplicas: 1
      }
      terminationGracePeriodSeconds: 30
    }
  }
}

// Outputs for reference and deployment scripts
output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output storageBlobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output storageContainerName string = storageContainerName
output storageContainerUrl string = '${storageAccount.properties.primaryEndpoints.blob}${storageContainerName}'
// Stable app-level ingress FQDNs (NOT latestRevisionFqdn, which is revision-specific
// and changes with every new revision).
output graphServiceFqdn string = graph.properties.configuration.ingress.fqdn
output webAppFqdn string = web.properties.configuration.ingress.fqdn
output graphBackend string = graphBackend
output fusekiDatasetUrl string = graphBackend == 'fuseki' ? fusekiDatasetUrl : ''
output mcpServerFqdn string = mcp.?properties.configuration.ingress.fqdn ?? ''
output mcpServerEndpoint string = empty(mcp.?properties.configuration.ingress.fqdn ?? '') ? '' : 'https://${mcp.?properties.configuration.ingress.fqdn}/mcp'
