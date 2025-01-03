package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.impl.PropertyImpl;
import org.apache.jena.vocabulary.RDF;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.List;
import java.util.Map;

/**
 * Class AppGraphBuilder creates an instance of this class at application startup
 * and invokes the "ingestDocument(...)" method for each graph source document read
 * from Azure Cosmos DB.  Thus, the AppGraph is built in an incremental manner.
 *
 * Note that one Cosmos DB document may result in the creation of many triples
 * in the graph; it's not a 1:1 ratio of documents-to-triples.
 *
 * Using class LibrariesGraphTriplesBuilder as an example, customers should implement
 * their own XxxGraphTriplesBuilder class for their graphs, named Xxx.
 *
 * Chris Joakim, Microsoft, 2025
 */

public class LibrariesGraphTriplesBuilder {

    // Constants
    public static final String TYPE_LIB_URI = "http://cosmosdb.com/caig#Lib";
    public static final String TYPE_DEV_URI = "http://cosmosdb.com/caig#Dev";

    // Class variables
    private static Logger logger = LogManager.getLogger(LibrariesGraphTriplesBuilder.class);

    // Instance variables
    private AppGraph graph;
    private Model model;
    private String namespace;
    PropertyImpl libtypeProperty;
    PropertyImpl nameProperty;
    PropertyImpl kwdsProperty;
    PropertyImpl usesLibProperty;
    PropertyImpl usedByLibProperty;
    PropertyImpl developerOfProperty;
    PropertyImpl developedByProperty;
    private long documentsIngested = 0;
    private ObjectMapper objectMapper;

    public LibrariesGraphTriplesBuilder(AppGraph g) {
        super();
        this.graph = g;
        this.model = g.getModel();
        this.objectMapper = new ObjectMapper();
        this.namespace = AppConfig.getGraphNamespace();
        this.libtypeProperty = new PropertyImpl(this.namespace, "libtype");
        this.nameProperty = new PropertyImpl(this.namespace, "name");
        this.kwdsProperty = new PropertyImpl(this.namespace, "kwds");
        this.usesLibProperty = new PropertyImpl(this.namespace, "uses_lib");
        this.usedByLibProperty = new PropertyImpl(this.namespace, "used_by_lib");
        this.developerOfProperty = new PropertyImpl(this.namespace, "developer_of");
        this.developedByProperty = new PropertyImpl(this.namespace, "developed_by");
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
        //  {
        //    "_id" : "pypi_zulip",
        //    "name" : "zulip",
        //    "libtype" : "pypi",
        //    "kwds" : "zulip_api_key zulip_client zulip_config zulip zulip_site",
        //    "developers" : [ "zulip-devel@googlegroups.com", "zulip_open_source_project" ],
        //    "dependency_ids" : [ "pypi_click", "pypi_distro", "pypi_requests", "pypi_typing_extensions" ]
        //  }
        try {
            if (doc != null) {
                this.documentsIngested++;
                String libId = (String) doc.get("_id");
                if ((documentsIngested % 1000) == 0) {
                    logger.warn("ingestDocument: " + this.documentsIngested + ", libId: " + libId);
                    logger.debug(this.objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(doc));
                }
                // Create the libraryResource if it doesn't already exist
                String libUri = "http://cosmosdb.com/caig/" + libId;
                Resource libraryResource = lookupResource(libUri);
                if (libraryResource == null) {
                    libraryResource = model.createResource(libUri);
                    model.add(libraryResource, RDF.type, TYPE_LIB_URI);
                    logger.debug("create libraryResource: " + libUri);
                }

                // Add properties/attributes of the Lib
                if (doc.containsKey("libtype")) {
                    String value = doc.get("libtype").toString().strip();
                    libraryResource.addProperty(libtypeProperty, value);
                }
                if (doc.containsKey("name")) {
                    String value = doc.get("name").toString().strip();
                    libraryResource.addProperty(nameProperty, value);
                }
                if (doc.containsKey("kwds")) {
                    String value = doc.get("kwds").toString().strip();
                    libraryResource.addProperty(kwdsProperty, value);
                }

                // Add the dependency relationships between Libs
                if (doc.containsKey("dependency_ids")) {
                    List dependencies = (List) doc.get("dependency_ids");
                    for (int i = 0; i < dependencies.size(); i++) {
                        String dep = dependencies.get(i).toString().strip();
                        String depUri = "http://cosmosdb.com/caig/" + dep;
                        Resource depResource = lookupResource(depUri);
                        if (depResource == null) {
                            depResource = model.createResource(depUri);
                        }
                        libraryResource.addProperty(usesLibProperty, dep);
                        depResource.addProperty(usedByLibProperty, libId);
                    }
                }

                // Add the relationships between Lib and Dev, and Dev and Lib
                if (doc.containsKey("developers")) {
                    List developers = (List) doc.get("developers");
                    for (int i = 0; i < developers.size(); i++) {
                        String dev = developers.get(i).toString().strip();
                        String devUri = "http://cosmosdb.com/caig/" + dev;
                        Resource devResource = lookupResource(devUri);
                        if (devResource == null) {
                            devResource = model.createResource(devUri);
                            model.add(devResource, RDF.type, TYPE_DEV_URI);
                            logger.debug("create devResource: " + devUri);
                        }
                        libraryResource.addProperty(developedByProperty, dev);
                        devResource.addProperty(developerOfProperty, libId);
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
                logger.debug("lookupResource %s %s".format(uri, classname(res)));
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
