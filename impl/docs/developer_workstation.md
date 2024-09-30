# CosmosAIGraph : Developer Workstation Setup

## Required Software

These are required to simply execute the solution on your workstation:

- **Windows 11 with PowerShell**
  - For Development, Windows 11 with PowerShell is recommended
  - Working bash scripts are also provided for macOS users
- [Git](https://git-scm.com/)
  - Distributed source control system.  Integrates with GitHub
  - Enables you to **git clone** this GitHub repository
- [Python3](https://www.python.org/downloads/)
  - This solution uses Python command-line and web application programs, not Jupyter Notebooks
  - Python version 3.12.x is recommended
  - Conda is not recommended for this solution
- **A Mongo Shell Program**, such as:
  - [Azure Data Studio](https://azure.microsoft.com/en-us/products/data-studio)
    - This is the recommended mongosh program for the CosmosAIGraph solution
    - See the configuration instructions here:
      - https://learn.microsoft.com/en-us/azure-data-studio/quickstart-azure-cosmos-db-mongodb?tabs=mongodb-vcore
  - [mongosh](https://www.mongodb.com/docs/mongodb-shell/install/)
    - The MSI installer option is recommended if you choose to use this program
  - [Studio3T](https://studio3t.com/)

Also, a working knowledge of **pip and Python Virtual Environments** is necessary.
See https://realpython.com/python-virtual-environments-a-primer/.

This reference implementation contains several **venv.ps1** and **venv.sh** scripts
which create the Python Virtual Environments for this solution.  Once these
are created, they can be **activated** with the following command:

```
> .\venv\Scripts\Activate.ps1
```

## Recommended Software

To develop your own solutions based on this reference application, 
this additional software is recommended:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - Docker Desktop will enable you to both build and execute containers
- [GitHub Desktop](https://desktop.github.com/)
  - Provides a nice UI and may be easier to use than the git command-line program
- [Visual Studio Code (VSC)](https://code.visualstudio.com/)
  - Lightweight IDE with multi-language support, including Python
  - Integrates well with Azure, see https://code.visualstudio.com/docs/azure/extensions
- [GitHub Copilot](https://github.com/features/copilot)
  - AI-powered coding assistant
  - Copilot integrates nicely with VSC; see https://code.visualstudio.com/docs/copilot/overview
- [Apache Ant and Java 1.8+](https://ant.apache.org/)
  - Ant is only necessary for the deploy_master_code.ps1 script
  - See [Understanding the Code](understanding_the_code.md)
