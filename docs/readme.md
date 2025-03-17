
<p align="center">
  <img src="img/deployment-architecture.png" width="100%">
</p>


---

The **CosmosAIGraph (caig)** solution is deployed as two microservices:

| Name   | Functionality                                                               |
| ------ | --------------------------------------------------------------------------- |
| web    |  Web microservice, user-facing, HTML-based UI and RESTful API                   |
| graph  |  Graph microservice with an in-memory Apache Jena graph |

These are located in the **web_app**, and **graph_app** folders
of this repository.

They are also packaged as Docker containers named as **caig_web**, and **caig_graph**, respectively.

## Implementation Summary

- **Python3** is used exclusively in the CosmosAIGraph solution
  - See https://www.python.org
- **FastAPI** is used exclusively as the framework for the web and http services
  - See https://fastapi.tiangolo.com
- **Azure Cosmos DB for NoSQL** is used as the persistent datastore for source data and session history as well as a vector database
  - See https://learn.microsoft.com/en-us/azure/cosmos-db/
  - Your domain data, with embeddings, are stored here
  - AI sessions - prompts/completions history and feedback - are persisted here as well
  - This Cosmos DB data can optionally be mirrored to OneLake in Microsoft Fabric for analytics, semantic cache and other capabilities
- **Azure OpenAI** is used for AI models
  - See https://learn.microsoft.com/en-us/azure/ai-services/openai/
- **semantic-kernel** is used for AI and LLM orchestration
  - See https://learn.microsoft.com/en-us/semantic-kernel/overview/
- **Apache Jena** is used as the high-performance in-memory graph
  - See https://jena.apache.org/
- **SPARQL 1.1** is the graph query language
  - See https://www.w3.org/TR/sparql11-query/
- **Web Ontology Language (OWL)** is the graph schema/ontology definition language
  - See https://www.w3.org/OWL/

---

## Quick Start

### Clone this GitHub Repository

Open a PowerShell Terminal, navigate to the desired parent directory
and execute the following **git clone** command.  This will copy the
contents of the public GitHub repository to your workstation.

If you don't have **git** installed on your system, please see the
[Developer Workstation Setup](developer_workstation.md) page.

```
> git clone https://github.com/AzureCosmosDB/CosmosAIGraph/CosmosAIGraph.git

> cd CosmosAIGraph

> Get-Location
```

The output value from the **Get-Location** will be a fully-qualified
directory path on your workstation.  Please set the **CAIG_HOME**
environment variable to this directory path value.

```
echo 'setting CAIG_HOME'
[Environment]::SetEnvironmentVariable("CAIG_HOME", "...your value from Get-Location ...", "User")
```

You will need to restart your Terminal for the above command to take effect.

You'll see in a section below that this CosmosAIGraph reference application
uses several environment variables, and they all begin with **CAIG_**.

### Provision Azure Cosmos DB and Azure OpenAI

- See [Initial PaaS Provisioning](initial_paas_provisioning.md)

### Developer Workstation Setup

- See [Developer Workstation Setup](developer_workstation.md)
- See [Environment Variables](environment_variables.md)

### Load Cosmos DB with Library and Config Documents

- See [Cosmos DB Document Design and Modeling](cosmos_design_modeling.md)
- See [Load Azure Cosmos DB for NoSQL](load_cosmos_nosql.md)

### Run the Application on your Workstation

- See [Local Execution](local_execution.md)
- See [Explore the FastAPI Framework and Endpoint Documentation](fastapi_endpoint_docs.md)
- See [Understanding the Code](understanding_the_code.md)

### Azure Container Apps Deployment

- See [Deploying the Azure Container Apps](aca_deployment.md)

### Screen Shots of the Current Implementation

- See [Screen Shots](screen_shots.md)

---

## Next Steps: Customizing this Solution for Your Application

It is recommended that CosmosAIGraph Proof-of-Concept (POC) team
has the following skill sets:

- A data analyst who is familiar with your input graph data
- A data engineer who can wrangle/transform the raw data into JSON documents for Cosmos DB
- A Python developer with UI skills
- A Java developer with graph (SPARQL/TTL) skills

- See [Customizing this Solution](customizing_this_solution.md)
- See the [FAQ Page](faq.md) to clarify your understanding of the CosmosAIGraph solution.
