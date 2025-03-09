package com.microsoft.cosmosdb.caig.models;

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
public class SparqlQueryResponse {

    private String sparql;
    private Map<String, Object> results = new HashMap<>();
    private long elapsed;
    private String error;
    private long start_time;
    private long finish_time;

    public SparqlQueryResponse() {
        super();
    }

    public SparqlQueryResponse(SparqlQueryRequest request) {
        this();
        this.sparql = request.getSparql();
        this.error = "";
        start_time = System.currentTimeMillis();
    }

    public void finish() {
        this.finish_time = System.currentTimeMillis();
        this.elapsed = this.finish_time - this.start_time;
    }
}
