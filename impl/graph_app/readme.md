# Java Impl Notes

## Links

- https://jena.apache.org/
- https://jena.apache.org/tutorials/rdf_api.html

## Quick Start

- Create the tmp directory
  - cd java_jena_graph_websvc
  - mkdir tmp
  
- Java and Gradle versions.
  - Java 21 is required
  - Gradle 8.11 or 8.12 is required
  - Query versions as shown below

```
PS ...\java_jena_graph_websvc> java --version
openjdk 21.0.5 2024-10-15 LTS
OpenJDK Runtime Environment Microsoft-10377968 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Microsoft-10377968 (build 21.0.5+11-LTS, mixed mode, sharing)


PS ...\java_jena_graph_websvc> gradle --version

------------------------------------------------------------
Gradle 8.12
------------------------------------------------------------

Build time:    2024-12-20 15:46:53 UTC
Revision:      a3cacb207fec727859be9354c1937da2e59004c1

Kotlin:        2.0.21
Groovy:        3.0.22
Ant:           Apache Ant(TM) version 1.10.15 compiled on August 25 2024
Launcher JVM:  21.0.5 (Microsoft 21.0.5+11-LTS)
Daemon JVM:    C:\Users\chjoakim\AppData\Local\Programs\Microsoft\jdk-21.0.5.11-hotspot (no JDK specified, using current Java home)
OS:            Windows 11 10.0 amd64
```

- Compile and package the app with either:
  - build.ps1
  - build.sh

- example-override.properties
  - Copy file example-override.properties to .override.properties
  - .override.properties has the same functionality as the .env file in python
  - Particularly important is CAIG_GRAPH_SOURCE_PATH
    - It may be one of: json_docs_file, rdf_file, or cosmos_nosql

- Start the app locally with either:
  - gradle bootRun
  - websvc.ps1
  - websvc.sh
  - docker compose -f docker-compose-graph-only.yml up
    - Be sure to edit this yml file as necessary
    - See docker-compose-graph-only.yml comments re: starting and stopping

- Test/Invoke the Graph Service HTTP endpoints
  - http_client.ps1
  - http_client.sh

- Java/Jena HTTP port is 8001, same as the Python implementation

