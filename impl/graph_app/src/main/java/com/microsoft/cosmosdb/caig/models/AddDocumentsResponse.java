package com.microsoft.cosmosdb.caig.models;

import lombok.Data;

/**
 * The WebApp returns an instance of this JSON-serialized class
 * in response to the /add_documents endpoint.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class AddDocumentsResponse {

    private int inputDocumentsCount;
    private int processedDocumentsCount;
    private int failuresCount;
    private boolean successful = false;
    private String errorMessage = null;

    public void incrementProcessedDocumentsCount() {
        this.processedDocumentsCount++;
    }

    public void incrementFailuresCount() {
        this.failuresCount++;
    }

    public void finish() {
        if (this.errorMessage == null) {
            this.successful = true;
        }
        else {
            this.successful = false;
        }
        if (this.failuresCount > 0) {
            this.successful = false;
        }
    }
}

