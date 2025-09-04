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
 * Enhanced to support rich dependency information from TTL properties.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class TraversedLib {

    private String uri;
    private String name;
    private boolean visited;
    private int depth;
    private ArrayList<String> dependencies; // Keep for backwards compatibility
    private ArrayList<RichDependency> richDependencies; // New rich dependency objects
    //private DependenciesQueryResult dependenciesQueryResult;

    public TraversedLib(String uri, int depth) {
        this.uri = uri;
        this.depth = depth;
        this.visited = false;
        dependencies = new ArrayList<String>();
        richDependencies = new ArrayList<RichDependency>();
        int idx = this.uri.indexOf('#');
        this.name = this.uri.substring(idx + 1);
    }
    
    /**
     * Add a rich dependency with TTL properties
     */
    public void addRichDependency(RichDependency richDep) {
        if (richDep != null) {
            this.richDependencies.add(richDep);
            // Also add to the legacy dependencies list for backwards compatibility
            if (richDep.getUri() != null) {
                this.dependencies.add(richDep.getUri());
            }
        }
    }
    
    /**
     * Set both rich and legacy dependencies
     */
    public void setRichDependencies(ArrayList<RichDependency> richDeps) {
        this.richDependencies = richDeps != null ? richDeps : new ArrayList<RichDependency>();
        
        // Update legacy dependencies list for backwards compatibility
        this.dependencies.clear();
        for (RichDependency richDep : this.richDependencies) {
            if (richDep.getUri() != null) {
                this.dependencies.add(richDep.getUri());
            }
        }
    }

}
