package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * Instances of this class are used to parse a JENA SPARQL query response,
 * the "bindings" portion within the Jena query response.
 * The Jackson JSON library is used to do this.
 *
 * Chris Joakim, Microsoft, 2025
 */

public class ResultsBindings {

    @JsonProperty("bindings")
    public List<Map> bindings;

    public ResultsBindings() {
        super();
    }
}
