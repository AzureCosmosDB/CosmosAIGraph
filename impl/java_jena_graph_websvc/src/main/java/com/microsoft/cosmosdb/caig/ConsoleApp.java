package com.microsoft.cosmosdb.caig;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.graph.AppGraph;
import com.microsoft.cosmosdb.caig.graph.AppGraphBuilder;
import com.microsoft.cosmosdb.caig.models.SparqlQueryRequest;
import com.microsoft.cosmosdb.caig.models.SparqlQueryResponse;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import com.microsoft.cosmosdb.caig.util.FileUtil;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.Model;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.ByteArrayOutputStream;
import java.util.ArrayList;

/**
 * This class implements ad-hoc command-line/console-app functionality and
 * generally doesn't leverage Spring beans/containers/services, etc..
 *
 * The primary intent of this class is to develop and test the AppGraph
 * creation process.
 *
 * The main class is: com.microsoft.cosmosdb.caig.ConsoleApp
 * See task "consoleApp" in the Gradle build.gradle file where
 * this class is executed from.
 *
 * Chris Joakim, Microsoft, 2025
 */

public class ConsoleApp {

    private static Logger logger = LogManager.getLogger(ConsoleApp.class);

    public static void main(String[] args) {

        try {
            ObjectMapper objectMapper = new ObjectMapper();
            logger.warn(objectMapper.writeValueAsString(args));
            // ["generateArtifacts","b","c"]
        }
        catch (JsonProcessingException e) {
            throw new RuntimeException(e);
        }
        AppConfig.initialize();
        AppConfig.logDefinedEnvironmentVariables();

        String function = args[0];
        switch(function) {
            case "invokeGraphBuilder":
                invokeGraphBuilder();
                break;
            case "generateArtifacts":
                generateArtifacts();
                break;
            default:
                logger.error("ConsoleApp- unknown function: " + function);
        }

        //invokeGraphBuilder();
        System.exit(0);
    }

    private static void invokeGraphBuilder() {
        try {
            logger.warn("getGraphSourceType:  " + AppConfig.getGraphSourceType());
            logger.warn("dumpGraphUponBuild:  " + AppConfig.dumpGraphUponBuild());
            logger.warn("getGraphDumpOutfile: " + AppConfig.getGraphDumpOutfile());

            String query = countTriplesQuery();
            AppGraph appGraph = AppGraphBuilder.build(query);
            AppGraph.setSingleton(appGraph);

            queryGraph(countTriplesQuery());
            queryGraph(getNTriplesQuery(20));
            queryGraph(usesFlaskQuery());

            AppConfig.logDefinedEnvironmentVariables();
        }
        catch (Throwable t) {
            t.printStackTrace();
        }
    }

    private static void generateArtifacts() {
        logger.warn("generateArtifacts...");
        generateDockerComposeGraphService();
    }

    private static void generateDockerComposeGraphService() {
        logger.warn("generateDockerComposeGraphService...");
        String[] envVars = AppConfig.DEFINED_ENVIRONMENT_VARIABLES;
        ArrayList<String> lines = new ArrayList<String>();
        lines.add("  graph_service:");
        lines.add("    image: cjoakim/caig_graph_java_jena_v1:latest");
        lines.add("    ports:");
        lines.add("      - \"8001:8001\"");
        lines.add("    volumes:");
        lines.add("      - ./tmp:/tmp:rw");
        lines.add("    environment:");
        for (int i = 0; i < envVars.length; i++) {
            String envVar = envVars[i];
            String line = String.format("      %-36s $%s", envVar+":", envVar);
            lines.add(line);
        }
        lines.add("");
        try {
            FileUtil util = new FileUtil();
            util.writeLines("tmp/graph_service_compose.txt", lines, true);
        }
        catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static String getNTriplesQuery(int n) {
        return "SELECT * WHERE { ?s ?p ?o . } LIMIT " + n;
    }
    private static String countTriplesQuery() {
        return "SELECT (COUNT(?s) AS ?triples) WHERE { ?s ?p ?o }";
    }
    private static String usesFlaskQuery() {
        return "PREFIX c: <http://cosmosdb.com/caig#> SELECT ?used_lib WHERE { <http://cosmosdb.com/caig/pypi_flask> c:uses_lib ?used_lib . } LIMIT 10";
    }

    private static SparqlQueryResponse queryGraph(String queryString) {
        logger.warn("ConsoleApp#queryModel: " + queryString);

        SparqlQueryRequest request = new SparqlQueryRequest();
        request.setSparql(queryString);
        SparqlQueryResponse response = AppGraph.getSingleton().query(request);
        ObjectMapper mapper = new ObjectMapper();
        try {
            String json = mapper.writerWithDefaultPrettyPrinter().writeValueAsString(response);
            System.out.println(json);
        } catch (JsonProcessingException e) {
            e.printStackTrace();
        }
        return response;
    }

}
