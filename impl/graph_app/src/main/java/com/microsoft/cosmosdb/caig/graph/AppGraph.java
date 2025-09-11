package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.models.*;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFWriter;
import org.apache.jena.riot.RIOT;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.update.UpdateExecution;
import org.apache.jena.update.UpdateExecutionFactory;
import org.apache.jena.update.UpdateFactory;
import org.apache.jena.update.UpdateRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Instances of this class represent the in-memory Application Graph object.
 * The name "AppGraph" was chosen so as not to collide with a similarly named class in the
 * Apache Jena codebase.
 *
 * Chris Joakim, Aleksey Savateyev
 */
public class AppGraph {

    // Class variables
    private static Logger logger = LoggerFactory.getLogger(AppGraph.class);
    private static AppGraph singleton = null;  // created by GraphBuilder at ApplicationStartup

    // Instance variables
    private long docsRead = 0;
    private Model model;
    final private String namespace;
    private long successfulQueries;
    private long unsuccessfulQueries;
    private long lastSuccessfulQueryTime;
    private long successfulUpdates;
    private long unsuccessfulUpdates;
    private long lastSuccessfulUpdateTime;

    public AppGraph() {

        super();
        this.namespace = AppConfig.getGraphNamespace();
        this.successfulQueries = 0;
        this.unsuccessfulQueries = 0;
        this.lastSuccessfulQueryTime = 0;
        this.successfulUpdates = 0;
        this.unsuccessfulUpdates = 0;
        this.lastSuccessfulUpdateTime = 0;
    }

    public static AppGraph getSingleton() {
        logger.debug("getSingleton - model impl class: " + singleton.getModel().getClass().getName());
        return singleton;
    }

    public static void setSingleton(AppGraph g) {
        logger.debug("setSingleton - model impl class: " + g.getModel().getClass().getName());
        singleton = g;
    }

