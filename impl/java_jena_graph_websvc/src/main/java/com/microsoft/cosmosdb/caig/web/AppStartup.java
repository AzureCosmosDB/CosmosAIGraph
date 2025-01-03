package com.microsoft.cosmosdb.caig.web;


import com.microsoft.cosmosdb.caig.graph.AppGraph;
import com.microsoft.cosmosdb.caig.graph.AppGraphBuilder;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.context.ApplicationListener;
import org.springframework.context.event.ContextRefreshedEvent;
import org.springframework.stereotype.Component;

/**
 * This class is invoked upon Spring application startup per the ApplicationListener
 * interface.  This startup logic will invoke class AppGraphBuilder to create the
 * singleton instance of class AppGraph.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Component
public class AppStartup implements
        ApplicationListener<ContextRefreshedEvent> {

    // Class variables
    private static Logger logger = LogManager.getLogger(AppStartup.class);
    public static int counter = 0;

    @Override public void onApplicationEvent(ContextRefreshedEvent event) {
        counter++;
        logger.warn("onApplicationEvent " + counter);

        AppConfig.initialize();
        AppConfig.logDefinedEnvironmentVariables();
        logger.warn("application version: " + AppConfig.getApplicationVersion());

        AppGraph g = AppGraphBuilder.build(null);
        AppGraph.setSingleton(g);

        // Redundant logging for readability after verbose AppGraphBuilder.build().
        AppConfig.logDefinedEnvironmentVariables();
        logger.warn("application version: " + AppConfig.getApplicationVersion());
    }
}
