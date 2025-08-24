import json
import logging

# Instances of this class are used to parse the HTTP response from
# the /sparql_query endpoint of the graph microservice.  The HTTP
# reponse data is a normalized JSON format from the Apache Jena library.
#
# See the 'outputAsJSON(...)' method in class org.apache.jena.query.ResultSetFormatter
# See impl/web_app/tests/test_sparql_query_response.py
#
# Chris Joakim, Microsoft, 2025
# Aleksey Savateyev, Microsoft, 2025

class SparqlQueryResponse:

    def __init__(self, httpx_response):
        self.r = httpx_response

    def parse(self):
        self.parse_error = False
        self.parse_exception = None
        self.response_obj = None
        self.results_obj = None
        self.count = 0

        try:
            self.text = self.r.text
            self.response_obj = json.loads(self.text)

            self.query_results_obj = self.response_obj.get("results")
            self.count = len(self.results_bindings())

        except Exception as e:
            print(str(e))
            self.parse_error = True
            self.parse_exception = str(e)
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    def has_errors(self) -> bool:
        return self.parse_error

    # def elapsedMs(self) -> float:
    #     try:
    #         return float(self.response_obj["elapsed"])
    #     except:
    #         return -1.0

    def result_variables(self):
        # The 'outputAsJSON(...)' method in class org.apache.jena.query.ResultSetFormatter
        # of the Apache Jena SDK brilliantly includes the names of the response variable
        # names of the SPARQL results.  This Python method returns that list
        # of variable names.  It can be passed to the 'binding_values_for(...)' method
        # below.
        try:
            return self.query_results_obj["head"]["vars"]
        except:
            return list()

    def results_bindings(self):
        try:
            return self.query_results_obj["results"]["bindings"]
        except:
            return list()

    def binding_values_for(self, binding_var_names: list):
        values = list()
        try:
            for binding in self.query_results_obj.get("results", {}).get("bindings", []):
                row_values = dict()
                for var_name in binding_var_names:
                    row_values[var_name] = binding.get(var_name, {}).get("value")
                values.append(row_values)
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
        return values

    def binding_values(self):
        return self.binding_values_for(self.result_variables())


# Example JSON response from the /sparql_query endpoint and Apache Jena:
# {
#   "sparql": "\nPREFIX c: <http://cosmosdb.com/caig#>\nSELECT ?used_library \nWHERE {\n    <http://cosmosdb.com/caig#flask> c:uses_library ?used_library .\n}\nLIMIT 6\n",
#   "results": {
#     "head": {
#       "vars": [
#         "used_library"
#       ]
#     },
#     "results": {
#       "bindings": [
#         {
#           "used_library": {
#             "type": "uri",
#             "value": "http://cosmosdb.com/caig#blinker"
#           }
#         },
#         {
#           "used_library": {
#             "type": "uri",
#             "value": "http://cosmosdb.com/caig#werkzeug"
#           }
#         },
#         {
#           "used_library": {
#             "type": "uri",
#             "value": "http://cosmosdb.com/caig#click"
#           }
#         },
#         {
#           "used_library": {
#             "type": "uri",
#             "value": "http://cosmosdb.com/caig#asgiref"
#           }
#         },
#         {
#           "used_library": {
#             "type": "uri",
#             "value": "http://cosmosdb.com/caig#jinja2"
#           }
#         },
#         {
#           "used_library": {
#             "type": "uri",
#             "value": "http://cosmosdb.com/caig#itsdangerous"
#           }
#         }
#       ]
#     }
#   },
#   "elapsed": 1,
#   "error": "",
#   "start_time": 1741360832280,
#   "finish_time": 1741360832281
