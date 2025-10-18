# CosmosAIGraph Deployment : Environment Variables

Per the [Twelve-Factor App methodology](https://12factor.net/config),
configuration is stored in the environment variables.  
This is the standard practice for Docker-containerized applications deployed to orchestrators
such as Azure Kubernetes Service (AKS) and Azure Container Apps (ACA).

## Defined Variables

This reference implementation uses the following environment variables.
All of these begin with the prefix `CAIG_`.

| Name | Description | Where Used |
| --------------------------------- | --------------------------------- | ---------- |
| CAIG_AZURE_OPENAI_COMPLETIONS_DEP | The name of your Azure OpenAI completions deployment.   | WEB RUNTIME |
| CAIG_AZURE_OPENAI_EMBEDDINGS_DEP | The name of your Azure OpenAI embeddings deployment.   | WEB RUNTIME |
| CAIG_AZURE_OPENAI_KEY | The Key of your Azure OpenAI account.   | WEB RUNTIME |
| CAIG_AZURE_OPENAI_URL | The URL of your Azure OpenAI account.   | WEB RUNTIME |
| CAIG_AZURE_OPENAI_VERSION | The Version of your Azure OpenAI account.   | WEB RUNTIME |
| CAIG_CONFIG_CONTAINER | The Cosmos DB container for configuration JSON values.   | RUNTIME |
| CAIG_CONVERSATIONS_CONTAINER | The Cosmos DB container where the chat conversations and history are persisted.   | WEB RUNTIME |
| CAIG_COSMOSDB_NOSQL_ACCT | The Name of your Cosmos DB NoSQL account.   | RUNTIME |
| CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM | The Cosmos DB NoSQL authentication mechanism; key or rbac.   | RUNTIME |
| CAIG_COSMOSDB_NOSQL_KEY | The key of your Cosmos DB NoSQL account.   | RUNTIME |
| CAIG_COSMOSDB_NOSQL_RG | The Resource Group of your Cosmos DB NoSQL account.   | DEV ENV |
| CAIG_COSMOSDB_NOSQL_URI | The URI of your Cosmos DB NoSQL account.   | RUNTIME |
| CAIG_FEEDBACK_CONTAINER | The Cosmos DB container where user feedback is persisted.   | WEB RUNTIME |
| CAIG_GRAPH_DUMP_OUTFILE | The file to write to if CAIG_GRAPH_DUMP_UPON_BUILD is true.   | GRAPH RUNTIME |
| CAIG_GRAPH_DUMP_UPON_BUILD | Boolean true/false to dump the Java/Jena model to CAIG_GRAPH_DUMP_OUTFILE.   | GRAPH RUNTIME |
| CAIG_GRAPH_NAMESPACE | The custom namespace for the RED graph.   | GRAPH RUNTIME |
| CAIG_GRAPH_SERVICE_NAME | Logical app name.   | DEV ENV |
| CAIG_GRAPH_SERVICE_PORT | 8002   | WEB RUNTIME |
| CAIG_GRAPH_SERVICE_URL | http://127.0.0.1 or determined by ACA.   | WEB RUNTIME |
| CAIG_GRAPH_SOURCE_CONTAINER | The graph Cosmos DB container name, if CAIG_GRAPH_SOURCE_TYPE is 'cosmos_nosql'.   | GRAPH RUNTIME |
| CAIG_GRAPH_SOURCE_DB | The graph Cosmos DB database name, if CAIG_GRAPH_SOURCE_TYPE is 'cosmos_nosql'.   | GRAPH RUNTIME |
| CAIG_GRAPH_SOURCE_OWL_FILENAME | The input RDF OWL ontology file.   | GRAPH RUNTIME |
| CAIG_GRAPH_SOURCE_PATH | The RDF input file or folder, if CAIG_GRAPH_SOURCE_TYPE is 'rdf_file'.   | GRAPH RUNTIME |
| CAIG_GRAPH_SOURCE_TYPE | The RDF graph data source type, either 'cosmos_nosql', or 'json_docs_file' or 'rdf_file'.   | GRAPH RUNTIME |
| CAIG_HOME | Root directory of the CosmosAIGraph GitHub repository on your system.   | DEV ENV |
| CAIG_LOG_LEVEL | A standard python or java logging level name.   | RUNTIME |
| CAIG_PROMPT_COMPLETION_PATH | Path to completion prompt .txt file.  | WEB RUNTIME |
| CAIG_PROMPT_SPARQL_PATH | Path to SPARQL generation prompt .txt file.  | WEB RUNTIME |
| CAIG_WEBSVC_AUTH_HEADER | Name of the custom HTTP authentication header; defaults to 'x-caig-auth'.   | RUNTIME |
| CAIG_WEBSVC_AUTH_VALUE | your-secret-value   | RUNTIME |
| CAIG_WEB_APP_NAME | Logical name.   | DEV ENV |
| CAIG_WEB_APP_PORT | 8000   | WEB RUNTIME |
| CAIG_WEB_APP_URL | http://127.0.0.1 or determined by ACA.   | WEB RUNTIME |
| CAIG_ACA_ENVIRONMENT_NAME |  The name of your Azure Container Apps environment.   | DEPLOYMENT |
| CAIG_DEFINED_AUTH_USERS |  The list of defined Azure Container Apps users.   | DEPLOYMENT |
| CAIG_AZURE_REGION |  The Azure region where your resources are deployed.   | DEPLOYMENT |
| CAIG_LA_WORKSPACE_NAME |  The name of your Azure Logic Apps workspace.   | DEPLOYMENT |

## Setting these Environment Variables

The repo contains generated PowerShell script **impl/set-caig-env-vars-sample.ps1** and bash script **impl/set-caig-env-vars-sample.sh**
which set all of these CAIG_ environment values in their respective environments.
You may find it useful to edit and execute this script rather than set them manually on your system


## python-dotenv

The [python-dotenv](https://pypi.org/project/python-dotenv/) library is used
in each subapplication of this implementation.
It allows you to define environment variables in a file named **`.env`**
and thus can make it easier to use this project during local development.

Please see the **sample.env** files in each subapplication for examples.

It is important for you to have a **.gitignore** entry for the **.env** file
so that application secrets don't get leaked into your source control system.


## Java .override.properties file

The Java codebase in this repo implements similar logic to the python-dotenv described above.

See file **sample.override.properties** in the **impl/graph_app/** directory.

