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
import org.apache.jena.riot.RDFWriter;
import org.apache.jena.riot.RIOT;
import org.apache.jena.util.FileManager;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import reactor.core.publisher.Flux;

import java.io.ByteArrayInputStream;
import java.io.FileOutputStream;
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
 *
 * Chris Joakim, Microsoft, 2025
 */

public class AppGraphBuilder {

    // Constants
    public static final String GRAPH_SOURCE_COSMOSDB_NOSQL = "cosmos_nosql";
    public static final String GRAPH_SOURCE_COSMOSDB_VCORE = "cosmos_vcore";
    public static final String GRAPH_SOURCE_RDF_FILE       = "rdf_file";
    public static final String GRAPH_SOURCE_JSON_DOCS_FILE = "json_docs_file";  // captured CosmosDB documents

    // Class variables
    private static Logger logger = LogManager.getLogger(AppGraphBuilder.class);

    /**
     * This constructor is intentionally private; use the static build() method.
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
    public static AppGraph build(String overrideQuery) {
        logger.warn("GraphBuilder#build() start, overrideQuery: " + overrideQuery);
        AppGraph appGraph = null;
        Model model = null;

        try {
            appGraph = new AppGraph();
            String source = AppConfig.getGraphSourceType();
            //String query = "SELECT * WHERE { ?s ?p ?o . } LIMIT 10";
            String query = "SELECT (COUNT(?s) AS ?triples) WHERE { ?s ?p ?o }";
            if (overrideQuery != null) {
                query = overrideQuery;
            }
            logger.error("GraphBuilder#build() - source: " + source);

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
                case GRAPH_SOURCE_COSMOSDB_VCORE:
                    model = initialzeModel(true);
                    appGraph.setModel(model);
                    populateFromCosmosDbVcore(appGraph);
                    break;
                case GRAPH_SOURCE_RDF_FILE:
                    populateFromRdfFile(appGraph);
                    break;

                default:
                    logger.error("GraphBuilder#build() - unknown graph source: " + source);
            }
            AppGraph.setSingleton(appGraph);

            // Initial query to check the newly loaded graph.
            if (query != null) {
                SparqlQueryRequest req = new SparqlQueryRequest();
                req.setSparql(query);
                SparqlQueryResponse resp = appGraph.query(req);
                logger.warn("SparqlQueryResponse: "  + resp);
            }

            // Optionally dump the newly loaded graph
            if (AppConfig.dumpGraphUponBuild()) {
                String outfile = AppConfig.getGraphDumpOutfile();
                if (outfile != null) {
                    appGraph.writeModelToFile(outfile, Lang.NT);
                }
            }
        }
        catch (Exception ex) {
            ex.printStackTrace();
        }
        logger.warn("GraphBuilder#build() finish");
        return appGraph;
    }

    /**
     * Create and return the Jena Model object which represents the graph.
     */
    private static Model initialzeModel(boolean readOntology) {

        // https://jena.apache.org/documentation/ontology/
        // https://stackoverflow.com/questions/37398476/reading-an-owl-file-using-jena-api
        // The path is in the src directory of the codebase.

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
                logger.warn("ontology: " + ontology);

                OntModel model = ModelFactory.createOntologyModel(OntModelSpec.OWL_MEM);
                model.read(byteStream, "");

                model.setNsPrefix("caig", "http://cosmosdb.com/caig#");
                return model;

                //            Reasoner reasoner = ReasonerRegistry.getOWLReasoner().bindSchema(model.getGraph());
                //            InfModel infModel = ModelFactory.createInfModel(reasoner, model);
                //            return infModel;
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

    private static void populateFromCosmosDbNoSQL(AppGraph g) {

        // See example here:
        // https://github.com/Azure/azure-sdk-for-java/tree/main/sdk/cosmos/azure-cosmos#create-cosmos-client

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
                //logger.warn(docAsJson(doc, true));
                //allDocuments.add(doc);
                triplesBuilder.ingestDocument(doc);
            }
            return Flux.empty();
        }).blockLast();

        g.setDocsRead(docCounter.get());
        logger.warn("populateFromCosmosDbNoSQL, docCount:  " + docCounter.get());

        // Initial ad-hoc code to capture the Cosmos DB documents to a file for use
        // in the above populateFromJsonDocsFile() method.
        if (false) {
            try {
                FileUtil fileUtil = new FileUtil();
                fileUtil.writeJson(allDocuments, "tmp/cosmosdb_documents.json", true, true);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private static void populateFromCosmosDbVcore(AppGraph g) throws Exception {
        throw new Exception("CosmosDB vCore graph source not currently implemented");
    }

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

    private static String cosmosdbSourceSqlQuery() {
        return """
        select c._id, c.name, c.libtype, c.kwds, c.developers, c.dependency_ids from c offset 0 limit 999999
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