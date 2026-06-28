# Apache Jena Fuseki Sidecar (alternative graph backend)

This directory contains the assets for running the CosmosAIGraph `graph_app`
against an **external Apache Jena Fuseki** triple store instead of the default
**in-process, in-memory** Jena model.

This is the *sidecar* deployment option. It is fully backward compatible: the
graph_app defaults to the in-memory backend and only uses Fuseki when
`CAIG_GRAPH_BACKEND=fuseki` is set.

## How it works

1. At startup, `AppGraphBuilder` assembles the RDF model exactly as before
   (ontology + triples sourced from Cosmos DB / RDF file / JSON docs).
2. If `CAIG_GRAPH_BACKEND=fuseki`, the graph_app then connects to the Fuseki
   dataset at `CAIG_FUSEKI_DATASET_URL` and uploads the assembled model via the
   SPARQL Graph Store Protocol.
3. All subsequent `/sparql_query`, `/sparql_update`, `/sparql_bom_query`, and
   `/add_documents` requests are served by Fuseki via the standard SPARQL 1.1
   protocol. No graph_app endpoint contracts change.

## Configuration (graph_app environment variables)

| Variable                  | Default                          | Description                                  |
|---------------------------|----------------------------------|----------------------------------------------|
| `CAIG_GRAPH_BACKEND`      | `in_memory`                      | Set to `fuseki` to enable the sidecar.       |
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

`deployment/caig.bicep` adds a `fuseki` sidecar container to the graph Container
App when the `graphBackend` parameter is set to `fuseki`. The graph container
reaches Fuseki over `http://localhost:3030/caig` (containers in the same ACA app
share the localhost network namespace). The dataset is ephemeral and
re-populated by the graph_app at startup.

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
