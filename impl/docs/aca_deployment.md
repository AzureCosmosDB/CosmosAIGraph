# CosmosAIGraph : Deploying the Azure Container App

## Azure Container Apps

The **recommended solution** for this reference application is to deploy to
[Azure Container Apps (ACA)](https://learn.microsoft.com/en-us/azure/container-apps/).

ACA offers a very mature and easy to use runtime environment for your applications
that are packaged and deployed as Docker Containers.  Several interesting features
include the following:

- [Environments](https://learn.microsoft.com/en-us/azure/container-apps/environment)
- [CPU and Memory sizes](https://learn.microsoft.com/en-us/azure/container-apps/containers)
- [Workload Profile Types](https://learn.microsoft.com/en-us/azure/container-apps/workload-profiles-overview#profile-types)
- [Networking and VNets](https://learn.microsoft.com/en-us/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli)
- [Scaling Rules](https://learn.microsoft.com/en-us/azure/container-apps/scale-app?pivots=azure-cli)

### Deployment with Bicep

See the **impl/deployment/** directory for working deployment scripts which use the 
[Bicep](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview)
deployment syntax.

You can execute the **az_bicep_deploy.ps1** script which uses the
[az CLI](https://learn.microsoft.com/en-us/cli/azure/) to deploy
the ACA application. 

The Bicep file is named **caig.bicep** and it uses the **caig.bicepparam**
parameters file.

There is functionality in this repo to generate the **caig.bicepparam** file,
and the top of your **caig.bicep** file, per the **CAIG_xxx** environment variables
that you have set on your workstation.

In the impl\app directory you can execute the following script.

```
(venv) PS ...\app> python main_common.py gen_all

LoggingService config level name: info
LoggingService initialized to level: 20
2024-03-01 16:03:21,461 - file written: tmp/caig-envvars-master.txt
2024-03-01 16:03:21,462 - file written: ../set-caig-env-vars-sample.ps1
2024-03-01 16:03:21,463 - file written: ../deployment/generated-param-names.bicep   <--- this
2024-03-01 16:03:21,463 - file written: ../deployment/generated.bicepparam          <--- this
2024-03-01 16:03:21,464 - file written: ../docs/environment_variables.md
```

---

## Azure Kubernetes Service (AKS)

Some customers may wish to deploy their CosmosAIGraph applications to alternative solutions,
such as [Azure Kubernetes Service (AKS)](https://azure.microsoft.com/en-us/products/kubernetes-service).

Since CosmosAIGraph is packaged as **Docker Containers** the use of AKS is certainly
possible, but is out-of-scope for this reference application.
