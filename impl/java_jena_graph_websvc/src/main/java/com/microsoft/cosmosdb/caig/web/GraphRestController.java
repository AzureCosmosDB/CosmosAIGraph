package com.microsoft.cosmosdb.caig.web;

import com.microsoft.cosmosdb.caig.graph.AppGraph;
import com.microsoft.cosmosdb.caig.graph.AppGraphBuilder;
import com.microsoft.cosmosdb.caig.models.*;
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

    private static boolean reloadInProgress = false;

    @PostMapping("/sparql_query")
    SparqlQueryResponse postSparqlQuery(@RequestBody SparqlQueryRequest request) {
        SparqlQueryResponse response = AppGraph.getSingleton().query(request);
        return response;
    }

    @PostMapping("/sparql_bom_query")
    SparqlBomQueryResponse postSparqlBomQuery(@RequestBody SparqlBomQueryRequest request) {
        SparqlBomQueryResponse response = new SparqlBomQueryResponse(request);
        // TODO - implement this endpoint for the D3.js UI visualizations
        return response;
    }

    /**
     * This is a dev-environment convenience feature.
     * @return
     */
    @GetMapping("/reload_graph")
    public GraphReloadResponse reloadGraph() {
        GraphReloadResponse response = new GraphReloadResponse();
        response.setOsName(System.getProperty("os.name").toLowerCase(Locale.ENGLISH));
        response.setDoReload(false);

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