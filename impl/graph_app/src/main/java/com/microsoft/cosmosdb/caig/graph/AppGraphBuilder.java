package com.microsoft.cosmosdb.caig.graph;

import com.azure.cosmos.CosmosAsyncClient;
import com.azure.cosmos.CosmosAsyncContainer;
import com.azure.cosmos.CosmosAsyncDatabase;
import com.azure.cosmos.CosmosClientBuilder;
import com.azure.cosmos.models.CosmosQueryRequestOptions;
import com.azure.cosmos.util.CosmosPagedFlux;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.models.SparqlQueryRequest;
import com.microsoft.cosmosdb.caig.models.SparqlQueryResponse;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import com.microsoft.cosmosdb.caig.util.BlobStorageUtil;
import com.microsoft.cosmosdb.caig.util.FileUtil;
import org.apache.jena.ontology.OntModel;
import org.apache.jena.ontology.OntModelSpec;
import org.apache.jena.rdf.model.InfModel;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.reasoner.Reasoner;
import org.apache.jena.reasoner.ReasonerRegistry;
import org.apache.jena.riot.Lang;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import reactor.core.publisher.Flux;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/**
 * Instances of this class are created at application startup to create/build the
 * singleton instance of class AppGraph per given environment variable configuration.
 * The graph can be loaded from one of three sources - cosmos_nosql, rdf_file,
 * or json_docs_file.  The latter two are for dev-environment only.
 *
 * Chris Joakim, Aleksey Savateyev
 */

public class AppGraphBuilder {

    // Constants
    public static final String GRAPH_SOURCE_COSMOSDB_NOSQL = "cosmos_nosql";
    public static final String GRAPH_SOURCE_RDF_FILE       = "rdf_file";
    public static final String GRAPH_SOURCE_JSON_DOCS_FILE = "json_docs_file";  // captured CosmosDB documents

    // Class variables
    private static Logger logger = LoggerFactory.getLogger(AppGraphBuilder.class);

    /**
     * This constructor is intentionally private; use the static build() method instead.
     */
    private AppGraphBuilder() {
        super();
    }

    /**
     * Create and return an instance of AppGraph per the graph source configuration.
     * AppGraph contains an attribute called "model" that is in instance of class
     * org.apache.jena.rdf.model.Model.  This graph exists in the memory of the
     * Java Virtual Machine (JVM), and is not persisted to disk.
     */
    public static AppGraph build(String overridePostLoadquery) {
        logger.warn("build() start, overridePostLoadquery: " + overridePostLoadquery);
        AppGraph appGraph = null;
        Model model = null;

        try {
            appGraph = new AppGraph();
            String source = AppConfig.getGraphSourceType();
            String postLoadQuery = "SELECT (COUNT(?s) AS ?triples) WHERE { ?s ?p ?o }";
            if (overridePostLoadquery != null) {
                postLoadQuery = overridePostLoadquery;
            }
            logger.info("build() - source: " + source);

            switch(source) {
                case GRAPH_SOURCE_JSON_DOCS_FILE:
                    // Same data as GRAPH_SOURCE_COSMOSDB_NOSQL, but with previously captured data in a JSON file
                    model = initializeModel(true);
                    appGraph.setModel(model);
                    populateFromJsonDocsFile(appGraph);
                    break;
                case GRAPH_SOURCE_COSMOSDB_NOSQL:
                    model = initializeModel(true);
                    appGraph.setModel(model);
                    populateFromCosmosDbNoSQL(appGraph);
                    break;
                case GRAPH_SOURCE_RDF_FILE:
                    model = initializeModel(true);
                    appGraph.setModel(model);
                    populateFromRdfFile(appGraph);
                    break;

                default:
                    logger.error("build() - unknown graph source: " + source);
            }
            AppGraph.setSingleton(appGraph);

            // Initial query to check the newly loaded graph.
            if (postLoadQuery != null) {
                SparqlQueryRequest req = new SparqlQueryRequest();
                req.setSparql(postLoadQuery);
                SparqlQueryResponse resp = appGraph.query(req);
                logger.warn("postLoadQuery: "  + postLoadQuery);
                logger.warn("postLoadQuery response: "  + resp);
            }

            // Optionally dump the newly loaded graph
            if (AppConfig.dumpGraphUponBuild()) {
                String outfile = AppConfig.getGraphDumpOutfile();
                if (outfile != null) {
                    appGraph.writeModelToFile(outfile, Lang.TTL);
                    //appGraph.writeModelToFile(outfile, Lang.JSONLD);
                }
            }
        }
        catch (Exception ex) {
            ex.printStackTrace();
        }
        logger.warn("build() finish");
        return appGraph;
    }

