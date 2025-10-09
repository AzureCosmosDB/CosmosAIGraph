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
  - Python version 3.13.x or later is recommended
  - Conda is not recommended for this solution
- **OpenJDK Java 21 or later**
  - The graph microservice is implemented in Java 21, Spring Boot, and Apache Jena
  - Download from: https://learn.microsoft.com/en-us/java/openjdk/download#openjdk-21
  - See [Understanding the Code](understanding_the_code.md)
- A **Java IDE**, such as:
  - [Eclipse](https://eclipseide.org/)
  - [IntelliJ IDEA](https://www.jetbrains.com/idea/)
  - [Visual Studio Code (VSC)](https://code.visualstudio.com/)
- **Gradle Build Tool**, version 8.12
  - Used to compile and package the Java code
  - See https://gradle.org/
  - See the build.gradle file in the repo
  - Alternately use the Maven build tool
    - Create your pom.xml file per the build.gradle contents.

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
