import asyncio
import logging

from abc import ABC, abstractmethod

from src.services.ai_conversation import AiConversation
from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.cosmos_vcore_service import CosmosVCoreService

# This is the abstract superclass for classes with connections
# to multiple databases, such as Cosmos DB Mongo vCore and Cosmos DB NoSQL.
# These include classes DBService and EntitiesService.
# Chris Joakim, Microsoft


class BaseDBService:

    def __init__(self, override_graph_source=None):
        """Constructor method."""
        try:
            self.graph_source = str(ConfigService.graph_source())
            if override_graph_source is not None:
                self.graph_source = (
                    override_graph_source  # used for testing & unit tests
                )
            self.vcore_svc = None
            self.nosql_svc = None
            self.nosql_dbproxy = None
            self.nosql_ctrproxy = None
            self.dbname = ConfigService.graph_source_db()
            self.graph_container = ConfigService.graph_source_container()
            self.conversations_container = ConfigService.conversations_container()
            logging.info(
                "BaseDBService constructor complete; source: {}".format(
                    self.graph_source
                )
            )
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    async def initialize(self):
        """This method should be called immediately after the constructor."""
        if self.graph_source == "cosmos_nosql":
            await self.initialize_cosmos_nosql()
        else:
            await self.initialize_cosmos_vcore()

    async def initialize_cosmos_nosql(self):
        opts = dict()
        opts["enable_diagnostics_logging"] = False
        self.nosql_svc = CosmosNoSQLService(opts)
        await self.nosql_svc.initialize()
        self.nosql_dbproxy = self.nosql_svc.set_db(self.dbname)
        self.nosql_ctrproxy = self.nosql_svc.set_container(self.graph_container)

    async def initialize_cosmos_vcore(self):
        opts = dict()
        opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
        self.vcore_svc = CosmosVCoreService(opts)
        self.vcore_svc.set_db(self.dbname)
        self.vcore_svc.set_coll(self.graph_container)

    def using_nosql(self) -> str:
        return "cosmos_nosql" in self.graph_source

    def using_vcore(self) -> str:
        return "cosmos_vcore" in self.graph_source

    @abstractmethod
    async def close(self):
        """Subclasses must implement this method."""
        pass

    def set_db(self, dbname):
        logging.info("DBService#set_db: {}".format(dbname))
        self.dbname = dbname
        if self.graph_source == "cosmos_nosql":
            self.nosql_svc.set_db(dbname)
        else:
            self.vcore_svc.set_db(dbname)

    def set_container(self, cname):
        logging.info("DBService#set_container: {}".format(cname))
        self.cname = cname
        if self.graph_source == "cosmos_nosql":
            self.nosql_svc.set_container(cname)
        else:
            self.vcore_svc.set_coll(cname)

    def set_coll(self, cname):
        """Alias for the above method"""
        self.set_container(cname)
