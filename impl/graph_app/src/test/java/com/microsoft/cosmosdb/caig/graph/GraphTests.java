package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.cosmosdb.caig.util.AppConfig;
import com.microsoft.cosmosdb.caig.util.FileUtil;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class GraphTests {
    @Test
    public void testQueryResultParsing() {
        try {
            String fixtureFile = "data/sample_jena_query_result.json";
            FileUtil fu = new FileUtil();
            String json = fu.readUnicode(fixtureFile);
            ObjectMapper objectMapper = new ObjectMapper();
            DependenciesQueryResult dqr = objectMapper.readValue(json, DependenciesQueryResult.class);

            ArrayList expectedHeadVars = new ArrayList();
            expectedHeadVars.add("used_library");
            assertEquals(1, dqr.getHeadVariableNames().size());
            assertEquals(expectedHeadVars, dqr.getHeadVariableNames());

            ArrayList<HashMap<String, String>> rows = dqr.getBindingValues();
            assertEquals(8, rows.size());
            assertEquals("http://cosmosdb.com/caig#blinker", rows.get(0).get("used_library"));
            assertEquals("http://cosmosdb.com/caig#importlib_metadata", rows.get(7).get("used_library"));

            ArrayList<String> values = dqr.getSingleNamedValues("used_library");
            System.err.println(values);
            assertEquals(8, values.size());
            assertEquals("http://cosmosdb.com/caig#blinker", values.get(0));
            assertEquals("http://cosmosdb.com/caig#importlib_metadata", values.get(7));

            values = dqr.getSingleNamedValues("oops_bad_name");
            System.err.println(values);
            assertEquals(0, values.size());
        }
        catch (Exception e) {
            fail("exception not expected");
        }
    }

}