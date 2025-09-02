package com.microsoft.cosmosdb.caig.graph;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Instances of this class are used to parse a JENA SPARQL query response.
 * The Jackson JSON library is used to do this.
 *
 * Chris Joakim, Microsoft, 2025
 */

@Data
public class DependenciesQueryResult {

    @JsonProperty("head")
    public Map<String, List<String>> headBindings;

    @JsonProperty("results")
    public ResultsBindings resultsBindings;

    public DependenciesQueryResult() {
        super();
    }

    public List<String> getHeadVariableNames() {
        return headBindings.get("vars");
    }

    /**
     * This method should be used when the SPARQL query has multiple return values per row.
     */
    public ArrayList<HashMap<String, String>> getBindingValues () {

        ArrayList<HashMap<String, String>> returnValues = new ArrayList<HashMap<String, String>>();
        List<String> headVars = this.getHeadVariableNames();

        List<Map> bindings = resultsBindings.bindings;
        for (int i = 0; i < bindings.size(); i++) {
            Map binding = bindings.get(i);
            HashMap<String, String> rowValues = new HashMap<String, String>();

            for (int h = 0; h < headVars.size(); h++) {
                String var = headVars.get(h);
                Map map = (Map) binding.get(var);
                if (map == null)
                    continue;
                rowValues.put(var, (String) map.get("value"));
            }
            returnValues.add(rowValues);
        }
        return returnValues;
    }

    /**
     * This method can be used when the SPARQL query has as single named return value
     * per row (i.e. - 'used_library').  The given varName should be in the Jena query
     * response head vars array.
     */
    public ArrayList<String> getSingleNamedValues(String varName) {

        ArrayList<HashMap<String, String>> rows = this.getBindingValues();
        ArrayList<String> returnValues = new ArrayList<String>();

        try {
            for (int i = 0; i < rows.size(); i++) {
                HashMap<String, String> row = rows.get(i);
                if (row.containsKey(varName)) {
                    returnValues.add(row.get(varName));
                }
            }
        }
        catch (Exception e) {
            throw new RuntimeException(e);
        }
        return returnValues;
    }
}

