package com.microsoft.cosmosdb.caig.models;

import lombok.Data;

/**
 * The WebApp receives an instance of this JSON-serialized class to execute
 * a given SPARQL in a POST request to the /sparql_query endpoint.
 * The HTTP request is invoked by the CosmosAIGraph web application.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class SparqlQueryRequest {

    private String sparql;

    public SparqlQueryRequest() {
        super();
    }
}

