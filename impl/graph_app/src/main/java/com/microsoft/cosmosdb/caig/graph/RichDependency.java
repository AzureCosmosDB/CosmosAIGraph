package com.microsoft.cosmosdb.caig.graph;

import lombok.Data;
import java.util.HashMap;
import java.util.Map;

/**
 * Represents a rich dependency relationship in the TTL graph.
 * Instead of just storing a simple URI string, this class captures
 * all the TTL properties of a dependency like DrawingNumber, ItemTag,
 * NominalDiameter, FlowDir, Type, StartNode, EndNode, etc.
 * 
 * This enables richer graph visualizations with meaningful edge labels
 * and detailed tooltips showing engineering properties.
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
     */
    public String getDisplayLabel() {
        // Priority order for display labels
        String itemTag = getStringProperty("ItemTag");
        if (itemTag != null && !itemTag.isEmpty()) {
            return itemTag;
        }
        
        String drawingNumber = getStringProperty("DrawingNumber");
        if (drawingNumber != null && !drawingNumber.isEmpty()) {
            return drawingNumber;
        }
        
        if (this.name != null && !this.name.isEmpty()) {
            return this.name;
        }
        
        return this.uri != null ? this.uri : "Unknown";
    }
    
    /**
     * Generate a meaningful edge label for graph visualization
     * Shows actual property names from the TTL graph
     */
    public String getEdgeLabel() {
        // Highest priority: Show the actual connecting property name
        String connectingProperty = getStringProperty("ConnectingProperty");
        if (connectingProperty != null && !connectingProperty.isEmpty()) {
            return connectingProperty;
        }
        
        // First priority: Show actual ItemTag if available
        String itemTag = getStringProperty("ItemTag");
        if (itemTag != null && !itemTag.isEmpty()) {
            return itemTag;
        }
        
        // Second priority: Show the connecting property name with diameter
        String nominalDiameter = getStringProperty("NominalDiameter");
        if (nominalDiameter != null && !nominalDiameter.isEmpty()) {
            return "NominalDiameter:" + nominalDiameter;
        }
        
        // Third priority: Show the actual connection property that created this edge
        if (hasProperty("StartNode") && hasProperty("EndNode")) {
            return "StartNode→EndNode";
        } else if (hasProperty("StartNode")) {
            return "StartNode";
        } else if (hasProperty("EndNode")) {
            return "EndNode";
        }
        
        // Fourth priority: Show FlowDir property if available
        String flowDir = getStringProperty("FlowDir");
        if (flowDir != null && !flowDir.isEmpty()) {
            return "FlowDir:" + flowDir.replace("StartNode to EndNode", "S→E");
        }
        
        // Fifth priority: Show the Type property
        String type = getStringProperty("Type");
        if (type != null && !type.isEmpty()) {
            return "Type:" + type;
        }
        
        // Sixth priority: Show DrawingNumber if available
        String drawingNumber = getStringProperty("DrawingNumber");
        if (drawingNumber != null && !drawingNumber.isEmpty()) {
            return "Drawing:" + drawingNumber.substring(drawingNumber.lastIndexOf('-') + 1);
        }
        
        // Last resort: Show RunID
        String runId = getStringProperty("RunID");
        if (runId != null && !runId.isEmpty()) {
            return "RunID:" + runId.substring(0, Math.min(8, runId.length()));
        }
        
        return "Property:Unknown";
    }
    
    /**
     * Generate a detailed tooltip text for this dependency
     */
    public String getTooltipText() {
        StringBuilder tooltip = new StringBuilder();
        
        String displayLabel = getDisplayLabel();
        tooltip.append("Equipment: ").append(displayLabel).append("\n");
        
        if (hasProperty("Type")) {
            tooltip.append("Type: ").append(getStringProperty("Type")).append("\n");
        }
        
        if (hasProperty("NominalDiameter")) {
            Double diameter = getDoubleProperty("NominalDiameter");
            if (diameter != null) {
                tooltip.append("Diameter: ").append(diameter).append("\n");
            }
        }
        
        if (hasProperty("FlowDir")) {
            tooltip.append("Flow Direction: ").append(getStringProperty("FlowDir")).append("\n");
        }
        
        if (hasProperty("DrawingNumber")) {
            tooltip.append("Drawing: ").append(getStringProperty("DrawingNumber")).append("\n");
        }
        
        if (hasProperty("RunID")) {
            tooltip.append("Run ID: ").append(getStringProperty("RunID")).append("\n");
        }
        
        return tooltip.toString().trim();
    }
}
