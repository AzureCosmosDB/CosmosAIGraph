package com.microsoft.cosmosdb.caig.models;

import com.microsoft.cosmosdb.caig.graph.TraversedNode;
import lombok.Data;

import java.util.HashMap;

/**
 * The WebApp responds with instance of this JSON-serialized class in response
 * to an HTTP POST request to the /sparql_query endpoint.
 * The HTTP request is invoked by the CosmosAIGraph web application.
 *
 * Chris Joakim, Aleksey Savateyev
 */

@Data
public class SparqlBomQueryResponse {

    private String entrypoint;
    private int max_depth;
    private int actual_depth;
    private HashMap<String, TraversedNode> nodes;
    private String error;
    private long elapsed;
    private long request_time;

    public SparqlBomQueryResponse(SparqlBomQueryRequest request) {
        this.entrypoint = request.getEntrypoint();
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
