package com.microsoft.cosmosdb.caig.graph;


import com.microsoft.cosmosdb.caig.models.SparqlQueryRequest;
import com.microsoft.cosmosdb.caig.models.SparqlQueryResponse;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFWriter;
import org.apache.jena.riot.RIOT;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.ByteArrayOutputStream;
import java.io.FileOutputStream;

/**
 * Instances of this class represent the in-memory Application Graph object.
 * The name "AppGraph" was chosen so as not to collide with a similarly named class in the
 * Apache Jena codebase.
 *
 * Chris Joakim, Microsoft, 2025
 */
public class AppGraph {

    // Class variables
    private static Logger logger = LogManager.getLogger(AppGraph.class);
    private static AppGraph singleton = null;  // created by GraphBuilder at ApplicationStartup

    // Instance variables
    private long docsRead = 0;
    private Model model;
    private long successfulQueries;
    private long unsuccessfulQueries;
    private long lastSuccessfulQueryTime;

    public AppGraph() {

        super();
        successfulQueries = 0;
        unsuccessfulQueries = 0;
        lastSuccessfulQueryTime = 0;
    }

    public static AppGraph getSingleton() {
        logger.warn("AppGraph#getSingleton - model impl class: " + singleton.getModel().getClass().getName());
        return singleton;
    }

    public static void setSingleton(AppGraph g) {
        logger.warn("AppGraph#setSingleton - model impl class: " + g.getModel().getClass().getName());
        singleton = g;
    }

    /**
     * Query the in-memory graph using the SPARQL in the given SparqlQueryRequest object.
     * The "synchronized" keyword is used here to allow only one thread to execute at any given time.
     * Each HTTP request runs in its own Thread.
     */
    public synchronized SparqlQueryResponse query(SparqlQueryRequest request) {
        logger.warn("AppGraph#query: " + request.getSparql());
        SparqlQueryResponse response = new SparqlQueryResponse(request);
        QueryExecution qexec = null;
        try {
            Query query = QueryFactory.create(response.getSparql());
            qexec = QueryExecutionFactory.create(
                    query, AppGraph.getSingleton().getModel());
            ResultSet results = qexec.execSelect();
            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            ResultSetFormatter.outputAsJSON(outputStream, results);
            String json = new String(outputStream.toByteArray());
            response.setResults(json);
            successfulQueries++;
            lastSuccessfulQueryTime = System.currentTimeMillis();
        }
        catch (Exception e) {
            unsuccessfulQueries++;
            logger.error("AppGraph#query - Exception on sparql: " + request.getSparql());
            logger.error(e.getMessage());
        }
        finally {
            if (qexec != null) {
                qexec.close();
            }
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

    /**
     * State info used by HealthRestController.
     */
    public long getSuccessfulQueriesCount() {
        return this.successfulQueries;
    }

    /**
     * State info used by HealthRestController.
     */
    public long getUnsuccessfulQueriesCount() {
        return this.unsuccessfulQueries;
    }

    /**
     * State info used by HealthRestController.
     */
    public long getLastSuccessfulQueryTime() {
        return this.lastSuccessfulQueryTime;
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
            logger.warn("AppGraph#writeModelToFile completed");
        }
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