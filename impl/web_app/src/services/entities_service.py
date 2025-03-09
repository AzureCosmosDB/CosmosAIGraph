import datetime
import logging
import time
import traceback

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.util.counter import Counter
from src.util.fs import FS

# Instances of this class are used to:
# - create and populate the 'entities' document in Cosmos DB
# - identify known entities in given text data per the 'entities' document
#
# Chris Joakim, Microsoft, 2025


class EntitiesService:

    # Class variables
    static_entities_doc = dict()
    static_libraries_dict = dict()
    static_library_names = list()

    @classmethod
    async def initialize(cls, force_reinitialize=False):
        logging.warning(
            "EntitiesService#initialize - force_reinitialize: {}".format(
                force_reinitialize
            )
        )
        cls.entities_doc = dict()
        cls.libraries_dict = dict()
        cls.library_names = list()

        # if EntitiesService has already been initialized, don't reinitialize
        # unless force_reinitialize is True
        if len(EntitiesService.static_library_names) > 0:
            if force_reinitialize == False:
                return

        # this instance of CosmosNoSQLService is transient;
        # is not used outside of this method
        try:
            nosql_svc = CosmosNoSQLService()
            await nosql_svc.initialize()
            nosql_svc.set_db(ConfigService.graph_source_db())
            nosql_svc.set_container(ConfigService.config_container())
            result_doc = await nosql_svc.point_read("entities", "entities")
            docs_found = 0
            if result_doc is not None:
                docs_found = docs_found + 1
                cls.static_entities_doc = result_doc
                cls.libraries_dict = result_doc["libraries"]
                if "pypi" in cls.libraries_dict.keys():
                    del cls.libraries_dict["pypi"]
                cls.library_names = cls.libraries_dict.keys()
            logging.warning(
                "EntitiesService#load - entities docs found: {}, size: {}".format(
                    docs_found, len(cls.libraries_dict.keys())
                )
            )
            await nosql_svc.close()
        except Exception as e:
            logging.critical(str(e))
            print(traceback.format_exc())

    @classmethod
    def libraries_count(cls):
        try:
            return len(cls.libraries_dict.keys())
        except Exception as e:
            return -1

    @classmethod
    def library_present(cls, name):
        try:
            if name is not None:
                return name in cls.library_names
        except Exception as e:
            pass
        return False

    @classmethod
    def identify(cls, text) -> Counter:
        """Identify the known entities in the given text data, return a dict"""
        c = Counter()
        if text is not None:
            words = text.lower().replace(",", " ").replace(".", " ").strip().split()
            for word in words:
                if len(word) > 1:
                    if word in cls.library_names:
                        c.increment(word)
        return c

    # TODO: revisit this logic.  the graph service should return the dict of entities
    # @classmethod
    # async def create(cls) -> dict:
    #     """
    #     Create and return the 'entities' JSON document to be stored in Cosmos DB.
    #     """
    #     doc = dict()
    #     doc["id"] = "entities"
    #     doc["pk"] = "entities"
    #     doc["created_at"] = time.time()
    #     doc["created_date"] = str(
    #         datetime.datetime.fromtimestamp(doc["created_at"])
    #     )
    #     doc["docs_read"] = -1
    #     doc["elapsed_seconds"] = -1
    #     doc["exception"] = ""
    #     doc["libraries"] = dict()
    #     try:
    #         infile = "../data/entities/entities_doc.json"
    #         data = FS.read_json(infile)
    #         doc["libraries"] = data["libraries"]
    #     except Exception as e:
    #         doc["exception"] = str(e)
    #         logging.critical("EntitiesService#create - exception: {}".format(str(e)))
    #         logging.exception(e, stack_info=True, exc_info=True)
    #     return doc
