import datetime
import json
import logging
import time
import traceback
import uuid

import certifi

from pymongo import MongoClient
from pymongo import InsertOne, DeleteMany, ReplaceOne, UpdateOne
from bson.objectid import ObjectId

from src.services.config_service import ConfigService
from src.services.ai_conversation import AiConversation
from src.models.webservice_models import AiConvFeedbackModel
from src.models.webservice_models import DocumentsVSResultsModel

# Instances of this class are used to access a Cosmos DB Mongo vCore
# account/database.
# Chris Joakim, Microsoft

logging.getLogger("pymongo").setLevel(logging.WARNING)


class CosmosVCoreService:
    def __init__(self, opts: dict):
        self._opts = opts
        self._db = None
        self._coll = None
        try:
            self._client = MongoClient(opts["conn_string"], tlsCAFile=certifi.where())
            logging.info("CosmosVCoreService - client initialized")
        except Exception as e:
            logging.critical(str(e))
            print(traceback.format_exc())

    def close(self) -> None:
        try:
            if self._client is not None:
                self._client.close()
                logging.info("CosmosVCoreService - client closed")
        except Exception as excp:
            logging.critical(str(excp))
            print(traceback.format_exc())

    def list_databases(self) -> list[str]:
        """Return the list of database names in the account."""
        try:
            return sorted(self._client.list_database_names())
        except Exception as excp:
            logging.critical(str(excp))
            print(traceback.format_exc())
            return None

    def get_client(self):
        """Return the pymongo client object."""
        return self._client

    def create_database(self, dbname):
        """Create a database with the given name."""
        return self._client[dbname]

    def delete_database(self, dbname):
        """Delete a database with the given name."""
        if dbname in "admin,local,config".split(","):
            return
        self._client.drop_database(dbname)

    def delete_container(self, cname):
        """Delete a container with the given name."""
        self._db.drop_collection(cname)

    def list_collections(self):
        """Return the list of collection names in the current database."""
        return self._db.list_collection_names(filter={"type": "collection"})

    def set_db(self, dbname):
        """Set the current database to the given name."""
        self._db = self._client[dbname]
        return self._db

    def get_db(self):
        return self._db

    def set_coll(self, collname):
        """Set the current collection to the given name."""
        try:
            self._coll = self._db[collname]
            return self._coll
        except Exception as excp:
            logging.critical(str(excp))
            print(traceback.format_exc())
            return None

    def set_container(self, collname):
        """alias for the set_coll method"""
        return self.set_coll(collname)

    def get_coll(self):
        return self._coll

    def get_container(self):
        """alias for the get_coll method"""
        return self.get_coll()

    def command_db_stats(self):
        """Execute the 'dbstats' command and return the results."""
        return self._db.command({"dbstats": 1})

    def command_coll_stats(self, cname):
        """Execute the 'collStats' command and return the results."""
        return self._db.command("collStats", cname)

    def command_list_commands(self):
        """Execute the 'listCommands' command and return the results."""
        return self._db.command("listCommands")

    def command_sharding_status(self):
        """Execute the 'printShardingStatus' command and return the results."""
        return self._db.command("printShardingStatus")

    def get_shards(self):
        """Return the list of shards in the cluster per the config database."""
        self.set_db("config")
        return self._db.shards.find()

    def get_shard_info(self) -> dict:
        """Return a dict of shard info."""
        shard_dict = {}
        for shard in self._client.config.shards.find():
            shard_name = shard.get("_id")
            shard_dict[shard_name] = shard
        return shard_dict

    def create_coll(self, cname):
        """Create a collection with the given name in the current database."""
        return self._db[cname]

    def create_simple_index(self, attr_name, unique=False):
        # See https://pymongo.readthedocs.io/en/stable/tutorial.html#indexing
        return self._coll.create_index([(attr_name, 1)], unique=unique)

    def get_coll_indexes(self, collname) -> list | None:
        """Return the list of indexes for the given collection."""
        try:
            self.set_coll(collname)
            return self._coll.index_information()
        except Exception as excp:
            logging.critical(str(excp))
            print(traceback.format_exc())
            return None

    # crud methods below, metadata methods above

    def insert_doc(self, doc):
        """Insert a document into the current collection and return the result."""
        return self._coll.insert_one(doc)

    def replace_one(self, query_spec, doc):
        """Replace or upsert the given document per the query spec and return the result."""
        return self._coll.replace_one(query_spec, doc, True)

    def find_one(self, query_spec):
        """
        Execute a find_one query in the current collection and return the result.
        """
        return self._coll.find_one(query_spec)

    def find(self, query_spec):
        """
        Execute a find query in the current collection and return the results.
        """
        return self._coll.find(query_spec)

    def find_by_id(self, id_str: str):
        """
        Execute a find_one query in the current collection, with the given id
        as a string, and return the results.
        """
        return self._coll.find_one({"_id": ObjectId(id_str)})

    def aggregate(self, pipeline):
        """Execute an aggregation pipeline in the current collection and return the results."""
        # https://pymongo.readthedocs.io/en/stable/examples/aggregation.html
        # https://learn.microsoft.com/en-us/azure/cosmos-db/mongodb/vcore/vector-search
        return self._coll.aggregate(pipeline)

    def delete_by_id(self, id_str: str):
        """Delete a document from the current collection by id and return the result."""
        return self._coll.delete_one({"_id": ObjectId(id_str)})

    def delete_one(self, query_spec):
        """Delete a document from the current collection and return the result."""
        return self._coll.delete_one(query_spec)

    def delete_many(self, query_spec):
        """Delete documents from the current collection and return the result."""
        return self._coll.delete_many(query_spec)

    def update_one(self, filter, update, upsert):
        """Update a document in the current collection and return the result."""
        return self._coll.update_one(filter, update, upsert)

    def update_many(self, filter, update, upsert):
        """Update documents in the current collection and return the result."""
        return self._coll.update_many(filter, update, upsert)

    def bulk_write(self, operations_list: list):
        """
        Execute a list of bulk operations that may include these types:
        InsertOne, DeleteMany, ReplaceOne, UpdateOne
        """
        return self._coll.bulk_write(operations_list)

    def count_docs(self, query_spec):
        """
        Return the number of documents in the current collection
        that match the query spec.
        """
        return self._coll.count_documents(query_spec)

    def load_conversation(self, conversation_id: str) -> AiConversation | None:
        try:
            if conversation_id is None:
                return AiConversation(None)
            if len(conversation_id.strip()) == 0:
                return AiConversation(None)

            self.set_coll(ConfigService.conversations_container())
            spec = dict()
            spec["conversation_id"] = conversation_id
            doc = self.find_one(spec)
            return AiConversation(doc)
        except Exception as e:
            logging.critical(
                "Exception in CosmosVCoreService#load_conversation id: {} -> {}".format(
                    conversation_id, str(e)
                )
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return AiConversation(None)

    def save_conversation(self, conv: AiConversation) -> bool:
        try:
            self.set_coll(ConfigService.conversations_container())
            conv.set_updated_at()
            doc = json.loads(conv.serialize())
            spec = dict()
            spec["conversation_id"] = doc["conversation_id"]
            self.replace_one(spec, doc)
            return True
        except Exception as e:
            logging.critical(
                "Exception in CosmosVCoreService#save_conversation id: {} -> {}".format(
                    conv, str(e)
                )
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return False

    def save_feedback(self, feedback: AiConvFeedbackModel) -> bool:
        try:
            self.set_coll(ConfigService.feedback_container())
            created_at = time.time()
            doc = dict()
            doc["_id"] = str(uuid.uuid4())
            doc["created_at"] = created_at
            doc["created_date"] = str(datetime.datetime.fromtimestamp(created_at))
            doc["conversation_id"] = feedback.conversation_id
            doc["feedback_last_question"] = feedback.feedback_last_question
            doc["feedback_user_feedback"] = feedback.feedback_user_feedback
            self.insert_doc(doc)
            return True
        except Exception as e:
            logging.critical(
                "Exception in CosmosVCoreService#save_feedback: {} -> {}".format(
                    feedback, str(e)
                )
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return False

    def search_documents_like_library(
        self, libtype, name, embeddings_attr="embedding", k=10
    ) -> DocumentsVSResultsModel:
        """
        Execute a vector search based on looking up the given library type and name.
        First lookup the given libtype and libname, get its' embeddings, then
        use that as the search vector for a vector search.
        The arg k refers to the max number of documents to return.
        """
        t1 = time.perf_counter()
        output_doc = {}
        output_doc["libtype"] = libtype
        output_doc["name"] = name
        output_doc["count"] = 0
        output_doc["doc"] = None
        output_doc["results"] = list()
        output_doc["error"] = None
        output_doc["elapsed"] = "-1.0"
        try:
            self.set_coll(ConfigService.graph_source_container())
            doc = self.find_one({"libtype": libtype, "name": name})
            if doc is None:
                output_doc["error"] = (
                    f"document not found for libtype: {libtype}, name: {name}"
                )
            else:
                self.stringify_doc_id(doc)
                output_doc["doc"] = doc
                vector = doc[embeddings_attr]
                vs_result = self.vector_search(vector, embeddings_attr, k)
                output_doc["results"] = vs_result["results"]
                output_doc["error"] = vs_result["error"]
                output_doc["elapsed"] = vs_result["elapsed"]
        except Exception as e:
            output_doc["error"] = str(e)
            print(str(e))
            print(traceback.format_exc())

        output_doc["count"] = len(output_doc["results"])
        output_doc["elapsed"] = time.perf_counter() - t1
        return output_doc

    def vector_search(self, vector, embeddings_attr="embedding", k=10) -> dict:
        """
        Execute a vector search using the given vector and return a results dict
        """
        vs_result = dict()
        vs_result["vector"] = vector
        vs_result["embeddings_attr"] = embeddings_attr
        vs_result["k"] = k
        vs_result["results"] = list()
        vs_result["error"] = None
        t1 = time.perf_counter()
        try:
            # construct a Mongo aggregation pipeline JSON structure:
            cosmosSearch = dict()
            cosmosSearch["vector"] = vector
            cosmosSearch["path"] = embeddings_attr
            cosmosSearch["k"] = k
            search = dict()
            search["cosmosSearch"] = cosmosSearch
            search["returnStoredSource"] = True
            stage = dict()
            stage["$search"] = search
            pipeline = [stage]
            # The aggregation pipeline should look like this:
            # [
            #   {
            #     "$search": {
            #       "cosmosSearch": {
            #         "vector": [
            #           0.0030290345,
            #           -0.00155827,
            #           ...
            #           -0.03667151,
            #           -0.020987844
            #         ],
            #         "path": "embeddings",
            #         "k": 10
            #       },
            #       "returnStoredSource": true
            #     }
            #   }
            # ]

            # execute the aggregation pipeline
            # results is a pymongo.command_cursor.CommandCursor object to iterate
            self.set_coll(ConfigService.graph_source_container())
            cursor = self.aggregate(pipeline)
            for result_doc in cursor:
                self.stringify_doc_id(result_doc)
                vs_result["results"].append(result_doc)
        except Exception as e:
            vs_result["error"] = str(e)
            print(str(e))
            print(traceback.format_exc())
        vs_result["count"] = len(vs_result["results"])
        vs_result["elapsed"] = time.perf_counter() - t1
        return vs_result

    def stringify_doc_id(self, doc):
        """
        Convert the _id attribute of the given vcore document to a string
        because an ObjectId is not JSON serializable
        """
        try:
            doc["_id"] = str(doc["_id"])
        except:
            pass
