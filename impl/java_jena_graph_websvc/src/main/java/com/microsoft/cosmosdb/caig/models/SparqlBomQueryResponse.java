package com.microsoft.cosmosdb.caig.models;

import lombok.Data;

import java.util.HashMap;

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
    private String libtype;
    private int max_depth;
    private int actual_depth;
    private HashMap<String, String> bom_libs;
    private String error;
    private long elapsed;
    private long requestTime;

    public SparqlBomQueryResponse(SparqlBomQueryRequest request) {
        this.libname = request.getLibname();
        this.libtype = request.getLibtype();
        this.max_depth = request.getMax_depth();
        this.requestTime = System.currentTimeMillis();
    }

    public void finish() {
        this.elapsed = System.currentTimeMillis() - this.requestTime;
    }
}
