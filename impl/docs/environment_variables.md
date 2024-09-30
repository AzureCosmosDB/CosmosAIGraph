# CosmosAIGraph Implementation 1 : Environment Variables

Per the [Twelve-Factor App methodology](https://12factor.net/config),
configuration is stored in environment variables.  
This is the standard practice for Docker-containerized applications deployed to orchestrators
such as Azure Kubernetes Service (AKS) and Azure Container Apps (ACA).

## Defined Variables

This reference implementation uses the following environment variables.
Some are used at runtime in ACA, some are used for Bicep-deployment,
and some are used for local workstation development.
All of these begin with the prefix `CAIG_`.

| Name | Description |
| --------------------------------- | --------------------------------- |
| CAIG_ACA_ENVIRONMENT_NAME | The Azure Container App (ACA) environment name |
| CAIG_AZURE_MONGO_VCORE_CONN_STR | The full connection string for the Cosmos DB Mongo vCore account |
| CAIG_AZURE_OPENAI_COMPLETIONS_DEP | The name of your Azure OpenAI completions deployment |
| CAIG_AZURE_OPENAI_EMBEDDINGS_DEP | The name of your Azure OpenAI embeddings deployment |
| CAIG_AZURE_OPENAI_KEY | The Key of your Azure OpenAI account |
| CAIG_AZURE_OPENAI_URL | The URL of your Azure OpenAI account |
| CAIG_AZURE_REGION | The Azure region where the ACA app is deployed to |
| CAIG_CONFIG_CONTAINER | The vCore container for configuration JSON values |
| CAIG_CONVERSATIONS_CONTAINER | The vCore container where the chat conversations and history are persisted |
| CAIG_COSMOSDB_NOSQL_KEY1 | The key of your Cosmos DB NoSQL account |
| CAIG_COSMOSDB_NOSQL_URI | The URI of your Cosmos DB NoSQL account |
| CAIG_DEFINED_AUTH_USERS |  |
| CAIG_FEEDBACK_CONTAINER | The vCore container where user feedback is persisted |
| CAIG_GRAPH_NAMESPACE | The custom namespace for the RED graph |
| CAIG_GRAPH_SERVICE_NAME |  |
| CAIG_GRAPH_SERVICE_PORT |  |
| CAIG_GRAPH_SERVICE_URL |  |
| CAIG_GRAPH_SOURCE_CONTAINER | The graph vCore container name, if CAIG_GRAPH_SOURCE_TYPE is 'cosmos_vcore' |
| CAIG_GRAPH_SOURCE_DB | The graph vCore database name, if CAIG_GRAPH_SOURCE_TYPE is 'cosmos_vcore' |
| CAIG_GRAPH_SOURCE_OWL_FILENAME | The input RDF OWL ontology file |
| CAIG_GRAPH_SOURCE_RDF_FILENAME | The RDF input file, if CAIG_GRAPH_SOURCE_TYPE is 'rdf_file' |
| CAIG_GRAPH_SOURCE_TYPE | The RDF graph data source type, either 'rdf_file' or 'cosmos_vcore' or 'cosmos_nosql' |
| CAIG_HOME | Root directory of the CosmosAIGraph GitHub repository on your system |
| CAIG_LA_WORKSPACE_NAME | The Log Analytics workspace name used by the Azure Container App (ACA) |
| CAIG_LOG_LEVEL | a python logging standard-lib level name: notset, debug, info, warning, error, or critical |
| CAIG_PG_FLEX_PASS | Azure PostgreSQL Flex Server user password |
| CAIG_PG_FLEX_SERVER | Azure PostgreSQL Flex Server hostname |
| CAIG_PG_FLEX_USER | Azure PostgreSQL Flex Server user |
| CAIG_WEBSVC_AUTH_HEADER | x-caig-auth |
| CAIG_WEBSVC_AUTH_VALUE | K6ZQw!81 |
| CAIG_WEB_APP_NAME |  |
| CAIG_WEB_APP_PORT |  |
| CAIG_WEB_APP_URL |  |

## Setting these Environment Variables

The repo contains generated PowerShell script **impl/set-caig-env-vars-sample.ps1**
which sets all of these CAIG_ environment values.
You may find it useful to edit and execute this script rather than set them manually on your system


## python-dotenv

The [python-dotenv](https://pypi.org/project/python-dotenv/) library is used
in each subapplication of this implementation.
It allows you to define environment variables in a file named **`.env`**
and thus can make it easier to use this project during local development.

Please see the **dotenv_example** files in each subapplication for examples.

It is important for you to have a **.gitignore** entry for the **.env** file
so that application secrets don't get leaked into your source control system.

