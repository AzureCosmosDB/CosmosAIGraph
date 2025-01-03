FROM mcr.microsoft.com/openjdk/jdk:21-ubuntu
WORKDIR /app
COPY    . .
COPY    build/libs/java_jena_graph_websvc.jar /app/app.jar
RUN     mkdir -p tmp
EXPOSE  8080
ENTRYPOINT ["java", "-jar", "app.jar"]

# Build process:
#   1) See build.ps1 and build.sh which invokes "gradle clean build jar"
#      Creates file build\libs\java_jena_graph_websvc.jar
#   2) docker build -f Dockerfile -t cjoakim/caig_graph_java_jena_v1 .
#   3) docker push cjoakim/caig_graph_java_jena_v1:latest

# Local Execution with Compose:
#   docker compose -f docker-compose-graph-only.yml up
#   docker compose -f docker-compose-graph-only.yml down
