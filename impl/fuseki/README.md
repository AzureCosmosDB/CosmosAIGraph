# Apache Jena Fuseki Backend (alternative graph backend)

This directory contains the assets for running the CosmosAIGraph `graph_app`
against an **external Apache Jena Fuseki** triple store instead of the default
**in-process, in-memory** Jena model.

This is the *external triple store* backend option. It is fully backward
compatible: the graph_app defaults to the in-memory backend and only uses Fuseki
when `CAIG_GRAPH_BACKEND=fuseki` is set.

## How it works

1. At startup, `AppGraphBuilder` assembles the RDF model exactly as before
   (ontology + triples sourced from Cosmos DB / RDF file / JSON docs).
2. If `CAIG_GRAPH_BACKEND=fuseki`, the graph_app then connects to the Fuseki
   dataset at `CAIG_FUSEKI_DATASET_URL` and uploads the assembled model via the
   SPARQL Graph Store Protocol.
3. All subsequent `/sparql_query`, `/sparql_update`, and `/add_documents`
   requests are served by Fuseki via the standard SPARQL 1.1 protocol. The
   `/sparql_bom_query` traversal runs against a one-time local snapshot of the
   Fuseki dataset for performance (see [Notes](#notes)). No graph_app endpoint
   contracts change.

## Configuration (graph_app environment variables)

| Variable                  | Default                          | Description                                  |
|---------------------------|----------------------------------|----------------------------------------------|
| `CAIG_GRAPH_BACKEND`      | `in_memory`                      | Set to `fuseki` to enable the Fuseki backend. |
| `CAIG_FUSEKI_DATASET_URL` | `http://localhost:3030/caig`     | Base URL of the Fuseki dataset.              |
| `CAIG_FUSEKI_USER`        | `admin`                          | HTTP Basic user for authenticated writes.    |
| `CAIG_FUSEKI_PASSWORD`    | `admin`                          | HTTP Basic password; matches `ADMIN_PASSWORD`. |

The query/update/GSP endpoints are derived from the dataset URL as
`/query`, `/update`, and `/data`. The Fuseki image serves SPARQL queries
anonymously but requires HTTP Basic authentication for write operations
(SPARQL update and Graph Store Protocol uploads), so the graph_app authenticates
with `CAIG_FUSEKI_USER` / `CAIG_FUSEKI_PASSWORD`. These must match the
container's `ADMIN_PASSWORD`.

## Local development

```powershell
# From the repository root:
.\run_fuseki.ps1
```

This starts the Fuseki Docker container (`impl\fuseki\fuseki.ps1`), sets
`CAIG_GRAPH_BACKEND=fuseki`, and launches the graph and web microservices.

To run only the Fuseki container:

```powershell
.\impl\fuseki\fuseki.ps1
```

- Fuseki UI:   http://localhost:3030/
- Dataset URL: http://localhost:3030/caig

The local container creates an ephemeral in-memory `caig` dataset via the
`FUSEKI_DATASET_1=caig` environment variable (the same mechanism used by Docker
Compose and ACA). The graph_app re-uploads the assembled model on each startup,
so the ephemeral dataset is acceptable.

## Docker Compose

`impl/docker-compose.yml` includes a `fuseki` service. Enable the backend by
exporting `CAIG_GRAPH_BACKEND=fuseki` before `docker compose up`. The compose
service uses an ephemeral in-memory dataset (`FUSEKI_DATASET_1=caig`); the
graph_app re-uploads the model on each startup.

## Azure Container Apps

`deployment/caig.bicep` deploys Fuseki as its **own internal-only ACA Container
App** (the same way as the `web` and `graph` apps) when the `graphBackend`
parameter is set to `fuseki`. This is the *secondary* deployment option; the
default `in_memory` backend deploys only the web and graph apps.

- The Fuseki app uses **internal ingress** (`external: false`) on target port
  `3030`, so it is reachable by the graph app over the environment-internal
  network but not the public internet.
- The graph app reaches it at `http://<fusekiServiceName>.internal.<envDefaultDomain>/caig`
  (ACA ingress maps port 80 to the container's 3030). This URL is passed to the
  graph app as `CAIG_FUSEKI_DATASET_URL`.
- Fuseki runs as a **single replica** (`minReplicas: maxReplicas: 1`) because the
  dataset is held in memory — every read/write must hit the same instance.
- Enable it by setting `GRAPH_BACKEND = "fuseki"` at the top of
  `deployment/az_bicep_deploy.ps1` / `.sh` (alongside `RESOURCE_GROUP` / `REGION`;
  `FUSEKI_SERVICE_NAME` is set there too). The Fuseki admin password
  (`CAIG_FUSEKI_ADMIN_PASSWORD`) is auto-generated as a strong random value by the
  deploy script when unset — set it yourself only if you want a fixed value. The
  dataset is ephemeral and re-populated by the graph_app at startup.

## Jena MCP server

When the Fuseki backend is enabled, an **Apache Jena MCP server**
([github.com/alekseys/mcp-jena](https://github.com/alekseys/mcp-jena)) is also
deployed so Microsoft Foundry IQ can consume the graph as a **Knowledge Source**
over the Model Context Protocol (Streamable HTTP).

It stays a **separate, reusable project** — this repo never vendors its source.
Instead:

- **Local** (`impl/docker-compose.yml`): the `mcp` service builds straight from
  the Git URL (`build.context: https://github.com/alekseys/mcp-jena.git`) and
  connects to the `fuseki` service. Exposed on `http://localhost:8080/mcp`.
- **Azure** (`deployment/`): `az_bicep_deploy.ps1` / `.sh` build the image
  **server-side with `az acr build` straight from the Git URL** (only when
  `GRAPH_BACKEND = 'fuseki'` in the deploy script) — no Docker install, no
  `docker login`, no manual registry setup. The script provisions an ACR
  (idempotent, name derived from the resource group), builds `mcp-jena:latest`,
  and passes the image + pull credentials to `deployment/caig.bicep`, which
  deploys the `mcp` ACA Container App.

The deploy script also **auto-generates a strong `API_KEY`** if `CAIG_MCP_API_KEY`
is not set, and prints the MCP endpoint + key at the end. So a Fuseki-backend
deploy needs no manual MCP steps — just set `GRAPH_BACKEND = 'fuseki'` in the
deploy script.

The MCP Container App:

- Uses **external ingress** on target port `8080` so MCP clients can reach it at
  `https://<mcp-fqdn>/mcp` (health probe at `/health`).
- Is secured by `API_KEY` (`CAIG_MCP_API_KEY`) — clients send it as
  `Authorization: Bearer <key>` or `x-api-key: <key>`. Auto-generated when unset.
- Reaches Fuseki over the environment-**internal** FQDN
  (`JENA_FUSEKI_URL=http://<fuseki>.internal.<domain>`, `DEFAULT_DATASET=caig`,
  `JENA_USERNAME`/`JENA_PASSWORD`), so Fuseki itself stays private.
- Runs a single replica, so all Streamable HTTP sessions land on the one instance
  (no session affinity needed).

Point MCP client at `https://<mcp-fqdn>/mcp` (see the `mcpServerEndpoint`
deployment output, also printed by the deploy script) and configure the API key
as the bearer token.

## Notes

- The Fuseki dataset is treated as a rebuildable cache of the source data;
  ephemeral (in-memory) datasets are acceptable because the graph_app uploads
  the model at every startup.
- BOM traversal (`/sparql_bom_query`) issues many small per-node queries. To
  avoid an N+1 storm of HTTP round-trips against Fuseki, the graph_app fetches a
  single local snapshot of the dataset at the start of each BOM query and runs
  the whole traversal in-process. Generic `/sparql_query` and `/sparql_update`
  still execute directly against Fuseki, so the snapshot always reflects the
  latest state.
- Do **not** bind-mount a single assembler file into `/fuseki/configuration/`:
  Docker creates that directory root-owned and non-writable, which makes Fuseki
  fail to start (`FusekiConfigException: Not writable`) and return `503` for
  every request. Use the `FUSEKI_DATASET_1` env var instead, or mount a full
  writable volume if persistence is required.
- The image tag (`stain/jena-fuseki:latest`) can be pinned to a specific version.