    /**
     * Query the in-memory graph using the SPARQL in the given SparqlQueryRequest object.
     * The "synchronized" keyword is used here to allow only one thread to execute at any given time.
     * Each HTTP request runs in its own Thread.
     */
    public synchronized SparqlQueryResponse query(SparqlQueryRequest request) {
        logger.warn("query: " + request.getSparql());
        SparqlQueryResponse response = new SparqlQueryResponse(request);
        QueryExecution qexec = null;
        try {
            Query query = QueryFactory.create(response.getSparql());
            qexec = QueryExecutionFactory.create(
                    query, AppGraph.getSingleton().getModel());
            ResultSet results = qexec.execSelect();
            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            ResultSetFormatter.outputAsJSON(outputStream, results);
            String json = new String(outputStream.toByteArray()).replaceAll("\\n", "");
            //System.out.println("query - json: " + json);
            ObjectMapper objectMapper = new ObjectMapper();
            Map<String, Object> map
                    = objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {
            });
            response.setResults(map);
            successfulQueries++;
            lastSuccessfulQueryTime = System.currentTimeMillis();
        } catch (Exception e) {
            unsuccessfulQueries++;
            logger.error("query - Exception on sparql: " + request.getSparql());
            logger.error(e.getMessage());
            response.setError(e.getMessage());
        } finally {
            if (qexec != null) {
                qexec.close();
            }
        }
        response.finish();
        return response;
    }


    public synchronized SparqlBomQueryResponse bomQuery(SparqlBomQueryRequest request) {
        logger.warn("bomQuery - entry point: " + request.getEntrypoint());
        SparqlBomQueryResponse response = new SparqlBomQueryResponse(request);
        HashMap<String, TraversedNode> nodes = new HashMap<String, TraversedNode>();
        response.setNodes(nodes);
        
        // First try exact ID matching
        String exactNodeUri = namespaceWithSeparator() + response.getEntrypoint();
        boolean foundExactMatch = nodeExists(exactNodeUri);
        
        if (foundExactMatch) {
            logger.info("Found exact match for: " + exactNodeUri);
            nodes.put(exactNodeUri, new TraversedNode(exactNodeUri, 0));
            logger.info("Added root node with depth 0: " + exactNodeUri);
        } else {
            logger.info("No exact match found for: " + exactNodeUri + ", trying loose attribute matching");
            // Try loose matching against all attributes
            Set<String> matchingNodes = findNodesByLooseMatching(request.getEntrypoint());
            if (!matchingNodes.isEmpty()) {
                logger.info("Found " + matchingNodes.size() + " nodes with loose matching");
                for (String matchingNodeUri : matchingNodes) {
                    nodes.put(matchingNodeUri, new TraversedNode(matchingNodeUri, 0));
                    logger.info("Added root node with depth 0: " + matchingNodeUri);
                }
            } else {
                logger.warn("No nodes found with loose matching for: " + request.getEntrypoint());
                // Still add the original URI to avoid empty response
                nodes.put(exactNodeUri, new TraversedNode(exactNodeUri, 0));
                logger.info("Added fallback root node with depth 0: " + exactNodeUri);
            }
        }
        
        QueryExecution qexec = null;
        try {
            boolean continueToProcess = true;
            int maxDepth = request.getMax_depth();
            int loopDepth = 0;
            int loopStartCount = 0;
            int loopFinishCount = 0;

            while (continueToProcess) {
                loopDepth++;
                loopStartCount = nodes.size();
                response.setActualDepth(loopDepth);
                logger.info("=== BOM Loop " + loopDepth + " starting, maxDepth=" + maxDepth + ", nodeCount=" + loopStartCount + " ===");

                if (loopDepth > maxDepth) {
                    logger.info("Terminating: loopDepth (" + loopDepth + ") > maxDepth (" + maxDepth + ")");
                    continueToProcess = false;
                } else {
                    Object[] nodeUris = nodes.keySet().toArray();
                    logger.warn("loop: " + loopDepth + " count " + nodeUris.length);
                    for (int i = 0; i < nodeUris.length; i++) {
                        String nodeUri = (String) nodeUris[i];
                        logger.debug("nodeUri: " + nodeUri + " idx " + i);
                        TraversedNode tLib = nodes.get(nodeUri);
                        if (tLib.isVisited()) {
                            logger.debug("nodeUri already visited: " + nodeUri + " (depth=" + tLib.getDepth() + ")");
                        } else {
                            logger.info("Processing unvisited node: " + nodeUri + " (current depth=" + tLib.getDepth() + ", assigning new deps to depth=" + loopDepth + ")");
                            queryDependencies(tLib, nodes, loopDepth);
                        }
                    }
                    // Terminate the graph traversal
                    loopFinishCount = nodes.size();
                    logger.info("=== BOM Loop " + loopDepth + " finished, startCount=" + loopStartCount + ", finishCount=" + loopFinishCount + " ===");
                    if (loopFinishCount == loopStartCount) {
                        logger.info("No new nodes found, terminating");
                        continueToProcess = false;
                    }
                }
            }
        } catch (Exception e) {
            unsuccessfulQueries++;
            logger.error(e.getMessage());
            response.setError(e.getMessage());
        } finally {
            if (qexec != null) {
                qexec.close();
            }
        }
        response.finish();
        return response;
    }

    // Helper to ensure the configured namespace ends with a separator (# or /)
    private String namespaceWithSeparator() {
        if (this.namespace == null || this.namespace.isEmpty()) {
            return "http://schema.org/ontology#";
        }
        if (this.namespace.endsWith("#") || this.namespace.endsWith("/")) {
            return this.namespace;
        }
        return this.namespace + "#";
    }

    /**
     * Check if a node with the exact URI exists in the graph
     */
    private boolean nodeExists(String nodeUri) {
        QueryExecution qexec = null;
        try {
            String sparql = "PREFIX c: <" + namespaceWithSeparator() + ">\n" +
                           "ASK { " + formatUri(nodeUri) + " ?p ?o }";
            
            Query query = QueryFactory.create(sparql);
            qexec = QueryExecutionFactory.create(query, this.model);
            boolean exists = qexec.execAsk();
            logger.debug("nodeExists check for " + nodeUri + ": " + exists);
            return exists;
        } catch (Exception e) {
            logger.error("Error checking if node exists: " + nodeUri, e);
            return false;
        } finally {
            if (qexec != null) {
                qexec.close();
            }
        }
    }

    /**
     * Find nodes by loose matching against all attributes
     * Returns URIs of nodes that have any attribute containing the search term
     */
    private Set<String> findNodesByLooseMatching(String searchTerm) {
        Set<String> matchingNodes = new HashSet<>();
        QueryExecution qexec = null;
        try {
            // Build SPARQL query to find any subject that has any property with a value containing the search term
            String sparql = "PREFIX c: <" + namespaceWithSeparator() + ">\n" +
                           "SELECT DISTINCT ?subject WHERE {\n" +
                           "  ?subject ?property ?value .\n" +
                           "  FILTER(isLiteral(?value) && CONTAINS(LCASE(STR(?value)), LCASE(\"" + searchTerm + "\")))\n" +
                           "} LIMIT 50";
            
            logger.debug("Loose matching SPARQL: " + sparql);
            
            Query query = QueryFactory.create(sparql);
            qexec = QueryExecutionFactory.create(query, this.model);
            ResultSet results = qexec.execSelect();
            
            while (results.hasNext()) {
                QuerySolution soln = results.nextSolution();
                Resource subject = soln.getResource("subject");
                if (subject != null) {
                    String subjectUri = subject.getURI();
                    matchingNodes.add(subjectUri);
                    logger.debug("Found loose match: " + subjectUri);
                }
            }
            
            logger.info("Loose matching found " + matchingNodes.size() + " nodes for term: " + searchTerm);
            
        } catch (Exception e) {
            logger.error("Error in loose matching for term: " + searchTerm, e);
        } finally {
            if (qexec != null) {
                qexec.close();
            }
        }
        
        return matchingNodes;
    }

    private void queryDependencies(
            TraversedNode tLib, HashMap<String, TraversedNode> tLibs, int loopDepth) {
        QueryExecution qexec = null;
        try {
            tLib.setVisited(true);
            String originalUri = tLib.getUri();
            logger.debug("queryDependencies - original URI: " + originalUri);
            
            // First, fetch and set all properties of the node itself
            RichDependency selfProperties = fetchRichDependencyProperties(originalUri);
            tLib.setSelfProperties(selfProperties.getProperties());

            String sparql = sparqlGenericEdgesQuery(originalUri);
            logger.debug("Generic edges SPARQL: " + sparql);

            // Validate the SPARQL query before creating it
            Query query = null;
            try {
                query = QueryFactory.create(sparql);
            } catch (Exception e) {
                logger.error("Failed to create SPARQL query for URI: " + originalUri + ". SPARQL: " + sparql, e);
                unsuccessfulQueries++;
                return;
            }
            
            qexec = QueryExecutionFactory.create(query, AppGraph.getSingleton().getModel());
            ResultSet results = qexec.execSelect();

            ArrayList<String> allConnections = new ArrayList<String>();
            ArrayList<RichDependency> richDependencies = new ArrayList<RichDependency>();
            
            while (results.hasNext()) {
                QuerySolution solution = results.nextSolution();

                // Get the edge property
                Resource edgeProperty = solution.getResource("edgeProperty");
                String edgePropertyUri = edgeProperty != null ? edgeProperty.getURI() : null;
                String edgeLabel = extractLocalName(edgePropertyUri);

                // Get the target node
                Resource targetNode = solution.getResource("targetNode");
                if (targetNode != null) {
                    String targetUri = targetNode.getURI();
                    allConnections.add(targetUri);

                    // Create rich dependency with all properties of the target
                    RichDependency richDep = fetchRichDependencyProperties(targetUri);
                    richDep.addProperty("EdgeProperty", edgePropertyUri);
                    richDep.addProperty("EdgeLabel", edgeLabel);
                    
                    // Get the direction
                    String direction = solution.getLiteral("direction") != null ?
                        solution.getLiteral("direction").getString() : "outbound";
                    richDep.addProperty("Direction", direction);

                    // Add directional arrow to edge label
                    if ("inbound".equals(direction)) {
                        richDep.addProperty("EdgeLabel", "← " + edgeLabel);
                    } else {
                        richDep.addProperty("EdgeLabel", edgeLabel + " →");
                    }
                    
                    richDependencies.add(richDep);

                    // Add the discovered node to the traversal map if not already present
                    if (!tLibs.containsKey(targetUri)) {
                        tLibs.put(targetUri, new TraversedNode(targetUri, loopDepth));
                        logger.info("Added new node: " + targetUri + " with depth " + loopDepth);
                    }
                }
            }
            
            logger.info("Found " + allConnections.size() + " edges for URI: " + originalUri);

            // Set both rich and legacy dependencies
            tLib.setDependencies(allConnections);
            tLib.setRichDependencies(richDependencies);

            successfulQueries++;
            lastSuccessfulQueryTime = System.currentTimeMillis();
        } catch (Throwable t) {
            unsuccessfulQueries++;
            logger.error("Error in queryDependencies for URI: " + tLib.getUri(), t);
            t.printStackTrace();
        } finally {
            if (qexec != null) {
                try {
                    qexec.close();
                } catch (Exception e) {
                    logger.warn("Error closing query execution", e);
                }
            }
        }
    }

    /**
     * Generates a SPARQL query to find ALL edges (object properties) connected to a given URI.
     * This is completely generic and works with any RDF ontology structure.
     */
    private String sparqlGenericEdgesQuery(String nodeUri) {
        try {
            StringBuilder sb = new StringBuilder();
            sb.append("PREFIX owl: <http://www.w3.org/2002/07/owl#>\n");
            sb.append("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n");
            sb.append("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n");
            
            String formattedNodeUri = formatUri(nodeUri);
            logger.debug("sparqlGenericEdgesQuery - formatted URI: " + formattedNodeUri);

            if (formattedNodeUri == null || formattedNodeUri.equals("<>") || !formattedNodeUri.startsWith("<") || !formattedNodeUri.endsWith(">")) {
                logger.error("Invalid formatted URI: " + formattedNodeUri + " from original: " + nodeUri);
                return createFallbackGenericEdgesQuery(nodeUri);
            }
            
            // Query for all object property relationships (edges)
            sb.append("SELECT DISTINCT ?edgeProperty ?targetNode ?direction\n");
            sb.append("WHERE {\n");
            sb.append("  {\n");
            sb.append("    # Outbound edges: this node -> other nodes\n");
            sb.append("    ").append(formattedNodeUri).append(" ?edgeProperty ?targetNode .\n");
            sb.append("    BIND(\"outbound\" AS ?direction)\n");
            sb.append("    # Filter to only URI resources (nodes, not literals)\n");
            sb.append("    FILTER(isURI(?targetNode))\n");
            sb.append("    # Optionally filter out system properties if needed\n");
            sb.append("    FILTER(!STRSTARTS(STR(?edgeProperty), \"http://www.w3.org/1999/02/22-rdf-syntax-ns#type\"))\n");
            sb.append("    FILTER(!STRSTARTS(STR(?edgeProperty), \"http://www.w3.org/2000/01/rdf-schema#subClassOf\"))\n");
            sb.append("  }\n");
            sb.append("  UNION\n");
            sb.append("  {\n");
            sb.append("    # Inbound edges: other nodes -> this node\n");
            sb.append("    ?targetNode ?edgeProperty ").append(formattedNodeUri).append(" .\n");
            sb.append("    BIND(\"inbound\" AS ?direction)\n");
            sb.append("    FILTER(isURI(?targetNode))\n");
            sb.append("    # Optionally filter out system properties if needed\n");
            sb.append("    FILTER(!STRSTARTS(STR(?edgeProperty), \"http://www.w3.org/1999/02/22-rdf-syntax-ns#type\"))\n");
            sb.append("    FILTER(!STRSTARTS(STR(?edgeProperty), \"http://www.w3.org/2000/01/rdf-schema#subClassOf\"))\n");
            sb.append("  }\n");
            sb.append("}\n");
            sb.append("LIMIT 100");
            
            String query = sb.toString();
            logger.debug("Generated generic edges SPARQL query:\n" + query);

            return query;
        } catch (Exception e) {
            logger.error("Error generating generic edges SPARQL query for URI: " + nodeUri, e);
            return createFallbackGenericEdgesQuery(nodeUri);
        }
    }
    
    /**
     * Creates a fallback query for generic edges when the main query generation fails.
     */
    private String createFallbackGenericEdgesQuery(String nodeUri) {
        String formattedUri = formatUri(nodeUri);
        if (formattedUri == null || formattedUri.equals("<>")) {
            formattedUri = "<http://example.org/unknown>";
        }
        
        return "SELECT DISTINCT ?edgeProperty ?targetNode ?direction\n" +
               "WHERE {\n" +
               "  {\n" +
               "    " + formattedUri + " ?edgeProperty ?targetNode .\n" +
               "    BIND(\"outbound\" AS ?direction)\n" +
               "    FILTER(isURI(?targetNode))\n" +
               "  }\n" +
               "  UNION\n" +
               "  {\n" +
               "    ?targetNode ?edgeProperty " + formattedUri + " .\n" +
               "    BIND(\"inbound\" AS ?direction)\n" +
               "    FILTER(isURI(?targetNode))\n" +
               "  }\n" +
               "}\n" +
               "LIMIT 50";
    }

    private String sparqlDependenciesQuery(String libUri) {
        try {
            StringBuilder sb = new StringBuilder();
            sb.append("PREFIX c: <").append(namespaceWithSeparator()).append(">\n");
            sb.append("PREFIX owl: <http://www.w3.org/2002/07/owl#>\n");
            sb.append("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n");
            sb.append("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n");
            
            // Get edge properties from ontology
            ArrayList<String> edgeProperties = getEdgePropertiesFromOntology();
            
            if (edgeProperties.isEmpty()) {
                logger.warn("No edge properties found, using default fallback query");
                return createFallbackQuery(libUri);
            }
            
            // Build SELECT clause with all edge properties as variables
            sb.append("SELECT");
            for (String edgeProperty : edgeProperties) {
                String sanitizedVar = sanitizeVariableName(edgeProperty);
                if (sanitizedVar != null && !sanitizedVar.isEmpty()) {
                    sb.append(" ?").append(sanitizedVar);
                }
            }
            sb.append("\n");
            
            sb.append("WHERE {\n");
            
            // Ensure libUri is properly formatted as a full URI
            String formattedLibUri = formatUri(libUri);
            logger.debug("sparqlDependenciesQuery - original URI: " + libUri + " -> formatted: " + formattedLibUri);
            
            // Validate the formatted URI
            if (formattedLibUri == null || formattedLibUri.equals("<>") || !formattedLibUri.startsWith("<") || !formattedLibUri.endsWith(">")) {
                logger.error("Invalid formatted URI: " + formattedLibUri + " from original: " + libUri);
                return createFallbackQuery(libUri);
            }
            
            // Build OPTIONAL patterns for each edge property
            for (String edgeProperty : edgeProperties) {
                String sanitizedVar = sanitizeVariableName(edgeProperty);
                if (sanitizedVar != null && !sanitizedVar.isEmpty()) {
                    sb.append("  OPTIONAL { ").append(formattedLibUri).append(" c:").append(edgeProperty).append(" ?").append(sanitizedVar).append(" . }\n");
                }
            }
            
            sb.append("}\n");
            sb.append("LIMIT 40");
            
            String query = sb.toString();
            logger.debug("Generated SPARQL query:\n" + query);
            
            // Basic validation of the generated query
            if (!query.contains("SELECT") || !query.contains("WHERE")) {
                logger.error("Generated invalid SPARQL query structure: " + query);
                return createFallbackQuery(libUri);
            }
            
            return query;
        } catch (Exception e) {
            logger.error("Error generating SPARQL query for URI: " + libUri, e);
            return createFallbackQuery(libUri);
        }
    }
    
    /**
     * Creates a simple fallback SPARQL query when the main query generation fails.
     */
    private String createFallbackQuery(String libUri) {
        String formattedUri = formatUri(libUri);
        if (formattedUri == null || formattedUri.equals("<>")) {
            formattedUri = "<" + namespaceWithSeparator() + "unknown>";
        }
        
        return "PREFIX c: <" + namespaceWithSeparator() + ">\n" +
               "SELECT ?used_library\n" +
               "WHERE {\n" +
               "  OPTIONAL { " + formattedUri + " c:used_library ?used_library . }\n" +
               "}\n" +
               "LIMIT 40";
    }
    
    /**
     * Formats a URI string to be valid in SPARQL queries.
     * If the URI is already a full URI (starts with http:// or https://), wraps it in angle brackets.
     * If it's a bare identifier, constructs a full URI using the namespace and wraps in angle brackets.
     */
    private String formatUri(String uri) {
        if (uri == null || uri.isEmpty()) {
            return "<" + namespaceWithSeparator() + "unknown>";
        }
        
        // If it starts with angle brackets, it's already formatted - but validate it
        if (uri.startsWith("<") && uri.endsWith(">")) {
            String innerUri = uri.substring(1, uri.length() - 1);
            if (isValidURI(innerUri)) {
                return uri;
            } else {
                // Remove angle brackets and re-process
                uri = innerUri;
            }
        }
        
        // If it's already a full URI, validate and wrap in angle brackets
        if (uri.startsWith("http://") || uri.startsWith("https://")) {
            if (isValidURI(uri)) {
                return "<" + uri + ">";
            } else {
                logger.warn("Invalid URI detected, escaping: " + uri);
                return "<" + escapeUri(uri) + ">";
            }
        }
        
        // Check if it already contains the namespace (from bomQuery concatenation)
        String namespace = namespaceWithSeparator();
        if (uri.startsWith(namespace)) {
            if (isValidURI(uri)) {
                return "<" + uri + ">";
            } else {
                logger.warn("Invalid URI with namespace detected, escaping: " + uri);
                return "<" + escapeUri(uri) + ">";
            }
        }
        
        // If it's a bare identifier, construct full URI with namespace
        String fullUri = namespace + escapeUriComponent(uri);
        return "<" + fullUri + ">";
    }
    
    /**
     * Checks if a URI string is valid for SPARQL.
     */
    private boolean isValidURI(String uri) {
        if (uri == null || uri.isEmpty()) {
            return false;
        }
        
        // Check for invalid characters that would break SPARQL parsing
        // These characters need to be escaped or the URI is invalid
        String invalidChars = "<>\"{}|^`\\";
        for (char c : invalidChars.toCharArray()) {
            if (uri.indexOf(c) != -1) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Escapes a full URI for safe use in SPARQL.
     */
    private String escapeUri(String uri) {
        if (uri == null) {
            return "";
        }
        
        return uri.replace("<", "%3C")
                  .replace(">", "%3E")
                  .replace("\"", "%22")
                  .replace("{", "%7B")
                  .replace("}", "%7D")
                  .replace("|", "%7C")
                  .replace("^", "%5E")
                  .replace("`", "%60")
                  .replace("\\", "%5C");
    }
    
    /**
     * Escapes a URI component (the part after the namespace) for safe use in SPARQL.
     */
    private String escapeUriComponent(String component) {
        if (component == null) {
            return "";
        }
        
        // More aggressive escaping for URI components
        return component.replace(" ", "%20")
                       .replace("<", "%3C")
                       .replace(">", "%3E")
                       .replace("\"", "%22")
                       .replace("{", "%7B")
                       .replace("}", "%7D")
                       .replace("|", "%7C")
                       .replace("^", "%5E")
                       .replace("`", "%60")
                       .replace("\\", "%5C");
    }
    
    /**
     * Sanitizes a property name to be a valid SPARQL variable name.
     * SPARQL variables must start with a letter and contain only letters, digits, and underscores.
     */
    private String sanitizeVariableName(String propertyName) {
        if (propertyName == null || propertyName.isEmpty()) {
            return "property";
        }
        
        // Replace invalid characters with underscores
        String sanitized = propertyName.replaceAll("[^a-zA-Z0-9_]", "_");
        
        // Ensure it starts with a letter
        if (!Character.isLetter(sanitized.charAt(0))) {
            sanitized = "var_" + sanitized;
        }
        
        return sanitized;
    }
    /**
     * Process an INSERT DATA request that looks like this:
     * {"sparql":"PREFIX c: <http://cosmosdb.com/caig#> INSERT DATA { <http://cosmosdb.com/caig/pypi_m27> <http://cosmosdb.com/caig#lt> \"pypi\" . }"}
     * <p>
     * See ConsoleApp#postSparqlAddDocuments for example code to invoke this endpoint.
     */
    public synchronized SparqlQueryResponse update(SparqlQueryRequest request) {
        logger.warn("update: " + request.getSparql());
        SparqlQueryResponse response = new SparqlQueryResponse(request);
        UpdateExecution uexec = null;
        try {
            UpdateRequest updateRequest = UpdateFactory.create();
            updateRequest.add(request.getSparql());  // multiple statements may be added
            Dataset ds = DatasetFactory.create(this.model);
            uexec = UpdateExecutionFactory.create(updateRequest, ds);
            uexec.execute();
            ds.commit();
            this.successfulUpdates++;
            this.lastSuccessfulUpdateTime = System.currentTimeMillis();
            logger.warn("successful update: " + this.successfulUpdates + " at: " + this.lastSuccessfulUpdateTime);
        } catch (Exception e) {
            this.unsuccessfulUpdates++;
            logger.error("update - Exception on sparql: " + request.getSparql());
            logger.error(e.getMessage());
            response.setError(e.getMessage());
        }
        response.finish();
        return response;
    }

    /**
     * This method can be invoked after the initial graph load in class AppGraphBuilder.
     * The given Array of objects must be in the same structure as the Cosmos DB source
     * documents as the same LibrariesGraphTriplesBuilder class is used to load these docs.
     * Typical use of this method is from the Cosmos DB Change Feed.
     */
    public synchronized AddDocumentsResponse addDocuments(ArrayList<Map<String, Object>> documents) {
        LibrariesGraphTriplesBuilder triplesBuilder = new LibrariesGraphTriplesBuilder(this);
        AddDocumentsResponse response = new AddDocumentsResponse();

        if (documents != null) {
            response.setInputDocumentsCount(documents.size());
            for (int i = 0; i < documents.size(); i++) {
                if (response.getFailuresCount() == 0) {
                    try {
                        response.incrementProcessedDocumentsCount();
                        Map<String, Object> doc = documents.get(i);
                        triplesBuilder.ingestDocument(doc);
                    } catch (Exception e) {
                        response.incrementFailuresCount();
                        response.setErrorMessage(e.getMessage());
                        e.printStackTrace();
                    }
                }
            }
        } else {
            response.setInputDocumentsCount(-1);
            response.setErrorMessage("null documents list provided to addDocuments");
        }
        response.finish();
        return response;
    }

    public long getDocsRead() {
        return this.docsRead;
    }

    public void setDocsRead(long count) {
        this.docsRead = count;
    }

    public long getSuccessfulQueries() {
        return successfulQueries;
    }

    public void setSuccessfulQueries(long successfulQueries) {
        this.successfulQueries = successfulQueries;
    }

    public long getUnsuccessfulQueries() {
        return unsuccessfulQueries;
    }

    public void setUnsuccessfulQueries(long unsuccessfulQueries) {
        this.unsuccessfulQueries = unsuccessfulQueries;
    }

    public long getLastSuccessfulQueryTime() {
        return lastSuccessfulQueryTime;
    }

    public void setLastSuccessfulQueryTime(long lastSuccessfulQueryTime) {
        this.lastSuccessfulQueryTime = lastSuccessfulQueryTime;
    }

    public long getSuccessfulUpdates() {
        return successfulUpdates;
    }

    public void setSuccessfulUpdates(long successfulUpdates) {
        this.successfulUpdates = successfulUpdates;
    }

    public long getUnsuccessfulUpdates() {
        return unsuccessfulUpdates;
    }

    public void setUnsuccessfulUpdates(long unsuccessfulUpdates) {
        this.unsuccessfulUpdates = unsuccessfulUpdates;
    }

    public long getLastSuccessfulUpdateTime() {
        return lastSuccessfulUpdateTime;
    }

    public void setLastSuccessfulUpdateTime(long lastSuccessfulUpdateTime) {
        this.lastSuccessfulUpdateTime = lastSuccessfulUpdateTime;
    }

    public Model getModel() {
        return this.model;
    }

    public void setModel(Model model) {
        this.model = model;
    }

    /**
     * Write the state of the model/graph to an RDF file with the given filename,
     * in one of several formats, defaulting to Lang.TTL (i.e. - TURTLE).
     * See https://jena.apache.org/documentation/io/rdf-output.html
     */
    public void writeModelToFile(String filename, Lang lang) {
        try {
            if (lang == null) {
                lang = Lang.TTL;
            }
            logger.warn("writeModelToFile: " + filename + ", lang: " + lang);
            FileOutputStream fos = new FileOutputStream(filename);
            RDFWriter.source(this.model)
                    .set(RIOT.symTurtleDirectiveStyle, "sparql")
                    .lang(lang)
                    .output(fos);
        } catch (Throwable t) {
            t.printStackTrace();
        } finally {
            logger.warn("writeModelToFile completed");
        }
    }

    /**
     * Read the graph from an RDF file with the given filename,
     * in one of several formats, defaulting to Lang.TTL (i.e. - TURTLE).
     * See https://jena.apache.org/documentation/io/rdf-output.html
     */
    public Model readGraphFromFile(String filename, Lang lang) {
        try {
            if (lang == null) {
                lang = Lang.TTL;
            }
            logger.warn("readGraphFromFile: " + filename + ", lang: " + lang);

            // Create an empty model
            Model model = ModelFactory.createDefaultModel();

            // Read the RDF data from a TTL file
            RDFDataMgr.read(model, filename, lang);

            this.model = model;
        } catch (Throwable t) {
            t.printStackTrace();
        } finally {
            logger.warn("readGraphFromFile completed");
        }
        return model;
    }

    private String nodeType(RDFNode node) {
        if (node == null) {
            return "null";
        } else if (node.isAnon()) {
            return "anon";
        } else if (node.isLiteral()) {
            return "literal";
        } else if (node.isResource()) {
            return "resource";
        } else if (node.isStatementTerm()) {
            return "statement_term";
        } else if (node.isURIResource()) {
            return "uri_resource";
        }
        return "?";
    }

    private String classname(Object obj) {
        if (obj == null) {
            return null;
        }
        return obj.getClass().getName();
    }
    
    /**
     * Fetch all TTL properties for a given dependency URI to create a RichDependency object.
     * This method dynamically queries the TTL graph to retrieve all available properties
     * for any ontology structure, making it domain-agnostic.
     */
    private RichDependency fetchRichDependencyProperties(String depUri) {
        RichDependency richDep = new RichDependency(depUri);
        QueryExecution qexec = null;
        
        try {
            // Build a SPARQL query to fetch all properties for this dependency URI
            StringBuilder sb = new StringBuilder();
            sb.append("PREFIX c: <").append(namespaceWithSeparator()).append(">\n");
            sb.append("PREFIX owl: <http://www.w3.org/2002/07/owl#>\n");
            sb.append("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n");
            sb.append("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n");
            sb.append("SELECT ?property ?value WHERE {\n");
            
            // Format the URI properly
            String formattedUri = formatUri(depUri);
            sb.append("  ").append(formattedUri).append(" ?property ?value .\n");
            
            // Filter out RDF type statements to focus on data properties
            sb.append("  FILTER(?property != rdf:type)\n");
            sb.append("}\n");
            sb.append("LIMIT 50");
            
            String sparql = sb.toString();
            logger.debug("Rich dependency query for " + depUri + ":\n" + sparql);
            
            Query query = QueryFactory.create(sparql);
            qexec = QueryExecutionFactory.create(query, this.model);
            ResultSet results = qexec.execSelect();
            
            while (results.hasNext()) {
                QuerySolution solution = results.nextSolution();
                RDFNode propertyNode = solution.get("property");
                RDFNode valueNode = solution.get("value");
                
                if (propertyNode != null && valueNode != null) {
                    String propertyUri = propertyNode.toString();
                    String propertyName = extractLocalName(propertyUri);
                    
                    // Extract the value based on its type
                    Object value;
                    if (valueNode.isLiteral()) {
                        // Handle literal values (strings, numbers, etc.)
                        String literalValue = valueNode.asLiteral().getString();
                        
                        // Try to parse as number if it looks like a number
                        if (literalValue.matches("\\d+\\.\\d+")) {
                            try {
                                value = Double.parseDouble(literalValue);
                            } catch (NumberFormatException e) {
                                value = literalValue;
                            }
                        } else if (literalValue.matches("\\d+")) {
                            try {
                                value = Integer.parseInt(literalValue);
                            } catch (NumberFormatException e) {
                                value = literalValue;
                            }
                        } else {
                            value = literalValue;
                        }
                    } else if (valueNode.isURIResource()) {
                        // Handle URI references - extract the local name
                        String uriValue = valueNode.asResource().getURI();
                        value = extractLocalName(uriValue);
                    } else {
                        value = valueNode.toString();
                    }
                    
                    // Add the property to the rich dependency
                    if (propertyName != null && !propertyName.isEmpty()) {
                        richDep.addProperty(propertyName, value);
                        logger.debug("Added property " + propertyName + " = " + value + " to " + depUri);
                    }
                }
            }
            
            // Set the type from properties if available (try common type property names)
            String[] typePropertyNames = {"type", "Type", "class", "Class", "category", "Category"};
            for (String typeProp : typePropertyNames) {
                String type = richDep.getStringProperty(typeProp);
                if (type != null) {
                    richDep.setType(type);
                    break;
                }
            }
            
            logger.debug("Created rich dependency for " + depUri + " with " + 
                        richDep.getProperties().size() + " properties");
            
        } catch (Exception e) {
            logger.error("Error fetching rich properties for dependency: " + depUri, e);
            // Return a basic RichDependency even if query fails
        } finally {
            if (qexec != null) {
                try {
                    qexec.close();
                } catch (Exception e) {
                    logger.warn("Error closing rich dependency query execution", e);
                }
            }
        }
        
        return richDep;
    }
    
    /**
     * Extracts the local name from a URI (the part after the last # or /).
     * This is useful for creating human-readable labels from URIs.
     */
    private String extractLocalName(String uri) {
        if (uri == null || uri.isEmpty()) {
            return "";
        }

        // Remove angle brackets if present
        if (uri.startsWith("<") && uri.endsWith(">")) {
            uri = uri.substring(1, uri.length() - 1);
        }

        // Try to find the last '#' first, then the last '/'
        int hashIdx = uri.lastIndexOf('#');
        int slashIdx = uri.lastIndexOf('/');

        // Use whichever delimiter appears last
        int idx = Math.max(hashIdx, slashIdx);

        if (idx >= 0 && uri.length() > idx + 1) {
            return uri.substring(idx + 1);
        } else {
            // Fallback to the full URI if no delimiter found
            return uri;
        }
    }

    /**
     * Get edge properties (ObjectProperties) from the ontology.
     * This method dynamically discovers object properties from the loaded RDF model.
     */
    private ArrayList<String> getEdgePropertiesFromOntology() {
        ArrayList<String> edgeProperties = new ArrayList<>();
        QueryExecution qexec = null;

        try {
            // Query to find all object properties in the ontology
            String sparql = "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n" +
                           "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n" +
                           "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n" +
                           "SELECT DISTINCT ?property WHERE {\n" +
                           "  { ?property a owl:ObjectProperty }\n" +
                           "  UNION\n" +
                           "  { ?s ?property ?o . FILTER(isURI(?o)) }\n" +
                           "} LIMIT 100";

            Query query = QueryFactory.create(sparql);
            qexec = QueryExecutionFactory.create(query, this.model);
            ResultSet results = qexec.execSelect();

            while (results.hasNext()) {
                QuerySolution solution = results.nextSolution();
                Resource property = solution.getResource("property");
                if (property != null) {
                    String propertyUri = property.getURI();
                    String localName = extractLocalName(propertyUri);
                    if (localName != null && !localName.isEmpty()) {
                        edgeProperties.add(localName);
                    }
                }
            }

            logger.info("Found " + edgeProperties.size() + " edge properties from ontology");

        } catch (Exception e) {
            logger.error("Error getting edge properties from ontology", e);
            // Return some default properties as fallback
            edgeProperties.add("uses");
            edgeProperties.add("used_by");
            edgeProperties.add("depends_on");
            edgeProperties.add("dependency_of");
        } finally {
            if (qexec != null) {
                qexec.close();
            }
        }

        return edgeProperties;
    }

    private String findConnectingProperty(String sourceUri, String targetUri,
                                        ArrayList<String> edgeProperties, 
                                        DependenciesQueryResult dqr) {
        try {
            for (String edgeProperty : edgeProperties) {
                String sanitizedVar = sanitizeVariableName(edgeProperty);
                ArrayList<String> propertyValues = dqr.getSingleNamedValues(sanitizedVar);
                
                if (propertyValues != null && propertyValues.contains(targetUri)) {
                    logger.debug("Found connecting property: " + edgeProperty + " links " + sourceUri + " -> " + targetUri);
                    return edgeProperty;
                }
            }
        } catch (Exception e) {
            logger.warn("Error finding connecting property for " + sourceUri + " -> " + targetUri, e);
        }
        
        return null;
    }

}

