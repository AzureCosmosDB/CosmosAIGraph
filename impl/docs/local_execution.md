# CosmosAIGraph : Local Execution

**This page is oriented toward Software Engineers** who want to explore and
execute this application on their workstation.

Other users may simply wish to deploy the pre-build Docker containers
to an Azure Container App as described [here](aca_deployment.md).

## Unzip file libraries-graph.zip

The full-size libraries-graph.nt (triples) file is too large for GitHub.
Therefore it has been zipped and added to this repo as file 
impl/app/rdf/libraries-graph.zip.  Navigate to this directory
and unzip this file such that file **impl/app/rdf/libraries-graph.nt**
exists

## Modes of Execution

Three different modes of execution are recommended, please use the mode
most natural to your development style.

The three modes are:

- **Microservice-per-Terminal**
- **Launcher Script**
- **Docker Compose**

## Microservice-per-Terminal

In this mode, you manually create two Terminal windows, navigate to
**impl/app/** in each, create/activate the python virtual environment,
and start the **webapp.ps1** or **websvc.ps1** script.

Be sure to modifify your environment variables, such as with the .env file,
before starting the microservices.

## Docker Compose

This is the recommended solution as you near deployment of your application to Azure.
This approach executes the application packaged as **Docker Containers** rather
than as local files.

Start your **Docker Destop** application if it's not already running.

Be sure to modify your environment variables in the **docker-compose.yml** 
before starting the microservices.

Create two PowerShell Terminal windows, and navigate to the **impl/app/** directory in each.

In the first terminal window, execute the following command to start the application
(both microservices).

```
docker compose -f docker/docker-compose.yml up
```

You should should see verbose output that includes the following:

<p align="center">
  <img src="img/docker-compose-up.png" width="50%">
</p>

---

In the second terminal window, execute the following command to terminate the application.

```
docker compose -f docker/docker-compose.yml down
```

You should should see verbose output that includes the following:

<p align="center">
  <img src="img/docker-compose-down.png" width="40%">
</p>

---

### The Docker Containers

These two pre-built Docker containers exist on **DockerHub**.

- cjoakim/caig_web:latest
- cjoakim/caig_graph:latest

These are used by default by the above **docker-compose** script
and also by the **Azure Container App** deployment process.

If you wish to rebuild these containers and deploy them to your own Registry,
please see the **impl/app/docker-builds.ps1** and **impl/app/docker-builds.sh**
scripts in this repository.  You're free to modify these as necessary.
Please change the **cjoakim** prefix to your own identifier.
