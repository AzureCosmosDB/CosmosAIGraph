package com.microsoft.cosmosdb.caig.models;

import lombok.Data;

import java.util.ArrayList;
import java.util.Map;

/**
 * The WebApp receives an instance of this JSON-serialized class
 * in a POST request to the /add_documents endpoint.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class AddDocumentsRequest {

    private ArrayList<Map<String, Object>> documents;
}

