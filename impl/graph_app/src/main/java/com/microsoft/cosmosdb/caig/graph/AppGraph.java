package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.models.*;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFWriter;
import org.apache.jena.riot.RIOT;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.Lang;
import org.apache.jena.rdf.model.ModelFactory;
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
import java.util.List;
import java.util.Map;

/**
 * Instances of this class represent the in-memory Application Graph object.
 * The name "AppGraph" was chosen so as not to collide with a similarly named class in the
 * Apache Jena codebase.
 *
 * Chris Joakim, Microsoft, 2025
 */
public class AppGraph {

    // Class variables
    private static Logger logger = LoggerFactory.getLogger(AppGraph.class);
    private static AppGraph singleton = null;  // created by GraphBuilder at ApplicationStartup

    // Instance variables
    private long docsRead = 0;
    private Model model;
    private String namespace;
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
            String json = new String(outputStream.toByteArray()).replaceAll("\\n","");
            //System.out.println("query - json: " + json);
            ObjectMapper objectMapper = new ObjectMapper();
            Map<String, Object> map
                    = objectMapper.readValue(json, new TypeReference<Map<String,Object>>(){});
            response.setResults(map);
            successfulQueries++;
            lastSuccessfulQueryTime = System.currentTimeMillis();
        }
        catch (Exception e) {
            unsuccessfulQueries++;
            logger.error("query - Exception on sparql: " + request.getSparql());
            logger.error(e.getMessage());
            response.setError(e.getMessage());
        }
        finally {
            if (qexec != null) {
                qexec.close();
            }
        }
        response.finish();
        return response;
    }


    public synchronized SparqlBomQueryResponse bomQuery(SparqlBomQueryRequest request) {
        logger.warn("bomQuery - libname: " + request.getLibname());
        SparqlBomQueryResponse response = new SparqlBomQueryResponse(request);
        HashMap<String, TraversedLib> tLibs = new HashMap<String, TraversedLib>();
        response.setLibs(tLibs);
        QueryExecution qexec = null;
        try {
            boolean continueToProcess = true;
            int maxDepth = request.getMax_depth();
            int loopDepth = 0;
            int loopStartLibCount = 0;
            int loopFinishLibCount = 0;
            String libUri = "http://cosmosdb.com/caig#" + response.getLibname();
            tLibs.put(libUri, new TraversedLib(libUri, 0));

            while (continueToProcess) {
                loopDepth++;
                loopStartLibCount = tLibs.size();
                response.setActualDepth(loopDepth);

                if (loopDepth > maxDepth) {
                    continueToProcess = false;
                }
                else {
                    Object[] tlibUris = tLibs.keySet().toArray();
                    logger.warn("loop: " + loopDepth + " count " + tlibUris.length);
                    for (int i = 0; i < tlibUris.length; i++) {
                        String tlibUri = (String) tlibUris[i];
                        logger.debug("tlibUri: " + tlibUri + " idx " + i);
                        TraversedLib tLib = tLibs.get(tlibUri);
                        if (tLib.isVisited()) {
                            logger.debug("tlibUri already visited: " + tlibUri);
                        }
                        else {
                            queryLibDependencies(tLib, tLibs, loopDepth);
                        }
                    }
                    // Terminate the graph traversal
                    loopFinishLibCount = tLibs.size();
                    if (loopFinishLibCount == loopStartLibCount) {
                        continueToProcess = false;
                    }
                }
            }
        }
        catch (Exception e) {
            unsuccessfulQueries++;
            logger.error(e.getMessage());
            response.setError(e.getMessage());
        }
        finally {
            if (qexec != null) {
                qexec.close();
            }
        }
        response.finish();
        return response;
    }

    private void queryLibDependencies(
            TraversedLib tLib, HashMap<String, TraversedLib> tLibs, int loopDepth) {
        try {
            tLib.setVisited(true);
            String sparql = sparqlDependenciesQuery(tLib.getUri());
            logger.debug("bom sparql: " + sparql);
            Query query = QueryFactory.create(sparql);
            QueryExecution qexec = QueryExecutionFactory.create(
                    query, AppGraph.getSingleton().getModel());
            ResultSet results = qexec.execSelect();
            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            ResultSetFormatter.outputAsJSON(outputStream, results);
            String json = new String(outputStream.toByteArray()).replaceAll("\\n","");
            ObjectMapper objectMapper = new ObjectMapper();

            DependenciesQueryResult dqr = objectMapper.readValue(json, DependenciesQueryResult.class);
            tLib.setDependencies(dqr.getSingleNamedValues("used_library"));

            ArrayList<String> dependencies = dqr.getSingleNamedValues("used_library");
            for (int d = 0; d < dependencies.size(); d++) {
                String depUri = dependencies.get(d);
                if (!tLibs.containsKey(depUri)) {
                    tLibs.put(depUri, new TraversedLib(depUri, loopDepth));
                }
            }
            successfulQueries++;
            lastSuccessfulQueryTime = System.currentTimeMillis();
        }
        catch (Throwable t) {
            unsuccessfulQueries++;
            t.printStackTrace();
        }
    }

    private String sparqlDependenciesQuery(String libUri) {
        StringBuilder sb = new StringBuilder();
        sb.append("PREFIX c: <http://cosmosdb.com/caig#>");
        sb.append(" SELECT ?used_library");
        sb.append(" WHERE { ");
        sb.append(" <" + libUri + "> c:uses_library ?used_library .");
        sb.append(" } LIMIT 40");
        return sb.toString();
    }

    /**
     * Process an INSERT DATA request that looks like this:
     * {"sparql":"PREFIX c: <http://cosmosdb.com/caig#> INSERT DATA { <http://cosmosdb.com/caig/pypi_m27> <http://cosmosdb.com/caig#lt> \"pypi\" . }"}
     *
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
        }
        catch (Exception e) {
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
                    }
                    catch (Exception e) {
                        response.incrementFailuresCount();
                        response.setErrorMessage(e.getMessage());
                        e.printStackTrace();
                    }
                }
            }
        }
        else {
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
        }
        catch (Throwable t) {
            t.printStackTrace();
        }
        finally {
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
        }
        catch (Throwable t) {
            t.printStackTrace();
        }
        finally {
            logger.warn("readGraphFromFile completed");
        }
        return model;
    }

    private String nodeType(RDFNode node) {
        if (node == null) {
            return "null";
        }
        else if (node.isAnon()) {
            return "anon";
        }
        else if (node.isLiteral()) {
            return "literal";
        }
        else if (node.isResource()) {
            return "resource";
        }
        else if (node.isStmtResource()) {
            return "stmt_resource";
        }
        else if (node.isURIResource()) {
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

}