import logging

from src.services.config_service import ConfigService
from src.util.fs import FS

# Central point in the application to get the Ontology/OWL file.
# Chris Joakim, Microsoft


class OntologyService:

    def __init__(self, opts={}):
        self.owl_filename = None
        self.owl = None
        try:
            self.owl_filename = ConfigService.graph_source_owl_filename()
            self.owl = FS.read(self.owl_filename)
        except Exception as e:
            logging.critical("Exception in OntologyService#__init__: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    def get_owl_content(self):
        return self.owl
