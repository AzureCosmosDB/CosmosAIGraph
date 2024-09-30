import logging

from src.services.config_service import ConfigService
from src.services.cosmos_vcore_service import CosmosVCoreService

# Instances of this class are use to read and write to a cache.
# The current implementation uses Cosmos DB Mongo vCore as the
# underlying datastore.
# Chris Joakim, Microsoft


class CacheService:
    def __init__(self, opts={}):
        """the given opts are for unit-testing purposes"""
        try:
            self.conn_string = ConfigService.mongo_vcore_conn_str()
            opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
            self.vcore = CosmosVCoreService(opts)
            self.dbname = ConfigService.graph_source_db()

            # The container name is typically 'cache', but it can be overridden
            # for unit testing purposes.
            self.cname = None
            if "container" in opts.keys():
                if "environment" in opts.keys():
                    if opts["environment"] == "unit_testing":
                        self.cname = opts["container"]
            if self.cname is None:
                self.cname = "cache"

            self.vcore.set_db(self.dbname)
            self.vcore.set_coll(self.cname)
            logging.info("CacheService init complete")
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    def get(self, key) -> dict | None:
        # mongosh example query: db.cache.find({'cache_key': 'pypi_flask_1'})
        try:
            if key is not None:
                filter = {"cache_key": key}
                return self.vcore.find_one(filter)
            else:
                return None
        except Exception as e:
            logging.critical("Exception in CacheService.get()")
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    def set(self, key, doc):
        try:
            if doc is not None:
                if self.is_key_value_valid(key):
                    criteria = {"cache_key": key}
                    doc["cache_key"] = key
                    return self.vcore.replace_one(criteria, doc)
            return None
        except Exception as e:
            logging.critical("Exception in CacheService.get()")
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    def count_docs(self):
        return self.vcore.count_docs({})

    def clear(self):
        for n in range(100):
            try:
                result = self.vcore.delete_many({})
                logging.info("CacheService#clear: {}".format(result))
                if result.deleted_count == 0:
                    return
            except Exception as e:
                logging.critical("Exception in CacheService.get()")
                logging.exception(e, stack_info=True, exc_info=True)

    def is_key_value_valid(self, key: str) -> bool:
        if key is None:
            return False
        if len(str(key)) < 1:
            return False
        return True
