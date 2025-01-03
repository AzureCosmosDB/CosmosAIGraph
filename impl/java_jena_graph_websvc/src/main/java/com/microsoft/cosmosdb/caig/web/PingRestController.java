package com.microsoft.cosmosdb.caig.web;

import com.microsoft.cosmosdb.caig.models.PingResponse;
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

    @GetMapping("/")
    public long index() {
        return System.currentTimeMillis();
    }

    @GetMapping("/ping")
    public PingResponse ping() {
        return new PingResponse();
    }
}