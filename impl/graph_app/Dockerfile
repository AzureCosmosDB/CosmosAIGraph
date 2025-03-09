FROM mcr.microsoft.com/openjdk/jdk:21-ubuntu
WORKDIR /app
COPY    . .
COPY    build/libs/caig_graph_app.jar /app/app.jar
RUN     mkdir -p tmp
EXPOSE  8001
ENTRYPOINT ["java", "-jar", "app.jar"]
