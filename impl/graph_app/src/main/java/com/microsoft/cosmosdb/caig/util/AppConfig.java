package com.microsoft.cosmosdb.caig.util;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.Properties;

/**
 * This class, with all static methods, is responsible for providing all configuration
 * values for the application, such as from environment variables.
 *
 * Chris Joakim, Microsoft, 2025
 */

public class AppConfig {

    // Constants
    public static final String APPLICATION_VERSION = "3.0";

    // Constants - Environment Variable Names
    public static final String CAIG_COSMOSDB_NOSQL_ACCT           = "CAIG_COSMOSDB_NOSQL_ACCT";
    public static final String CAIG_COSMOSDB_NOSQL_URI            = "CAIG_COSMOSDB_NOSQL_URI";
    public static final String CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM = "CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM";
    public static final String CAIG_COSMOSDB_NOSQL_KEY            = "CAIG_COSMOSDB_NOSQL_KEY";
    public static final String CAIG_GRAPH_SOURCE_TYPE             = "CAIG_GRAPH_SOURCE_TYPE";
    public static final String CAIG_GRAPH_SOURCE_DB               = "CAIG_GRAPH_SOURCE_DB";
    public static final String CAIG_GRAPH_SOURCE_CONTAINER        = "CAIG_GRAPH_SOURCE_CONTAINER";
    public static final String CAIG_GRAPH_SOURCE_OWL_FILENAME     = "CAIG_GRAPH_SOURCE_OWL_FILENAME";
    public static final String CAIG_GRAPH_SOURCE_RDF_FILENAME     = "CAIG_GRAPH_SOURCE_RDF_FILENAME";
    public static final String CAIG_GRAPH_NAMESPACE               = "CAIG_GRAPH_NAMESPACE";
    public static final String CAIG_GRAPH_DUMP_UPON_BUILD         = "CAIG_GRAPH_DUMP_UPON_BUILD";
    public static final String CAIG_GRAPH_DUMP_OUTFILE            = "CAIG_GRAPH_DUMP_OUTFILE";

    public static final String[] DEFINED_ENVIRONMENT_VARIABLES = {
            CAIG_COSMOSDB_NOSQL_ACCT,
            CAIG_COSMOSDB_NOSQL_URI,
            CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM,
            CAIG_COSMOSDB_NOSQL_KEY,
            CAIG_GRAPH_SOURCE_TYPE,
            CAIG_GRAPH_SOURCE_DB,
            CAIG_GRAPH_SOURCE_CONTAINER,
            CAIG_GRAPH_SOURCE_OWL_FILENAME,
            CAIG_GRAPH_SOURCE_RDF_FILENAME,
            CAIG_GRAPH_NAMESPACE,
            CAIG_GRAPH_DUMP_UPON_BUILD,
            CAIG_GRAPH_DUMP_OUTFILE
    };

    private static Properties overrideProperties = new Properties();
    private static Logger logger = LoggerFactory.getLogger(AppConfig.class);
    private static long initialzedEpoch;

    /**
     * Attempt to read the .override_properties file in the app directory.
     * This file is optional, and should contain environment variable overrides.
     * This functionality is similar to https://pypi.org/project/python-dotenv/
     * See file example-override.properties in the graph app directory.
     */
    public static void initialize() {
        initialzedEpoch = System.currentTimeMillis();
        logger.warn("initialize at " + initialzedEpoch);
        overrideProperties = new Properties();
        try {
            String userDirectory = System.getProperty("user.dir");
            String infile = String.format("%s%s%s", userDirectory, File.separator, ".override.properties");
            logger.warn("initialize reading infile: " + infile);
            FileReader reader = new FileReader(infile);
            overrideProperties.load(reader);
            ObjectMapper mapper = new ObjectMapper();
            logger.warn("overrideProperties: " + mapper.writerWithDefaultPrettyPrinter().writeValueAsString(overrideProperties));
        }
        catch (IOException e) {
            logger.error("Exception in ApplicationConfig#initialize - optional .override.properties file may be absent or malformed");
        }
    }

    public static long getInitialzedEpoch() {
        return initialzedEpoch;
    }

    /**
     * Return the value of the given environment variable name.
     */
    public static String getEnvVar(String name) {

        if (name != null) {
            if (overrideProperties.containsKey(name)) {
                return overrideProperties.getProperty(name);
            }
            return System.getenv(name);
        }
        return null;
    }

    /**
     * Return the value of the given environment variable name, defaulting to the
     * given defaultValue if the environment variable is not present.
     */
    public static String getEnvVar(String name, String defaultValue) {

        String s = getEnvVar(name);
        if (s == null) {
            return defaultValue;
        }
        else {
            return s;
        }
    }

    /**
     * Log the several CAIG_xxx environment variables, and their values.
     * These are defined above in this class as constants.
     */
    public static void logDefinedEnvironmentVariables() {
        HashMap<String, String> env = new HashMap();
        ObjectMapper objectMapper = new ObjectMapper();
        for (String name : DEFINED_ENVIRONMENT_VARIABLES) {
            String value = getEnvVar(name, "?");
            env.put(name, value);
        }
        try {
            String jsonStr = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(env);
            System.out.println("logDefinedEnvironmentVariables\n%s\n".format(jsonStr));
        }
        catch (JsonProcessingException e) {
            throw new RuntimeException(e);
        }
    }

    public static String getApplicationVersion() {
        return APPLICATION_VERSION;
    }

    public static String getCosmosNoSqlAcount() {
        return getEnvVar(CAIG_COSMOSDB_NOSQL_ACCT, null);
    }

    public static String getCosmosNoSqlUri() {
        return getEnvVar(CAIG_COSMOSDB_NOSQL_URI, null);
    }

    public static String getCosmosNoSqlAuthMechanism() {
        return getEnvVar(CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM, null);
    }

    public static String getCosmosNoSqlKey1() {
        return getEnvVar(CAIG_COSMOSDB_NOSQL_KEY, null);
    }

    public static String getGraphSourceType() {
        return getEnvVar(CAIG_GRAPH_SOURCE_TYPE, "cosmos_nosql");
    }

    public static String getGraphSourceDb() {
        return getEnvVar(CAIG_GRAPH_SOURCE_DB, null);
    }

    public static String getGraphSourceContainer() {
        return getEnvVar(CAIG_GRAPH_SOURCE_CONTAINER, null);
    }

    public static String getGraphOwlFilename() {
        return getEnvVar(CAIG_GRAPH_SOURCE_OWL_FILENAME, "./ontologies/libraries.owl");
    }

    public static String getGraphRdfFilename() {
        return getEnvVar(CAIG_GRAPH_SOURCE_RDF_FILENAME, "./rdf/libraries-graph.nt");
    }

    public static String getGraphNamespace() {
        return getEnvVar(CAIG_GRAPH_NAMESPACE, "http://cosmosdb.com/caig#");
    }

    public static boolean dumpGraphUponBuild() {
        String s = getEnvVar(CAIG_GRAPH_DUMP_UPON_BUILD, "").toLowerCase();
        if (s.contains("true")) {
            return true;
        }
        return false;
    }

    public static String getGraphDumpOutfile() {
        return getEnvVar(CAIG_GRAPH_DUMP_OUTFILE, "tmp/graph_dump.nt");
    }
}
