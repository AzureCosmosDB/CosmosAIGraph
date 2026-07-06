# CosmosAIGraph : Deploying to the Azure Container Apps

The **recommended deployment** for this reference implementation is in 
[Azure Container Apps (ACA)](https://learn.microsoft.com/en-us/azure/container-apps/).

ACA offers a very mature and easy way to use runtime environment for your applications
that are packaged and deployed as Docker containers. Several relevant features
include the following:

- [Environments](https://learn.microsoft.com/en-us/azure/container-apps/environment)
- [CPU and memory sizes](https://learn.microsoft.com/en-us/azure/container-apps/containers)
- [Workload profile types](https://learn.microsoft.com/en-us/azure/container-apps/workload-profiles-overview#profile-types)
- [Networking and VNets](https://learn.microsoft.com/en-us/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli)
- [Scaling rules](https://learn.microsoft.com/en-us/azure/container-apps/scale-app?pivots=azure-cli)

### Deployment with Bicep

**Important:** First, make sure that your **application** environment variables (Cosmos DB,
Azure OpenAI, graph source, etc.) are set as described in the
[Environment Variables](environment_variables.md) document. The deployment scripts read these
environment variables to set them in the ACA containers.

**Deployment-specific** settings are configured directly at the top of the deploy script
(not via environment variables), so they live in one place:

- `RESOURCE_GROUP` and `REGION` — the target resource group and Azure region.
- `ACA_ENVIRONMENT_NAME`, `LA_WORKSPACE_NAME`, `COSMOSDB_NOSQL_RG`, `DEFINED_AUTH_USERS` —
  infrastructure inputs that the app itself never reads (they are only Bicep inputs).
- `GRAPH_BACKEND` — `in_memory` (default) or `fuseki` (see **Graph backends** below).
- `FUSEKI_SERVICE_NAME` / `MCP_SERVER_NAME` — the ACA app names used when `GRAPH_BACKEND = 'fuseki'`.

Your **account-specific** values (Azure OpenAI + Cosmos keys/URLs, containers, graph
source, auth secret) come from the environment variables in the **Environment Variables**
step above. Because you run the project locally with `.env` / `.override.properties`
rather than shell env vars, put those values in a small script that exports them for the
deploy shell — e.g. `deployment/set-caig-deploy-env.ps1` (keep it out of source control:
it holds keys).

See the **/deployment** folder for the deployment scripts, which use the [Bicep](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview) syntax.
Edit the variables at the top of **az_bicep_deploy.ps1** (Windows) or **az_bicep_deploy.sh**
(macOS/Linux), then run the deployment in one shell session (the scripts use the
[az CLI](https://learn.microsoft.com/en-us/cli/azure/)):

```powershell
cd deployment
. .\set-caig-deploy-env.ps1   # dot-source your account-specific values into this shell
.\az_bicep_deploy.ps1         # RESOURCE_GROUP / REGION / GRAPH_BACKEND etc. are set at the top
```

(**Note:** On macOS/Linux: make sure to set executable permissions with: 
chmod +x ./deployment/az_bicep_deploy.sh)



The Bicep file is named **caig.bicep** and it uses the **caig.bicepparam** parameters file.

If you add/delete some of your environment variables, run the following command in the **impl\web_app**
folder to (re)generate the Bicep **fragment** files — **deployment/generated-param-names.bicep**
(param declarations) and **deployment/generated.bicepparam** (param values) — per the **CAIG_xxx**
environment variables you have set on your workstation. These are reference fragments: you then
copy the entries you need into the hand-maintained **caig.bicep** and **caig.bicepparam** files
(`gen_all` does **not** overwrite `caig.bicep` / `caig.bicepparam`).

```
(venv) PS ...\web_app> python main_common.py gen_all

LoggingService config level name: info
LoggingService initialized to level: 20
2024-03-01 16:03:21,461 - file written: tmp/caig-envvars-master.txt
2024-03-01 16:03:21,462 - file written: ../set-caig-env-vars-sample.ps1
2024-03-01 16:03:21,463 - file written: ../deployment/generated-param-names.bicep   <--- this
2024-03-01 16:03:21,463 - file written: ../deployment/generated.bicepparam          <--- this
2024-03-01 16:03:21,464 - file written: ../docs/environment_variables.md
```

### Graph backends (in-memory vs Fuseki + MCP)

The `graph_app` supports two interchangeable graph backends, selected with the
`GRAPH_BACKEND` variable at the top of the deploy script. The choice is fully
backward compatible — the default requires no extra resources.

| Backend | `GRAPH_BACKEND` | What gets deployed to ACA |
| ------- | --------------- | ------------------------- |
| In-memory (default) | `in_memory` | `web` + `graph` Container Apps only. The graph is held in-process by Jena. |
| Fuseki | `fuseki` | `web` + `graph` + a **Fuseki** Container App (internal-only Apache Jena triple store) + an **MCP** Container App. |

When `GRAPH_BACKEND = 'fuseki'`:

- **Fuseki** is deployed as its own internal-only Container App; the `graph_app`
  uploads the assembled model to it at startup and serves SPARQL from it.
- An **Apache Jena MCP server** ([github.com/alekseys/mcp-jena](https://github.com/alekseys/mcp-jena))
  is deployed as an externally-reachable Container App so Microsoft Foundry IQ can
  consume the graph as a **Knowledge Source** over Streamable HTTP (`/mcp`).
- The deploy script automatically builds the MCP image from its repo with
  `az acr build`, provisions an ACR, and **auto-generates strong random values**
  for the Fuseki admin password (`CAIG_FUSEKI_ADMIN_PASSWORD`) and the MCP
  `API_KEY` (`CAIG_MCP_API_KEY`) when they are not already set (the MCP key is
  printed at the end of the deployment).

To enable it, set `$GRAPH_BACKEND = "fuseki"` (PowerShell) or `GRAPH_BACKEND="fuseki"`
(bash) at the top of `az_bicep_deploy.ps1` / `.sh` and run the script. No other
manual steps are required. See
[impl/fuseki/README.md](../impl/fuseki/README.md) for the full backend and MCP
details.

> **Do I need to run `gen_all` first?** No. The Fuseki, MCP, and ACR parameters
> are already present in the hand-maintained **caig.bicep** and
> **caig.bicepparam** files, and the deploy scripts publish the deployment options
> to the environment variables that the param file reads. Just set `GRAPH_BACKEND`
> to `fuseki` in the deploy script and run it — the Fuseki admin password and MCP
> API key are auto-generated as strong random values when unset (set
> `CAIG_FUSEKI_ADMIN_PASSWORD` / `CAIG_MCP_API_KEY` yourself only if you want
> fixed, stable values across redeploys). `gen_all` only refreshes the generated
> reference fragments and the environment variable docs/samples; it is not part of
> the deployment path.

