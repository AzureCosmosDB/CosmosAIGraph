package com.microsoft.cosmosdb.caig;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * This class is the entry point for this Spring Web application per the
 * @SpringBootApplication annotation.
 *
 * The main class is: com.microsoft.cosmosdb.caig.WebApp
 *
 * Chris Joakim, Microsoft, 2025
 */

@SpringBootApplication
public class WebApp {

	public static void main(String[] args) {

		SpringApplication.run(WebApp.class, args);
	}

}
