# CosmosAIGraph : Application Architecture

<p align="center">
  <img src="img/app-architecture-v3.png" width="90%">
</p>

---

## Application Components

- Microservices
  - web microervice - UI front end with AI functionality
  - graph microservice - Contains the in-memory graph
- Azure Container App - Runtime orchestrator for the above two microservices
- Cosmos DB NoSQL or Mongo vCore API - Domain data and conversational AI documents, embeddings
- Azure OpenAI - completions and embeddings service

