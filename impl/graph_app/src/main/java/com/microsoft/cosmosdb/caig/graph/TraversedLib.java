package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.Data;

import java.util.ArrayList;
import java.util.Map;

/**
 * Instances of this class represent a Library that is traversed in a
 * Bill-of-Material (BOM) traversal.  Instances are created in AppGraph
 * and returned within a SparqlBomQueryResponse to the Web App.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class TraversedLib {

    private String uri;
    private String name;
    private boolean visited;
    private int depth;
    private ArrayList<String> dependencies;
    //private DependenciesQueryResult dependenciesQueryResult;

    public TraversedLib(String uri, int depth) {
        this.uri = uri;
        this.depth = depth;
        this.visited = false;
        dependencies = new ArrayList<String>();
        int idx = this.uri.indexOf('#');
        this.name = this.uri.substring(idx + 1);
    }

}
