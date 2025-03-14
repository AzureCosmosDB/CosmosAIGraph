package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.impl.PropertyImpl;
import org.apache.jena.vocabulary.RDF;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;

/**
 * Class AppGraphBuilder creates an instance of this class at application startup
 * and invokes the "ingestDocument(...)" method for each graph source document read
 * from Azure Cosmos DB.  Thus, the AppGraph is built in an incremental manner.
 *
 * Note that one Cosmos DB document may result in the creation of several triples
 * in the graph; it's not a 1:1 ratio of documents-to-triples.
 *
 * Using class LibrariesGraphTriplesBuilder as an example, customers should implement
 * their own XxxGraphTriplesBuilder class for their graphs, named Xxx.
 *
 * A customer XxxGraphTriplesBuilder class can potentially be generated given
 * the known metadata of the ontology and Cosmos DB JSON document structure.
 *
 * Chris Joakim, Microsoft, 2025
 */

public class LibrariesGraphTriplesBuilder {

    // Constants
    public static final String CAIG_NAMESPACE     = "http://cosmosdb.com/caig#";
    public static final String TYPE_LIBRARY_URI   = "http://cosmosdb.com/caig#Library";
    public static final String TYPE_DEVELOPER_URI = "http://cosmosdb.com/caig#Developer";

    // Class variables
    private static Logger logger = LoggerFactory.getLogger(LibrariesGraphTriplesBuilder.class);

    // Instance variables
    private AppGraph graph;
    private Model model;
    private String namespace;
    private long documentsIngested = 0;
    private ObjectMapper objectMapper;

    // These PropertyImpls relate to the Jena Graph, not the Cosmos DB document attribute names.
    PropertyImpl nameProperty;
    PropertyImpl keywordsProperty;
    PropertyImpl usesLibProperty;
    PropertyImpl usedByLibProperty;
    PropertyImpl developerOfProperty;
    PropertyImpl developedByProperty;
    PropertyImpl releaseCountProperty;


    public LibrariesGraphTriplesBuilder(AppGraph g) {
        super();
        this.graph = g;
        this.model = g.getModel();
        this.objectMapper = new ObjectMapper();
        this.namespace = CAIG_NAMESPACE; //AppConfig.getGraphNamespace();

        // These PropertyImpls relate to the Jena Graph, not the Cosmos DB document attribute names.
        // These values (i.e. - 'libtype', 'libname', 'keywords') are in the OWL ontology file
        this.nameProperty = new PropertyImpl(this.namespace, "name");
        this.keywordsProperty = new PropertyImpl(this.namespace, "keywords");
        this.usesLibProperty = new PropertyImpl(this.namespace, "uses_library");
        this.usedByLibProperty = new PropertyImpl(this.namespace, "used_by_library");
        this.developerOfProperty = new PropertyImpl(this.namespace, "developer_of");
        this.developedByProperty = new PropertyImpl(this.namespace, "developed_by");
        this.releaseCountProperty = new PropertyImpl(this.namespace, "release_count");
    }

    public long getDocumentsIngested() {
        return documentsIngested;
    }


    /**
     * Add to the graph the zero-to-many triples that correspond to the given
     * Cosmos DB document.
     * See https://jena.apache.org/tutorials/rdf_api.html
     */
    public void ingestDocument(Map<String, Object> doc) {
        // The Cosmos DB query result documents look like this:
        // {
        //   "_id" : "pypi_flask",
        //   "name" : "flask",
        //   "libtype" : "pypi",
        //   "kwds" : "flask wsgi _wsgi python pip",
        //   "developers" : [ "contact@palletsprojects.com" ],
        //   "dependency_ids" : [ "pypi_asgiref", "pypi_blinker", "pypi_click", "pypi_importlib_metadata", "pypi_itsdangerous", "pypi_jinja2", "pypi_python_dotenv", "pypi_werkzeug" ],
        //    "release_count" : 57
        //  }
        try {
            if (doc != null) {
                this.documentsIngested++;
                String libName = ((String) doc.get("name")).toLowerCase();
                if ((documentsIngested % 1000) == 0) {
                    logger.warn("ingestDocument: " + this.documentsIngested + ", libName: " + libName);
                    logger.debug(this.objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(doc));
                }
                // Create the libraryResource if it doesn't already exist
                String libUri = this.namespace + libName;
                Resource libraryResource = lookupResource(libUri);

                libraryResource = model.createResource(libUri);
                model.add(libraryResource, RDF.type, model.createResource(TYPE_LIBRARY_URI));
                logger.warn("create libraryResource: " + libUri);

                // Add properties/attributes of the Lib
                if (doc.containsKey("name")) {
                    String value = doc.get("name").toString().strip().toLowerCase();
                    libraryResource.addProperty(nameProperty, value);
                }
                if (doc.containsKey("kwds")) {
                    String value = doc.get("kwds").toString().strip().toLowerCase();
                    libraryResource.addProperty(keywordsProperty, value);
                }
                if (doc.containsKey("release_count")) {
                    try {
                        String value = ("" + doc.get("release_count")).strip();
                        libraryResource.addProperty(releaseCountProperty, value);
                    } catch (Throwable t) {
                        logger.error("release_count parse error on libName: " + libName);
                    }
                }

                // Add the dependency relationships between Libs
                if (doc.containsKey("dependency_ids")) {
                    List dependencies = (List) doc.get("dependency_ids");
                    for (int i = 0; i < dependencies.size(); i++) {
                        String dep = dependencies.get(i).toString().strip().toLowerCase();
                        // dep is a value like "pypi_jinja2", parse the "jinja2" out of it
                        if (dep.startsWith("pypi_")) {
                            dep = dep.substring(5).toLowerCase();
                        }
                        String depUri = this.namespace + dep;
                        Resource depResource = lookupResource(depUri);
                        if (depResource == null) {
                            depResource = model.createResource(depUri);
                        }
                        model.add(libraryResource, this.usesLibProperty, depResource);
                        model.add(depResource, this.usedByLibProperty, libraryResource);
                    }
                }

                // Add the relationships between Library and Developer, and Developer to Library
                if (doc.containsKey("developers")) {
                    List developers = (List) doc.get("developers");
                    for (int i = 0; i < developers.size(); i++) {
                        String dev = developers.get(i).toString().strip().toLowerCase();
                        String devUri = this.namespace + dev;
                        Resource devResource = lookupResource(devUri);

                        devResource = model.createResource(devUri);
                        model.add(devResource, RDF.type, model.createResource(TYPE_DEVELOPER_URI));
                        logger.warn("create devResource: " + devUri);

                        model.add(libraryResource, this.developedByProperty, devResource);
                        model.add(devResource, this.developerOfProperty, libraryResource);
                    }
                }
            }
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * Lookup the given URI in the model.  Return either the Resource, or null.
     */
    public Resource lookupResource(String uri) {
        Resource res = null;
        if (uri != null) {
            res = this.model.getResource(uri);
            if (res != null) {
                //logger.warn("lookupResource found: " + uri);
            }
        }
        return res;
    }

    /**
     * Return the full java classname of the given object, or null.
     */
    private String classname(Object obj) {
        if (obj == null) {
            return null;
        }
        return obj.getClass().getName();
    }
}
