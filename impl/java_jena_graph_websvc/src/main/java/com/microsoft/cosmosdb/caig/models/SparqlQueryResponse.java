package com.microsoft.cosmosdb.caig.models;

import lombok.Data;

import java.util.ArrayList;

/**
 * The WebApp responds with instance of this JSON-serialized class in response
 * to a HTTP POST request to the /sparql_query endpoint.
 * The HTTP request is invoked by the CosmosAIGraph web application.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class SparqlQueryResponse {

    private String sparql;
    private String results;
    private long elapsed;
    private String error;
    private String servertype;
    private long requestTime;

    public SparqlQueryResponse(SparqlQueryRequest request) {
        this.sparql = request.getSparql();
        this.servertype = "java";
        requestTime = System.currentTimeMillis();
    }

    public void finish() {
        this.elapsed = System.currentTimeMillis() - this.requestTime;
    }
}
