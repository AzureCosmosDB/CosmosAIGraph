package com.microsoft.cosmosdb.caig.models;

import com.fasterxml.jackson.databind.JsonNode;
import com.microsoft.cosmosdb.caig.graph.DependenciesQueryResult;
import com.microsoft.cosmosdb.caig.graph.TraversedLib;
import lombok.Data;

import java.util.HashMap;
import java.util.Map;

/**
 * The WebApp responds with instance of this JSON-serialized class in response
 * to a HTTP POST request to the /sparql_query endpoint.
 * The HTTP request is invoked by the CosmosAIGraph web application.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class SparqlBomQueryResponse {

    private String libname;
    private int max_depth;
    private int actual_depth;
    private HashMap<String, TraversedLib> libs;
    private String error;
    private long elapsed;
    private long request_time;

    public SparqlBomQueryResponse(SparqlBomQueryRequest request) {
        this.libname = request.getLibname();
        this.max_depth = request.getMax_depth();
        this.actual_depth = 0;
        this.request_time = System.currentTimeMillis();
    }

    public void setActualDepth(int depth) {
        this.actual_depth = depth;
    }

    public void setError(String error) {
        this.error = error;
    }

    public void finish() {

        this.elapsed = System.currentTimeMillis() - this.request_time;
    }
}
