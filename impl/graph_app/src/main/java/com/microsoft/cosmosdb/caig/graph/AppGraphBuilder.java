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
import com.microsoft.cosmosdb.caig.util.FileUtil;
import org.apache.jena.ontology.OntModel;
import org.apache.jena.ontology.OntModelSpec;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.util.FileManager;
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
 * Chris Joakim, Microsoft, 2025
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
            logger.error("build() - source: " + source);

            switch(source) {
                case GRAPH_SOURCE_JSON_DOCS_FILE:
                    // Same data as GRAPH_SOURCE_COSMOSDB_NOSQL, but with previously captured data in a JSON file
                    model = initialzeModel(true);
                    appGraph.setModel(model);
                    populateFromJsonDocsFile(appGraph);
                    break;
                case GRAPH_SOURCE_COSMOSDB_NOSQL:
                    model = initialzeModel(true);
                    appGraph.setModel(model);
                    populateFromCosmosDbNoSQL(appGraph);
                    break;
                case GRAPH_SOURCE_RDF_FILE:
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
                    appGraph.writeModelToFile(outfile, Lang.NT);
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
    private static Model initialzeModel(boolean readOntology) {

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
                InputStream byteStream = new ByteArrayInputStream(ontology.getBytes(StandardCharsets.UTF_8));
                logger.warn("owlFile:  " + owlFile);
                logger.warn("ontology: " + ontology);

                OntModel model = ModelFactory.createOntologyModel(OntModelSpec.OWL_MEM);
                model.read(byteStream, "");

                model.setNsPrefix("caig", "http://cosmosdb.com/caig#");
                return model;

                // Reasoner reasoner = ReasonerRegistry.getOWLReasoner().bindSchema(model.getGraph());
                // InfModel infModel = ModelFactory.createInfModel(reasoner, model);
                // return infModel;
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

        CosmosAsyncClient cosmosAsyncClient = new CosmosClientBuilder()
                .endpoint(uri)
                .key(key)
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
     * This method is used for initial development, using a previously captured *.nt
     * triples file.
     */
    private static void populateFromRdfFile(AppGraph g) throws Exception {
        //throw new Exception("RDF file graph source not currently implemented");
        try {
            String infile = AppConfig.getGraphRdfFilename();
            logger.warn("populateFromRdfFile - " + infile);
            Model model = FileManager.get().loadModel(infile);
            logger.warn("model class:" + model.getClass().getName()); // class:org.apache.jena.rdf.model.impl.ModelCom
            logger.warn("empty: " + model.isEmpty()); // false
            g.setModel(model);

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