package com.microsoft.cosmosdb.caig.graph;

import lombok.Data;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

/**
 * Instances of this class represent a node that is traversed in a
 * Bill-of-Material (BOM) traversal.  Instances are created in AppGraph
 * and returned within a SparqlBomQueryResponse to the Web App.
 *
 * Enhanced to support rich dependency information from TTL properties.
 *
 * Chris Joakim, Aleksey Savateyev
 */

@Data
public class TraversedNode {

    private String uri;
    private String name; // A.S. Extracting name from URI
    private boolean visited;
    private int depth;
    private ArrayList<String> dependencies; // Keep for backwards compatibility
    private ArrayList<RichDependency> richDependencies; // A.S. Rich dependency objects to support edge labels
    private Map<String, Object> selfProperties; // Properties of this node itself

    public TraversedNode(String uri, int depth) {

        this.uri = uri;
        this.depth = depth;
        this.visited = false;
        this.dependencies = new ArrayList<String>();
        this.richDependencies = new ArrayList<RichDependency>(); // A.S.
        this.selfProperties = new HashMap<String, Object>();

        // A.S. Extract name from URI
        // Try to find the last '#' first, then the last '/'
        int hashIdx = this.uri.lastIndexOf('#');
        int slashIdx = this.uri.lastIndexOf('/');

        // Use whichever delimiter appears last
        int idx = Math.max(hashIdx, slashIdx);

        if (idx >= 0 && this.uri.length() > idx + 1) {
            this.name = this.uri.substring(idx + 1);
        } else {
            // Fallback to the full URI if no delimiter found
            this.name = this.uri;
        }
    }

    // A.S.
    public void addRichDependency(RichDependency richDep) {
        this.richDependencies.add(richDep);
        this.dependencies.add(richDep.getUri());
    }

    // A.S.
    public void setRichDependencies(ArrayList<RichDependency> richDeps) {
        this.richDependencies = richDeps;

        // Update dependencies to be in sync with rich dependencies
        this.dependencies.clear();
        for (RichDependency rd : richDeps) {
            this.dependencies.add(rd.getUri());
        }
    }

    /**
     * Get a property value from the node's own properties
     */
    public Object getProperty(String key) {
        return selfProperties.get(key);
    }

    /**
     * Get a string property value, with null handling
     */
    public String getStringProperty(String key) {
        Object value = selfProperties.get(key);
        return value != null ? value.toString() : null;
    }
}
