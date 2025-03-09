import logging

import httpx

from src.services.config_service import ConfigService
from src.util.fs import FS

# Central point in the application to get the Ontology/OWL file.
# Chris Joakim, Microsoft, 2025


class OntologyService:

    owl_filename = None
    owl = None
    http_url = None
    http_status_code = -1
    http_content = None
    http_content_saved = False

    @classmethod
    async def initialize(cls):
        cls.owl_filename = ConfigService.graph_source_owl_filename()
        cls.owl = None
        cls.http_status_code = None
        cls.http_content = None

        # This HTTP-based logic is disabled for now.  Read the OWL from disk instead.
        # First, try to HTTP GET the ontology from the graph service,
        # as it is the single source of truth of the ontology definition.
        # Save the ontology to disk if it appears to be valid.
        # try:
        #     cls.http_url = ConfigService.graph_service_ontology_url()
        #     logging.warning("OntologyService: GET {}".format(cls.http_url))

        #     async with httpx.AsyncClient() as client:
        #         r = await client.get(cls.http_url, timeout=30.0)
        #         cls.http_status_code = r.status_code
        #         cls.http_content = r.text.strip()
        #         logging.warning(
        #             "OntologyService: status_code {}".format(cls.http_status_code)
        #         )
        #         if cls.http_status_code == 200:
        #             if cls.http_content.startswith('<?xml version="1.0"?>'):
        #                 if cls.http_content.endswith("</rdf:RDF>"):
        #                     FS.write(cls.owl_filename, cls.http_content)
        #                     cls.http_content_saved = True
        #                     cls.owl = cls.http_content
        # except Exception as e:
        #     logging.critical(
        #         "Exception in OntologyService#initialize http request: {}".format(
        #             str(e)
        #         )
        #     )
        #     logging.exception(e, stack_info=True, exc_info=True)

        # Read the last saved ontology file from disk if necessary
        if cls.owl is None:
            try:
                cls.owl = FS.read(cls.owl_filename)
            except Exception as e:
                logging.critical(
                    "Exception in OntologyService#initialize reading file: {}".format(
                        str(e)
                    )
                )
                logging.exception(e, stack_info=True, exc_info=True)

        if cls.owl is None:
            logging.critical(
                "OntologyService#initialize complete.  FATAL ERROR - owl is null!"
            )
        else:
            logging.warning(
                "OntologyService#initialize complete, owl length: {}".format(
                    len(cls.owl)
                )
            )

    @classmethod
    def get_owl_content(cls):
        return cls.owl
