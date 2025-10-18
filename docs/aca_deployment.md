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

**Important:** First, make sure that your environment variables are set as described in the
[Environment Variables](environment_variables.md) document. The Deployment scripts below use the environment variables to set them in ACA containers.

See the **/deployment** folder for the deployment scripts which use the [Bicep](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview) deployment syntax.

Then, execute **az_bicep_deploy.ps1** (on Windows) or **az_bicep_deploy.sh** (on macOS/Linux) script which uses the
[az CLI](https://learn.microsoft.com/en-us/cli/azure/) to deploy the ACA application.

(**Note:** On macOS/Linux: make sure to set executable permissions with: 
chmod +x ./deployment/az_bicep_deploy.sh)



The Bicep file is named **caig.bicep** and it uses the **caig.bicepparam** parameters file.

If you add/delete some of your environment variables, run the following command **impl\web_app** folder to generate the **caig.bicepparam** file
and the top of your **caig.bicep** file, per the **CAIG_xxx** environment variables that you have set on your workstation:

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