    /**
     * Create and return the Jena Model object which represents the graph.
     */
    private static Model initializeModel(boolean readOntology) {

        // See https://jena.apache.org/documentation/ontology/

        boolean useDefaultModelLogic = true;

        if (useDefaultModelLogic) {
            Model model = ModelFactory.createDefaultModel();
            return model;
        }
        else {
            try {
                String owlFile = AppConfig.getGraphOwlFilename();
                FileUtil fileUtil = new FileUtil();
                String ontology = fileUtil.readUnicode(owlFile);
                
                if (ontology == null || ontology.isEmpty()) {
                    logger.error("Failed to load OWL ontology from: " + owlFile);
                    return ModelFactory.createDefaultModel();
                }
                
                InputStream byteStream = new ByteArrayInputStream(ontology.getBytes(StandardCharsets.UTF_8));
                logger.warn("owlFile:  " + owlFile);
                logger.warn("ontology length: " + ontology.length());

                
                OntModel model = ModelFactory.createOntologyModel(OntModelSpec.OWL_MEM);
                model.read(byteStream, "");

                model.setNsPrefix("default", AppConfig.getGraphNamespace());

                // set sample namespaces in case sample datasets are used
                //model.setNsPrefix("caig", "http://cosmosdb.com/caig#");
                //model.setNsPrefix("ns1", AppConfig.getGraphNamespace());
                return model;

                // Reasoner reasoner = ReasonerRegistry.getOWLReasoner().bindSchema(model.getGraph());
                // InfModel infModel = ModelFactory.createInfModel(reasoner, model);
                // return infModel;

                 
/*
                // Load ontology as schema
                Model schema = ModelFactory.createDefaultModel();
                schema.read(byteStream, "", "TTL");

                // Create base data model
                Model dataModel = ModelFactory.createDefaultModel();

                // After loading data into dataModel, wrap with RDFS reasoner:
                InfModel infModel = ModelFactory.createRDFSModel(schema, dataModel);
                return infModel;
*/
            } catch (Throwable t) {
                t.printStackTrace();
            }
        }
        return null;
    }

    /**
     * This method is used for initial development, using a previously captured
     * JSON file containing the same Cosmos DB documents that are read in the
     * following populateFromCosmosDbNoSQL method.
     */
    private static void populateFromJsonDocsFile(AppGraph g) {
        try {
            FileUtil fileUtil = new FileUtil();
            String infile = "data/cosmosdb_documents.json";
            ArrayList<Map<String, Object>>  documents = fileUtil.readJsonMapArray(infile);
            logger.warn("populateFromJsonDocsFile, documents read: " + documents.size());

            LibrariesGraphTriplesBuilder triplesBuilder = new LibrariesGraphTriplesBuilder(g);

            for (int i = 0; i < documents.size(); i++) {
                Map<String, Object> doc = documents.get(i);
                triplesBuilder.ingestDocument(doc);
            }
            logger.warn("documentsIngested: " + triplesBuilder.getDocumentsIngested());
        }
        catch (Exception e) {
            e.printStackTrace();
        }
    }

