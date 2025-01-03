package com.microsoft.cosmosdb.caig.models;

import lombok.Data;

/**
 * The WebApp returns an instance of this JSON-serialized class in response to
 * a HTTP request to the /reload_graph endpoint.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class GraphReloadResponse {

    private final long startTime = System.currentTimeMillis();
    private long elapsedTime = -1;
    private String osName;
    private boolean doReload = false;
    private String message;
    private long docCount;

    public void finish() {
        this.elapsedTime = System.currentTimeMillis() - this.startTime;
    }
}