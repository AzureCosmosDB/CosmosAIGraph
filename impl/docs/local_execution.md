# CosmosAIGraph : Local Execution

**This page is oriented toward Software Engineers** who want to explore and
execute this application on their workstation.

Other users may simply wish to deploy the pre-built Docker containers to an Azure Container App as described [here](aca_deployment.md).

## Unzip file libraries-graph.zip

The full-size libraries-graph.nt (N-triples) file is too large for GitHub.
Therefore it has been zipped and added to this repo as a file 
impl/app/rdf/libraries-graph.zip.  Navigate to this directory
and unzip this file to **impl/app/rdf/libraries-graph.nt**
.

## Modes of Execution

Three different modes of execution are recommended, please use the mode
most natural to your development style.

The three modes are:

- **Microservice-per-Terminal**
- **Launcher Script**
- **Docker Compose**

## Microservice-per-Terminal

In this mode, you two Terminal windows are created each hosting its microservice, you can do that either by navigate to
**impl/app/** in each, creating/activating the python virtual environment,
and starting the **webapp.ps1** or **websvc.ps1** script or simply running **impl/run.ps1** script.

Be sure to set your environment variables, either by preparing and .env file, or by preparing and running **impl/set-caig-env-vars-sample.ps1** script, before starting the microservices.

## Docker Compose

This is the closest method to running your application to Azure.
This approach executes the application packaged as **Docker Containers** rather than as local files.

Start your **Docker Desktop** application if it's not already running.

Be sure to modify your environment variables in the appropriate
**docker-compose-xxx.yml** ile before starting the microservices.

Two docker-compose yml files are available:

- docker/docker-compose-with-rdflib.yml
  - This uses the Python-based web application
  - This uses the Python-based graph microservice using rdflib

- docker-compose-with-jena.yml 
  - This also uses the same Python-based web application
  - This uses the Java-based graph microservice using Apache Jena

Create two PowerShell Terminal windows, and navigate to the **impl/app/** directory in each.

In the first terminal window, execute the following command to start the application (both microservices).

```
docker compose -f docker/docker-compose-with-rdflib.yml up
or
docker compose -f docker/docker-compose-with-jena.yml up
```

You should see similar verbose output that includes the following:

<p align="center">
  <img src="img/docker-compose-up.png" width="50%">
</p>

---

In the second terminal window, execute the following command to terminate the application.

```
docker compose -f docker/docker-compose-with-rdflib.yml down
or
docker compose -f docker/docker-compose-with-jena.yml down
```

You should see similar verbose output that includes the following:

<p align="center">
  <img src="img/docker-compose-down.png" width="40%">
</p>

---

### The Docker Containers

These three pre-built Docker containers exist on **DockerHub**:

- cjoakim/caig_web_v2:latest
- cjoakim/caig_graph_v2:latest
- cjoakim/caig_graph_java_jena_v1:latest

These are used by default by the above **docker-compose** scripts
and also by the **Azure Container App** deployment process.

If you wish to rebuild these containers and deploy them to your own
Container Registry, please see the following Dockerfiles in this repo.
You're free to modify these as necessary.
Please change the **cjoakim** prefix to your own identifier.

- impl/app/docker/Dockerfile_graph
- impl/app/docker/Dockerfile_web
- impl/java_jena_graph_websvc/Dockerfile
