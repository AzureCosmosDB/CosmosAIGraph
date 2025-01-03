package com.microsoft.cosmosdb.caig.web;

import com.microsoft.cosmosdb.caig.graph.AppGraph;
import com.microsoft.cosmosdb.caig.graph.AppGraphBuilder;
import com.microsoft.cosmosdb.caig.models.GraphReloadResponse;
import com.microsoft.cosmosdb.caig.models.HealthResponse;
import com.microsoft.cosmosdb.caig.models.SparqlQueryRequest;
import com.microsoft.cosmosdb.caig.models.SparqlQueryResponse;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.Locale;

/**
 * This class implements the Health functionality HTTP endpoint of this Spring application
 * per the @RestController annotation.  A runtime environment such as Azure Container Apps (ACA)
 * or Azure Kubernetes Service (AKS) can be configured to envoke this endpoint to determine
 * the health of this node and restart it as necessary.
 *
 * Chris Joakim, Microsoft, 2025
 */

@RestController
public class HealthRestController {

    // Class variables
    private static Logger logger = LogManager.getLogger(HealthRestController.class);
    private static final String SPARQL_QUERY = "SELECT * WHERE { ?s ?p ?o . } LIMIT 10";

    @GetMapping("/health")
    public HealthResponse healthCheck() {

        HealthResponse healthResponse = new HealthResponse();
        AppGraph appGraph = AppGraph.getSingleton();
        healthResponse.setSuccessfulQueries(appGraph.getSuccessfulQueriesCount());
        healthResponse.setUnsuccessfulQueries(appGraph.getUnsuccessfulQueriesCount());
        healthResponse.setLastSuccessfulQueryTime(appGraph.getLastSuccessfulQueryTime());

        // Query the graph if it hasn't been successfully queried in the last n-minutes.
        // n is 2 for this reference impl; modify this as necessary;
        long oneMinute = 60000;
        long now    = System.currentTimeMillis();
        long recent = now - (oneMinute * 2);
        long last   = appGraph.getLastSuccessfulQueryTime();
        logger.warn("now:    " + now);
        logger.warn("recent: " + recent);
        logger.warn("last:   " + last);

        if (last < recent) {
            SparqlQueryRequest request = new SparqlQueryRequest();
            request.setSparql(SPARQL_QUERY);
            SparqlQueryResponse queryResponse = appGraph.query(request);
            if (queryResponse.getResults() == null) {
                throw new HealthCheckFailureException("unable to query the graph at this time");
            }
            else {
                healthResponse.setMessage("successful realtime graph query executed");
            }
            healthResponse.setSuccessfulQueries(appGraph.getSuccessfulQueriesCount());
            healthResponse.setUnsuccessfulQueries(appGraph.getUnsuccessfulQueriesCount());
            healthResponse.setLastSuccessfulQueryTime(appGraph.getLastSuccessfulQueryTime());
        }
        else {
            healthResponse.setMessage("successful recent graph activity");
        }
        return healthResponse;
    }

    @ResponseStatus(HttpStatus.SERVICE_UNAVAILABLE)
    public class HealthCheckFailureException extends RuntimeException {
        public HealthCheckFailureException(String message) {
            super(message);
        }
    }

}