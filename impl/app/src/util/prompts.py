# Instances of this class are used to return various "engineered"
# system or user prompt strings.
# Chris Joakim, Aleksey Savateyev, Microsoft

import logging


class Prompts:
    def __init__(self, opts={}):
        self.opts = opts

    def generate_sparql_system_prompt(self, minimized_owl) -> str | None:
        try:
            return f"""
You are a helpful agent designed to generate a query to the knowledge graph, which is built using standard RDF principles and technologies.
The following ontology describes the entities and relationships in the knowledge graph:
{minimized_owl}
While not including type suffixes such as ^^xsd:string and using concise Turtle syntax, generate and return a JSON document with SPARQL 1.1 query that would return the relevant entities and/or relationships per user prompt. 
""".strip()
        except Exception as e:
            logging.critical(
                "Exception in generate_sparql_system_prompt: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return None