    /**
     * This is the primary intended graph loading mechanism - graph data
     * sourced from Azure Cosmos DB NoSQL API.
     */
    private static void populateFromCosmosDbNoSQL(AppGraph g) {
        String uri = AppConfig.getCosmosNoSqlUri();
        String key = AppConfig.getCosmosNoSqlKey1();
        String dbname = AppConfig.getGraphSourceDb();
        String cname = AppConfig.getGraphSourceContainer();
        String sql = cosmosdbSourceSqlQuery();
        AtomicLong docCounter = new AtomicLong(0);
        ArrayList<Map> allDocuments = new ArrayList<>();
        LibrariesGraphTriplesBuilder triplesBuilder = new LibrariesGraphTriplesBuilder(g);

        logger.warn("populateFromCosmosDbNoSQL, uri: " + uri);
        logger.warn("populateFromCosmosDbNoSQL, key: " + key);
        logger.warn("populateFromCosmosDbNoSQL, dbname: " + dbname);
        logger.warn("populateFromCosmosDbNoSQL, cname:  " + cname);

        // Use Gateway mode for Java 21 compatibility
        // Direct mode with Java 21 has SSL hostname verification issues with regional endpoint redirects
        // Gateway mode adds ~5-10ms latency but is fully compatible and reliable
        // See: https://github.com/Azure/azure-sdk-for-java/issues/31847
        CosmosAsyncClient cosmosAsyncClient = new CosmosClientBuilder()
                .endpoint(uri)
                .key(key)
                .gatewayMode()
                .buildAsyncClient();

        CosmosAsyncDatabase database = cosmosAsyncClient.getDatabase(dbname);
        logger.warn("populateFromCosmosDbNoSQL, database id: " + database.getId());

        CosmosAsyncContainer container = database.getContainer(cname);
        logger.warn("populateFromCosmosDbNoSQL, container id: " + container.getId());

        CosmosQueryRequestOptions queryOptions = new CosmosQueryRequestOptions();
        CosmosPagedFlux<Map> flux = container.queryItems(sql, queryOptions, Map.class);

        flux.byPage(100).flatMap(fluxResponse -> {
            List<Map> results = fluxResponse.getResults().stream().collect(Collectors.toList());
            for (int r = 0; r < results.size(); r++) {
                Map doc = results.get(r);
                docCounter.incrementAndGet();
                triplesBuilder.ingestDocument(doc);
                // allDocuments.add(doc);
            }
            return Flux.empty();
        }).blockLast();

        g.setDocsRead(docCounter.get());
        logger.warn("populateFromCosmosDbNoSQL, docCount:  " + docCounter.get());

        if (false) {
            // this is ad-hoc development environment logic.
            // captured file data/cosmosdb_documents.json can be used to load the graph
            // in the future rather than reading the documents from Cosmos DB.
            // The file is written to tmp/cosmosdb_documents.json here; then manually
            // copy it to data/cosmosdb_documents.json after visually validating it.
            try {
                FileUtil fileUtil = new FileUtil();
                String outfile = "tmp/cosmosdb_documents.json";
                fileUtil.writeJson(allDocuments, outfile, true, true);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * This method is used for initial development, using a previously captured *.ttl
     * triples file or an HTTPS URL to RDF content (e.g., Azure Blob Storage).
     * Supports both single file URLs and directory URLs for loading multiple files.
     */
    private static void populateFromRdfFile(AppGraph g) throws Exception {
        try {
            String graphPath = AppConfig.getGraphPath();
            logger.warn("populateFromRdfFile - " + graphPath);
            Model ontology = g.getModel();
            Model model = ModelFactory.createDefaultModel();
            
            // Check if graphPath is a URL or a file/directory path
            if (graphPath.startsWith("http://") || graphPath.startsWith("https://")) {
                // Load from URL (single file or directory)
                FileUtil fileUtil = new FileUtil();
                
                // Check if this is a directory URL (ends with / or no extension)
                if (BlobStorageUtil.isBlobDirectoryUrl(graphPath)) {
                    // List all RDF files in the blob directory
                    logger.warn("Loading RDF from blob directory: " + graphPath);
                    List<String> blobUrls = BlobStorageUtil.listBlobsInDirectory(graphPath);
                    
                    if (blobUrls.isEmpty()) {
                        logger.error("No RDF files found in blob directory: " + graphPath);
                    } else {
                        for (String blobUrl : blobUrls) {
                            logger.warn("Loading RDF from blob: " + blobUrl);
                            String rdfContent = fileUtil.readUnicode(blobUrl);
                            if (rdfContent != null && !rdfContent.isEmpty()) {
                                String lowerUrl = blobUrl.toLowerCase();
                                Lang lang = Lang.TTL;
                                if (lowerUrl.endsWith(".nt")) lang = Lang.NT;
                                else if (lowerUrl.endsWith(".rdf")) lang = Lang.RDFXML;
                                else if (lowerUrl.endsWith(".owl")) lang = Lang.RDFXML;
                                
                                java.io.InputStream is = new java.io.ByteArrayInputStream(
                                    rdfContent.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                                model.read(is, null, lang.getName());
                                logger.warn("Successfully loaded RDF from blob: " + blobUrl);
                            } else {
                                logger.error("Failed to load RDF content from blob: " + blobUrl);
                            }
                        }
                    }
                } else {
                    // Single file URL
                    logger.warn("Loading RDF from URL: " + graphPath);
                    String rdfContent = fileUtil.readUnicode(graphPath);
                    if (rdfContent != null && !rdfContent.isEmpty()) {
                        // Guess the language from the URL extension
                        String lowerPath = graphPath.toLowerCase();
                        Lang lang = Lang.TTL;
                        if (lowerPath.endsWith(".nt")) lang = Lang.NT;
                        else if (lowerPath.endsWith(".rdf")) lang = Lang.RDFXML;
                        else if (lowerPath.endsWith(".owl")) lang = Lang.RDFXML;
                        
                        java.io.InputStream is = new java.io.ByteArrayInputStream(
                            rdfContent.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                        model.read(is, null, lang.getName());
                        logger.warn("Successfully loaded RDF from URL");
                    } else {
                        logger.error("Failed to load RDF content from URL: " + graphPath);
                    }
                }
            } else {
                // Load from local file or directory
                java.io.File fileOrDir = new java.io.File(graphPath);
                if (fileOrDir.isDirectory()) {
                    java.io.File[] files = fileOrDir.listFiles((dir, name) -> name.endsWith(".ttl") || name.endsWith(".nt") || name.endsWith(".rdf") || name.endsWith(".owl"));
                    if (files != null) {
                        for (java.io.File f : files) {
                            logger.warn("Loading RDF file: " + f.getAbsolutePath());
                            // Try to guess the language from the extension
                            String fname = f.getName().toLowerCase();
                            Lang lang = Lang.TTL;
                            if (fname.endsWith(".nt")) lang = Lang.NT;
                            else if (fname.endsWith(".rdf")) lang = Lang.RDFXML;
                            else if (fname.endsWith(".owl")) lang = Lang.RDFXML;
                            model.read(f.getAbsolutePath(), lang.getName());
                        }
                    }
                } else {
                    // Single file
                    String fname = fileOrDir.getName().toLowerCase();
                    Lang lang = Lang.TTL;
                    if (fname.endsWith(".nt")) lang = Lang.NT;
                    else if (fname.endsWith(".rdf")) lang = Lang.RDFXML;
                    else if (fname.endsWith(".owl")) lang = Lang.RDFXML;
                    model = g.readGraphFromFile(graphPath, lang);
                }
            }
            logger.warn("model class:" + model.getClass().getName());
            logger.warn("empty: " + model.isEmpty());
            // Create reasoner and materialize inferences
            Reasoner reasoner = ReasonerRegistry.getRDFSReasoner().bindSchema(ontology);
            InfModel infModel = ModelFactory.createInfModel(reasoner, model);
            // Materialize all inferred triples into a new model
            Model materialized = ModelFactory.createDefaultModel().add(infModel);
            g.setModel(materialized);
        }
        catch (Throwable t) {
            t.printStackTrace();
        }
    }

    /**
     * Return a Cosmos DB NoSQL API SELECT query which returns only the necessary
     * attributes for building the in-memory graph.  For example, exclude the
     * "embeddings" attribute and large text value attributes.
     */
    private static String cosmosdbSourceSqlQuery() {
        return """
        select c._id, c.name, c.libtype, c.kwds, c.developers, c.dependency_ids, c.release_count from c offset 0 limit 999999
        """.strip();
    }

    private static String docAsJson(Map doc, boolean pretty) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            if (pretty) {
                return mapper.writerWithDefaultPrettyPrinter().writeValueAsString(doc);
            }
            else {
                return mapper.writeValueAsString(doc);
            }
        }
        catch (JsonProcessingException e) {
            return null;
        }
    }
}

