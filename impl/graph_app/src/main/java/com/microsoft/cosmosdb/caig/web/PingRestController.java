package com.microsoft.cosmosdb.caig.web;

import com.microsoft.cosmosdb.caig.models.PingResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * This class implements a simple ping functionality HTTP endpoints of this Spring application
 * per the @RestController annotation.  It will respond with a message and the current
 * epoch time.
 *
 * Chris Joakim, Microsoft, 2025
 */

@RestController
public class PingRestController {

    // Class variables
    private static Logger logger = LoggerFactory.getLogger(PingRestController.class);

    @GetMapping("/")
    public long index() {
        logger.warn("/index");
        return System.currentTimeMillis();
    }

    @GetMapping("/ping")
    public PingResponse ping() {
        logger.warn("/ping");
        return new PingResponse();
    }
}