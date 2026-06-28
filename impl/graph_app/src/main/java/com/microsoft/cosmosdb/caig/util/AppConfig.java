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
    public static final String CAIG_COSMOSDB_NOSQL_KEY            = "CAIG_COSMOSDB_NOSQL_KEY";
    public static final String CAIG_GRAPH_SOURCE_TYPE             = "CAIG_GRAPH_SOURCE_TYPE";
    public static final String CAIG_GRAPH_SOURCE_DB               = "CAIG_GRAPH_SOURCE_DB";
    public static final String CAIG_GRAPH_SOURCE_CONTAINER        = "CAIG_GRAPH_SOURCE_CONTAINER";
    public static final String CAIG_GRAPH_SOURCE_OWL_FILENAME     = "CAIG_GRAPH_SOURCE_OWL_FILENAME";
    public static final String CAIG_GRAPH_SOURCE_PATH     = "CAIG_GRAPH_SOURCE_PATH";
    public static final String CAIG_GRAPH_NAMESPACE               = "CAIG_GRAPH_NAMESPACE";
    public static final String CAIG_GRAPH_DUMP_UPON_BUILD         = "CAIG_GRAPH_DUMP_UPON_BUILD";
    public static final String CAIG_GRAPH_DUMP_OUTFILE            = "CAIG_GRAPH_DUMP_OUTFILE";
    public static final String CAIG_GRAPH_BACKEND                 = "CAIG_GRAPH_BACKEND";
    public static final String CAIG_FUSEKI_DATASET_URL           = "CAIG_FUSEKI_DATASET_URL";
    public static final String CAIG_FUSEKI_USER                  = "CAIG_FUSEKI_USER";
    public static final String CAIG_FUSEKI_PASSWORD              = "CAIG_FUSEKI_PASSWORD";

    // Graph backend types
    public static final String GRAPH_BACKEND_IN_MEMORY = "in_memory";
    public static final String GRAPH_BACKEND_FUSEKI    = "fuseki";

    public static final String[] DEFINED_ENVIRONMENT_VARIABLES = {
            CAIG_COSMOSDB_NOSQL_ACCT,
            CAIG_COSMOSDB_NOSQL_URI,
            CAIG_COSMOSDB_NOSQL_KEY,
            CAIG_GRAPH_SOURCE_TYPE,
            CAIG_GRAPH_SOURCE_DB,
            CAIG_GRAPH_SOURCE_CONTAINER,
            CAIG_GRAPH_SOURCE_OWL_FILENAME,
            CAIG_GRAPH_SOURCE_PATH,
            CAIG_GRAPH_NAMESPACE,
            CAIG_GRAPH_DUMP_UPON_BUILD,
            CAIG_GRAPH_DUMP_OUTFILE,
            CAIG_GRAPH_BACKEND,
            CAIG_FUSEKI_DATASET_URL,
            CAIG_FUSEKI_USER
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

        if (name != null)
            return (overrideProperties.containsKey(name)) ?
                    overrideProperties.getProperty(name).replaceAll("^(\"|')|(\"|')$", "") :
                    System.getenv(name);

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
        return getEnvVar(CAIG_GRAPH_SOURCE_OWL_FILENAME, "");
    }

    public static String getGraphPath() {
        return getEnvVar(CAIG_GRAPH_SOURCE_PATH, "");
    }

    public static String getGraphNamespace() {
        return getEnvVar(CAIG_GRAPH_NAMESPACE, "");
    }

    public static boolean dumpGraphUponBuild() {
        String s = getEnvVar(CAIG_GRAPH_DUMP_UPON_BUILD, "").toLowerCase();
        if (s.contains("true")) {
            return true;
        }
        return false;
    }

    public static String getGraphDumpOutfile() {
        return getEnvVar(CAIG_GRAPH_DUMP_OUTFILE, null);
    }

    /**
     * Return the configured graph backend type, defaulting to "in_memory".
     * Supported values are "in_memory" (the default, in-process Apache Jena model)
     * and "fuseki" (an external Apache Jena Fuseki triple store sidecar).
     */
    public static String getGraphBackend() {
        return getEnvVar(CAIG_GRAPH_BACKEND, GRAPH_BACKEND_IN_MEMORY).trim().toLowerCase();
    }

    /**
     * Return true if the graph should be served from an external Apache Jena
     * Fuseki sidecar rather than the in-process in-memory Jena model.
     */
    public static boolean useFusekiBackend() {
        return GRAPH_BACKEND_FUSEKI.equals(getGraphBackend());
    }

    /**
     * Return the base URL of the Fuseki dataset, e.g. "http://localhost:3030/caig".
     * The standard query, update, and Graph Store Protocol endpoints are derived
     * from this base URL ("/query", "/update", "/data").
     */
    public static String getFusekiDatasetUrl() {
        return getEnvVar(CAIG_FUSEKI_DATASET_URL, "http://localhost:3030/caig");
    }

    /**
     * Return the username used to authenticate to the Fuseki sidecar, defaulting
     * to "admin". Return an empty string to disable HTTP authentication.
     */
    public static String getFusekiUser() {
        return getEnvVar(CAIG_FUSEKI_USER, "admin");
    }

    /**
     * Return the password used to authenticate to the Fuseki sidecar, defaulting
     * to "admin".
     */
    public static String getFusekiPassword() {
        return getEnvVar(CAIG_FUSEKI_PASSWORD, "admin");
    }
}
