package com.microsoft.cosmosdb.caig.graph;

import lombok.Data;
import java.util.HashMap;
import java.util.Map;

/**
 * Represents a rich dependency relationship in the TTL graph.
 * Instead of just storing a simple URI string, this class captures
 * all the TTL properties of a dependency dynamically from the loaded ontology.
 * 
 * This enables richer graph visualizations with meaningful edge labels
 * and detailed tooltips showing actual domain properties from any ontology.
 * 
 * Aleksey Savateyev
 */
@Data
public class RichDependency {
    
    private String uri;
    private String name;
    private String type;
    private Map<String, Object> properties;
    
    public RichDependency() {
        this.properties = new HashMap<>();
    }
    
    public RichDependency(String uri) {
        this();
        this.uri = uri;
        // Extract name from URI (after # or /)
        if (uri != null) {
            int hashIndex = uri.lastIndexOf('#');
            int slashIndex = uri.lastIndexOf('/');
            int startIndex = Math.max(hashIndex, slashIndex);
            if (startIndex >= 0 && startIndex < uri.length() - 1) {
                this.name = uri.substring(startIndex + 1);
            } else {
                this.name = uri;
            }
        }
    }
    
    /**
     * Add a property to this dependency
     */
    public void addProperty(String key, Object value) {
        if (key != null && value != null) {
            this.properties.put(key, value);
        }
    }
    
    /**
     * Get a property value as String, with null safety
     */
    public String getStringProperty(String key) {
        Object value = this.properties.get(key);
        return value != null ? value.toString() : null;
    }
    
    /**
     * Get a property value as Double, with null safety
     */
    public Double getDoubleProperty(String key) {
        Object value = this.properties.get(key);
        if (value instanceof Number) {
            return ((Number) value).doubleValue();
        } else if (value instanceof String) {
            try {
                return Double.parseDouble((String) value);
            } catch (NumberFormatException e) {
                return null;
            }
        }
        return null;
    }
    
    /**
     * Check if this dependency has a specific property
     */
    public boolean hasProperty(String key) {
        return this.properties.containsKey(key) && this.properties.get(key) != null;
    }
    
    /**
     * Generate a meaningful display label for this dependency based on its properties
     * Uses dynamic prioritization based on available properties
     */
    public String getDisplayLabel() {
        // Priority order: look for common identifier properties
        String[] priorityKeys = {"name", "label", "title", "identifier", "id", "tag", "itemTag", "drawingNumber"};
        
        for (String key : priorityKeys) {
            String value = getStringProperty(key);
            if (value != null && !value.isEmpty()) {
                return value;
            }
        }
        
        // Try case-insensitive search for these common patterns
        for (String propKey : this.properties.keySet()) {
            String lowerKey = propKey.toLowerCase();
            if (lowerKey.contains("name") || lowerKey.contains("label") || 
                lowerKey.contains("title") || lowerKey.contains("tag")) {
                String value = getStringProperty(propKey);
                if (value != null && !value.isEmpty()) {
                    return value;
                }
            }
        }
        
        if (this.name != null && !this.name.isEmpty()) {
            return this.name;
        }
        
        return this.uri != null ? this.uri : "Unknown";
    }
    
    /**
     * Generate a meaningful edge label for graph visualization
     * Shows actual property names from the TTL graph using dynamic discovery
     */
    public String getEdgeLabel() {
        // HIGHEST PRIORITY: Use the EdgeLabel property set by AppGraph (entity type-based labeling)
        String edgeLabel = getStringProperty("EdgeLabel");
        if (edgeLabel != null && !edgeLabel.isEmpty()) {
            return edgeLabel;
        }
        
        // Second priority: Show the actual connecting property name
        String connectingProperty = getStringProperty("ConnectingProperty");
        if (connectingProperty != null && !connectingProperty.isEmpty()) {
            return connectingProperty;
        }
        
        // Look for common meaningful properties in order of priority
        String[] priorityKeys = {
            // Relationship properties
            "relationship", "relation", "edge", "link", "connection",
            // Identifier properties  
            "name", "label", "title", "identifier", "id", "tag",
            // Type/classification properties
            "type", "category", "class", "classification",
            // Numeric/measurement properties
            "value", "size", "diameter", "length", "weight"
        };
        
        for (String key : priorityKeys) {
            String value = getStringProperty(key);
            if (value != null && !value.isEmpty()) {
                return key + ":" + value;
            }
        }
        
        // Search for properties with common patterns (case-insensitive)
        for (String propKey : this.properties.keySet()) {
            String lowerKey = propKey.toLowerCase();
            Object value = this.properties.get(propKey);
            
            // Prefer shorter, more meaningful property names
            if (lowerKey.length() <= 15 && value != null) {
                String strValue = value.toString();
                if (!strValue.isEmpty() && strValue.length() <= 20) {
                    // Skip generic/system properties
                    if (!lowerKey.startsWith("rdf") && !lowerKey.startsWith("owl") && 
                        !lowerKey.startsWith("rdfs") && !lowerKey.equals("type")) {
                        return propKey + ":" + strValue;
                    }
                }
            }
        }
        
        // Look for any connecting relationship properties
        for (String propKey : this.properties.keySet()) {
            String lowerKey = propKey.toLowerCase();
            if (lowerKey.contains("start") || lowerKey.contains("end") || 
                lowerKey.contains("from") || lowerKey.contains("to") || 
                lowerKey.contains("source") || lowerKey.contains("target")) {
                Object value = this.properties.get(propKey);
                if (value != null) {
                    return propKey;
                }
            }
        }
        
        // Final fallback: use the first available property
        if (!this.properties.isEmpty()) {
            String firstKey = this.properties.keySet().iterator().next();
            Object firstValue = this.properties.get(firstKey);
            if (firstValue != null && !firstKey.toLowerCase().startsWith("rdf") && 
                !firstKey.toLowerCase().startsWith("owl") && !firstKey.toLowerCase().startsWith("rdfs")) {
                String strValue = firstValue.toString();
                if (strValue.length() <= 15) {
                    return firstKey + ":" + strValue;
                } else {
                    return firstKey;
                }
            }
        }
        
        return "connected";
    }
    
    /**
     * Generate a detailed tooltip text for this dependency
     * Shows all available properties dynamically
     */
    public String getTooltipText() {
        StringBuilder tooltip = new StringBuilder();
        
        String displayLabel = getDisplayLabel();
        tooltip.append("Entity: ").append(displayLabel).append("\n");
        
        // Show all properties except system ones
        for (Map.Entry<String, Object> entry : this.properties.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();
            
            // Skip system/technical properties
            if (key.toLowerCase().startsWith("rdf") || 
                key.toLowerCase().startsWith("owl") || 
                key.toLowerCase().startsWith("rdfs") ||
                key.equals("ConnectingProperty")) {
                continue;
            }
            
            if (value != null) {
                String strValue = value.toString();
                if (strValue.length() > 50) {
                    strValue = strValue.substring(0, 47) + "...";
                }
                tooltip.append(key).append(": ").append(strValue).append("\n");
            }
        }
        
        return tooltip.toString().trim();
    }
}
