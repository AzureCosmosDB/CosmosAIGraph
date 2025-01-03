package com.microsoft.cosmosdb.caig.models;

import lombok.Data;

/**
 * The WebApp returns an instance of this JSON-serialized class in response to
 * a HTTP request to the /health endpoint.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class HealthResponse {

    private final long epoch = System.currentTimeMillis();
    private int code;
    private String message;
    private long successfulQueries;
    private long unsuccessfulQueries;
    private long lastSuccessfulQueryTime;
}