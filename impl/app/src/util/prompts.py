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
You are a helpful agent designed to generate a query to the knowledge graph, which is built using RDF 1.0 principles.

The following ontology pertains to the knowledge graph:
{minimized_owl}

The knowledge graph can match entities with multiple relationships to several other entities.

Example user input:
"Which documents have more than one client?"

Return a JSON with SPARQL 1.0 query that would return the relevant entities and/or relationships from the knowledge graph.
""".strip()
        except Exception as e:
            logging.critical(
                "Exception in generate_sparql_system_prompt: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return None
