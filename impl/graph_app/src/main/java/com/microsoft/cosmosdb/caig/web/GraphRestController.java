package com.microsoft.cosmosdb.caig.web;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.graph.AppGraph;
import com.microsoft.cosmosdb.caig.graph.AppGraphBuilder;
import com.microsoft.cosmosdb.caig.models.*;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import com.microsoft.cosmosdb.caig.util.FileUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;

/**
 * This class implements the Graph functionality HTTP endpoints of this Spring application
 * per the @RestController annotation.
 *
 * Chris Joakim, Microsoft, 2025
 */

@RestController
public class GraphRestController {

    // Class variables
    private static Logger logger = LoggerFactory.getLogger(GraphRestController.class);
    private static boolean reloadInProgress = false;

    /**
     * Return the "single source of truth" ontology/OWL/XML used by the graph app,
     * to the web app, for the SPARQL generative-AI logic in the web application.
     */
    @GetMapping(value="/ontology", produces=MediaType.APPLICATION_XML_VALUE)
    public String ontology() {
        logger.warn("/ontology");
        String owlFilename = AppConfig.getGraphOwlFilename();
        String xml = new FileUtil().readUnicode(owlFilename);
        return xml;
    }

    @PostMapping("/sparql_query")
    SparqlQueryResponse postSparqlQuery(@RequestBody SparqlQueryRequest request) {
        logger.warn("/sparql_query");
        SparqlQueryResponse response = AppGraph.getSingleton().query(request);
        return response;
    }

    /**
     * This endpoint is for ad-hoc use such as in a development environment.
     * For production apps, the graph should be sourced from Cosmos DB data
     * rather than triples.
     * See the /add_documents endpoint, below, to mutate the graph from
     * Cosmos DB documents.
     */
    @PostMapping("/sparql_update")
    SparqlQueryResponse postSparqlUpdate(@RequestBody SparqlQueryRequest request) {
        logger.warn("/sparql_update");
        try {
            ObjectMapper mapper = new ObjectMapper();
            System.out.println(mapper.writerWithDefaultPrettyPrinter().writeValueAsString(request));
        } catch (JsonProcessingException e) {
            throw new RuntimeException(e);
        }
        SparqlQueryResponse response = AppGraph.getSingleton().update(request);
        return response;
    }

    @PostMapping("/sparql_bom_query")
    SparqlBomQueryResponse postSparqlBomQuery(@RequestBody SparqlBomQueryRequest request) {
        logger.warn("/sparql_bom_query");
        //SparqlBomQueryResponse response = new SparqlBomQueryResponse(request);
        // TODO - implement this endpoint for the D3.js UI visualizations


        SparqlBomQueryResponse response =
                AppGraph.getSingleton().bomQuery(request);
        return response;
    }

    @PostMapping("/add_documents")
    AddDocumentsResponse postSparqlBomQuery(@RequestBody AddDocumentsRequest request) {
        logger.warn("/add_documents");
        AddDocumentsResponse response = AppGraph.getSingleton().addDocuments(request.getDocuments());
        return response;
    }

    /**
     * This is a dev-environment convenience feature.
     * @return
     */
    @GetMapping("/reload_graph")
    public GraphReloadResponse reloadGraph() {
        logger.warn("/reload_graph");
        GraphReloadResponse response = new GraphReloadResponse();
        response.setOsName(System.getProperty("os.name").toLowerCase(Locale.ENGLISH));
        response.setDoReload(false);

        // ensure that this functionality can only be invoked in a development environment - Windows or macOS
        if (response.getOsName().contains("win")) {
            response.setDoReload(true);
        }
        if (response.getOsName().contains("mac")) {
            response.setDoReload(true);
        }

        if (reloadInProgress) {
            response.setDoReload(false);
            response.setMessage("a graph reload is already in progress; ignoring this request");
        }
        else {
            if (response.isDoReload()) {
                try {
                    reloadInProgress = true;
                    AppGraph appGraph = AppGraphBuilder.build(null);
                    AppGraph.setSingleton(appGraph);
                    response.setDocCount(appGraph.getDocsRead());
                }
                finally {
                    reloadInProgress = false;
                }
            }
        }
        response.finish();
        return response;
    }

}