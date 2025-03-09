package com.microsoft.cosmosdb.caig.graph;

import org.apache.jena.rdf.model.* ;

/**
 * Example of how to define a custom RDF Vocabulary, in this case for the Caig (CosmosAIGraph)
 * reference implementation.  See the alternative implementation in LibrariesGraphTriplesBuilder.
 * Chris Joakim, Microsoft, 2025
 */
public class Caig extends Object {

    public static final String uri = "http://cosmosdb.com/caig#/";

    public static final Property uses_library    = ResourceFactory.createProperty( uri, "uses_library" );
    public static final Property used_by_library = ResourceFactory.createProperty( uri, "used_by_library" );

    public static final Property developer_of = ResourceFactory.createProperty( uri, "developer_of" );
    public static final Property developed_by = ResourceFactory.createProperty( uri, "developed_by" );

    public static String getURI() {
        return uri;
    }
}
