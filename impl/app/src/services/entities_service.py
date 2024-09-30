import asyncio
import datetime
import logging
import time

from src.services.base_db_service import BaseDBService
from src.services.config_service import ConfigService
from src.services.cosmos_vcore_service import CosmosVCoreService
from src.util.counter import Counter
from src.util.fs import FS

# Instances of this class are used to:
# - create and populate the 'entities' document in Cosmos DB
# - identify known entities in given text data per the 'entities' document
# Chris Joakim, Microsoft

logging.getLogger("pymongo").setLevel(logging.WARNING)


class EntitiesService(BaseDBService):

    # Class variable
    static_entities_doc = None
    static_libraries_dict = None
    static_library_names = None

    def __init__(self, vcore=None):
        """Constructor method; call initialize() immediately after this."""
        super().__init__()  # call BaseDBService constructor
        self.entities_doc = None
        self.libraries_dict = dict()
        self.library_names = list()

    async def initialize(self):
        """This method should be called immediately after the constructor."""
        if EntitiesService.static_entities_doc is not None:
            # Use the previously cached data in the static/class variables
            self.entities_doc = EntitiesService.static_entities_doc
            self.libraries_dict = EntitiesService.static_libraries_dict
            self.library_names = EntitiesService.static_library_names
            return

        if self.using_nosql():
            await self.initialize_cosmos_nosql()
            self.nosql_svc.set_db(ConfigService.graph_source_db())
            self.nosql_svc.set_container(ConfigService.config_container())
            result_doc = await self.nosql_svc.point_read("entities", "entities")
            docs_found = 0
            if result_doc is not None:
                docs_found = docs_found + 1
                self.entities_doc = result_doc
                self.libraries_dict = result_doc["libraries"]
                if "pypi" in self.libraries_dict.keys():
                    del self.libraries_dict["pypi"]
                self.library_names = self.libraries_dict.keys()
            logging.warning(
                "EntitiesService#load - entities docs found: {}, size: {}".format(
                    docs_found, len(self.libraries_dict.keys())
                )
            )
        else:
            await self.initialize_cosmos_vcore()
            self.vcore_svc.set_db(ConfigService.graph_source_db())
            self.vcore_svc.set_coll(ConfigService.config_container())
            query_spec = {"id": "entities"}
            cursor = self.vcore_svc.get_coll().find(query_spec, skip=0, limit=999999)
            docs_found = 0
            for result_doc in cursor:
                docs_found = docs_found + 1
                self.entities_doc = result_doc
                self.libraries_dict = result_doc["libraries"]
                if "pypi" in self.libraries_dict.keys():
                    del self.libraries_dict["pypi"]
                self.library_names = self.libraries_dict.keys()
            logging.warning(
                "EntitiesService#load - entities docs found: {}, size: {}".format(
                    docs_found, len(self.libraries_dict.keys())
                )
            )
        static_entities_doc = self.entities_doc
        static_libraries_dict = self.libraries_dict
        static_library_names = self.library_names

    def libraries_count(self):
        try:
            return len(self.libraries_dict.keys())
        except Exception as e:
            return -1

    def library_present(self, name):
        try:
            return name in self.library_names
        except Exception as e:
            pass
        return False

    def identify(self, text) -> Counter:
        """Identify the known entities in the given text data, return a dict"""
        c = Counter()
        if text is not None:
            words = text.lower().replace(",", " ").replace(".", " ").strip().split()
            for word in words:
                if len(word) > 1:
                    if word in self.library_names:
                        c.increment(word)
        return c

    async def create(self):
        """
        Create and return the 'entities' JSON document
        from the set of actual Cosmos DB library documents.
        """
        new_entities = dict()
        new_entities["id"] = "entities"
        new_entities["pk"] = "entities"
        new_entities["created_at"] = time.time()
        new_entities["created_date"] = str(
            datetime.datetime.fromtimestamp(new_entities["created_at"])
        )
        new_entities["docs_read"] = -1
        new_entities["elapsed_seconds"] = -1
        new_entities["exception"] = ""
        new_entities["libraries"] = dict()
        try:
            if self.using_nosql():
                await self.create_nosql_entities_doc(new_entities)
            else:
                await self.create_vcore_entities_doc(new_entities)
        except Exception as e:
            new_entities["exception"] = str(e)
            logging.critical("EntitiesService#create - exception: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
        return new_entities

    async def create_nosql_entities_doc(self, new_entities: dict):
        infile = "../data/entities/entities_doc.json"
        return FS.read_json(infile)

    async def create_vcore_entities_doc(self, new_entities: dict):
        self.vcore_svc.set_coll(ConfigService.graph_source_container())
        docs_read = 0
        logging.info("EntitiesService#build start")
        t1 = time.perf_counter()
        coll = self.vcore_svc.get_coll()
        query_spec = {"libtype": "pypi"}
        projection = self.library_projection_attrs()
        cursor = coll.find(query_spec, projection=projection, skip=0, limit=999999)
        for libdoc in cursor:
            docs_read = docs_read + 1
            if docs_read % 1000 == 0:
                logging.info(
                    "EntitiesService#build - libdocs read: {}".format(docs_read)
                )
            name = libdoc["name"]
            new_entities["libraries"][name] = "pypi"
        t2 = time.perf_counter()
        seconds = f"{(t2 - t1):.9f}"
        logging.critical(
            "EntitiesService#create_vcore_entities_doc - {} docs read in {} seconds".format(
                docs_read, seconds
            )
        )
        new_entities["docs_read"] = docs_read
        new_entities["elapsed_seconds"] = seconds
        return new_entities

    def library_projection_attrs(self):
        return {
            "name": 1,
            "libtype": 1,
            "developers": 1,
        }

    async def close(self):
        logging.info("DBService#close()")
        if self.using_nosql():
            await self.nosql_svc.close()
        else:
            self.vcore_svc.close()
