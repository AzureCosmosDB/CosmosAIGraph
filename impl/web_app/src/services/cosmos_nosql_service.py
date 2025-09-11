import json
import logging
import traceback
import uuid

from azure.cosmos.aio import CosmosClient
from azure.cosmos.aio._database import DatabaseProxy
from azure.cosmos.aio._container import ContainerProxy
from azure.identity.aio import DefaultAzureCredential

# from azure.cosmos import CosmosClient
from azure.identity import ClientSecretCredential

from src.models.webservice_models import AiConvFeedbackModel
from src.services.ai_conversation import AiConversation
from src.services.config_service import ConfigService

from src.util.cosmos_doc_filter import CosmosDocFilter


# Instances of this class are used to access a Cosmos DB NoSQL
# account/database using the asynchronous SDK methods.
# This module uses the 'azure-cosmos' SDK on PyPi.org, currently version 4.7.0.
# See https://pypi.org/project/azure-cosmos/
# See https://learn.microsoft.com/en-us/python/api/overview/azure/cosmos-readme?view=azure-python
# See https://azuresdkdocs.blob.core.windows.net/$web/python/azure-cosmos/4.7.0/azure.cosmos.html
# See https://github.com/Azure/azure-sdk-for-python/tree/azure-cosmos_4.7.0/sdk/cosmos/azure-cosmos/samples
# See https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search
#
# Chris Joakim, Microsoft, 2025

# azure_logger can be used to set the verbosity of the Azure and Cosmos SDK logging
azure_logger = logging.getLogger("azure")
azure_logger.setLevel(logging.WARNING)


LAST_REQUEST_CHARGE_HEADER = "x-ms-request-charge"


class CosmosNoSQLService:

    def __init__(self, opts={}):
        # https://www.slingacademy.com/article/python-defining-a-class-with-an-async-constructor/
        # https://stackoverflow.com/questions/33128325/how-to-set-class-attribute-with-await-in-init
        self._opts = opts
        self._dbname: str | None = None
        self._dbproxy: DatabaseProxy | None = None
        self._ctrproxy: ContainerProxy | None = None
        self._cname: str | None = None
        self._client: CosmosClient | None = None
        logging.info("CosmosNoSQLService - constructor")

    async def initialize(self):
        """This method should be called after the above constructor."""
        auth_mechanism = ConfigService.cosmosdb_nosql_auth_mechanism()
        logging.info("CosmosNoSQLService#auth_mechanism: %s", auth_mechanism)

        try:
            uri = ConfigService.cosmosdb_nosql_uri()
            if auth_mechanism == "key":
                logging.info("Initializing CosmosClient with key authentication.")
                key = ConfigService.cosmosdb_nosql_key()
                self._client = CosmosClient(uri, credential=key)
            else:
                logging.info("Initializing CosmosClient with DefaultAzureCredential.")
                credential = DefaultAzureCredential()
                self._client = CosmosClient(uri, credential=credential)

            logging.info("CosmosClient initialized successfully.")
            self.set_db(ConfigService.graph_source_db())
        except Exception as e:
            logging.error("Failed to initialize CosmosNoSQLService: %s", e)
            raise RuntimeError("CosmosNoSQLService initialization failed.") from e

    async def close(self):
        if self._client is not None:
            await self._client.close()
            logging.info("CosmosNoSQLService - client closed")

    async def list_databases(self):
        """Return the list of database names in the account."""
        self.validate_client()
        dblist = list()
        async for db in self._client.list_databases():
            dblist.append(db["id"])
        return dblist

    def validate_client(self):
        assert self._client is not None, "CosmosClient is not initialized. Call 'initialize' first."

    def validate_dbproxy(self):
        assert self._dbproxy is not None, "Database proxy is not set. Call 'set_db' first."

    def validate_ctrproxy(self):
        assert self._ctrproxy is not None, "Container proxy is not set. Call 'set_container' first."

    def set_db(self, dbname: str) -> DatabaseProxy:
        """Set the current database to the given dbname."""
        self.validate_client()
        try:
            self._dbname = dbname
            self._dbproxy = self._client.get_database_client(dbname)
        except Exception as e:
            logging.critical("Failed to set database: %s", e)
            raise
        return self._dbproxy  # <class 'azure.cosmos.aio._database.DatabaseProxy'>

    def get_current_cname(self):
        return self._cname

    def set_container(self, cname: str) -> ContainerProxy:
        """Set the current container in the current database to the given cname."""
        self.validate_dbproxy()
        if cname is None:
            raise ValueError("Container name cannot be None.")
        try:
            self._cname = cname
            self._ctrproxy = self._dbproxy.get_container_client(cname)
        except Exception as e:
            logging.critical("Failed to set container: %s", e)
            raise
        return self._ctrproxy  # <class 'azure.cosmos.aio._container.ContainerProxy'>

    async def list_containers(self):
        """Return the list of container names in the current database."""
        self.validate_dbproxy()
        container_list = list()
        async for container in self._dbproxy.list_containers():
            container_list.append(container["id"])
        return container_list

    async def point_read(self, id: str, pk: str):
        self.validate_ctrproxy()
        return await self._ctrproxy.read_item(item=id, partition_key=pk)

    async def create_item(self, doc: dict):
        self.validate_ctrproxy()
        return await self._ctrproxy.create_item(body=doc)

    async def upsert_item(self, doc: dict):
        self.validate_ctrproxy()
        return await self._ctrproxy.upsert_item(body=doc)

    async def delete_item(self, id: str, pk: str):
        self.validate_ctrproxy()
        return await self._ctrproxy.delete_item(item=id, partition_key=pk)

    # https://github.com/Azure/azure-sdk-for-python/blob/azure-cosmos_4.7.0/sdk/cosmos/azure-cosmos/samples/document_management_async.py

    async def execute_item_batch(self, item_operations: list, pk: str):
        self.validate_ctrproxy()
        return await self._ctrproxy.execute_item_batch(
            batch_operations=item_operations, partition_key=pk
        )

    async def query_items(self, sql: str, cross_partition: bool = False, pk: str | None = None, max_items: int = 100):
        self.validate_ctrproxy()
        parameters_list, results_list = list(), list()
        parameters_list.append(
            {"name": "@enable_cross_partition_query", "value": cross_partition}
        )
        if pk is not None:
            parameters_list.append({"name": "@partition_key", "value": pk})
        query_results = self._ctrproxy.query_items(
            query=sql, parameters=parameters_list
        )
        async for item in query_results:
            results_list.append(item)
        return results_list

    async def parameterized_query(
        self,
        sql_template,
        sql_parameters,
        cross_partition=False,
        pk=None,
        max_items=100,
    ):
        parameters_list, results_list = list(), list()
        parameters_list.append(
            {"name": "@enable_cross_partition_query", "value": cross_partition}
        )
        parameters_list.append({"name": "@max_item_count", "value": max_items})
        if pk is not None:
            parameters_list.append({"name": "@partition_key", "value": pk})
        if sql_parameters is not None:
            for sql_param in sql_parameters:
                parameters_list.append(sql_param)
        query_results = self._ctrproxy.query_items(
            query=sql_template, parameters=parameters_list
        )
        async for item in query_results:
            results_list.append(item)
        return results_list

    async def get_documents_by_name(self, libnames: list, additional_attrs: list = list()):
        quoted_names, docs = list(), list()
        for libname in libnames:
            quoted_names.append("'{}'".format(libname))
        self.set_container(ConfigService.graph_source_container())
        sql = "select * from c where c.name in ({})".format(",".join(quoted_names))
        items_paged = self._ctrproxy.query_items(query=sql, parameters=[])
        async for item in items_paged:
            cdf = CosmosDocFilter(item)
            docs.append(cdf.filter_library(additional_attrs))
            #docs.append(item)
        return docs

    async def save_conversation(self, conv: AiConversation | None):
        resp = None
        if conv is not None:
            logging.info(f"Saving conversation with completions: {conv.completions}")
            self.set_container(ConfigService.conversations_container())

            # Load existing conversation to merge completions
            existing_conv = await self.load_conversation(conv.conversation_id)
            if existing_conv:
                logging.info("Merging completions with existing conversation.")
                logging.info(f"BEFORE MERGE: incoming={len(conv.completions)}, existing={len(existing_conv.completions)}")
                
                # Create a comprehensive list of all completions
                all_completions = existing_conv.completions.copy()  # Start with existing
                
                # Add new completions that don't already exist
                existing_ids = {c.get("completion_id") for c in existing_conv.completions}
                new_completions = [c for c in conv.completions if c.get("completion_id") not in existing_ids]
                
                logging.info(f"MERGE FILTERING: {len(new_completions)} new completions after dedup")
                for i, c in enumerate(new_completions):
                    logging.info(f"  New completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")
                
                # Append new completions to the existing list
                all_completions.extend(new_completions)
                
                # Sort by index to maintain proper order
                all_completions.sort(key=lambda x: x.get('index', 0))
                
                # Update the conversation's completions
                conv.completions = all_completions
                
                logging.info(f"AFTER MERGE: total={len(conv.completions)} completions")
                for i, c in enumerate(conv.completions):
                    logging.info(f"  Final completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")

                # Debugging: Log the state of completions after merging
                logging.debug("Completions after merging:")
                for c in conv.completions:
                    logging.debug(f"Completion ID: {c.get('completion_id')}, Index: {c.get('index')}")
            else:
                logging.info("No existing conversation found - saving new conversation.")

            # Debugging: Log completions before saving
            logging.debug("Completions before saving:")
            for c in conv.completions:
                logging.debug(f"Completion ID: {c.get('completion_id')}, Index: {c.get('index')}, Content: {c.get('content')}")

            # Debugging: Log completions after merging
            logging.debug("Completions after merging:")
            for c in conv.completions:
                logging.debug(f"Completion ID: {c.get('completion_id')}, Index: {c.get('index')}, Content: {c.get('content')}")

            doc = json.loads(conv.serialize())
            print(f"[DEBUG] SAVING TO DB: {len(doc.get('completions', []))} completions")
            for i, c in enumerate(doc.get('completions', [])):
                print(f"[DEBUG]   DB Save completion {i}: Index={c.get('index')}, User={c.get('user_text')}")
            resp = await self.upsert_item(doc)
        return resp

    async def load_conversation(self, conv_id: str | None) -> AiConversation | None:
        conv = None
        if conv_id is not None:
            self.set_container(ConfigService.conversations_container())
            sql_params = [dict(name="@conversation_id", value=conv_id)]
            sql = "select * from c where c.conversation_id = @conversation_id offset 0 limit 1"
            items = await self.parameterized_query(sql, sql_params, True)
            print(f"[DEBUG] DB QUERY returned {len(items)} items for conv_id={conv_id}")
            for doc in items:
                completions = doc.get("completions", [])
                print(f"[DEBUG] RAW DB DOC has {len(completions)} completions")
                for i, c in enumerate(completions):
                    print(f"[DEBUG]   Raw DB completion {i}: Index={c.get('index')}, User={c.get('user_text')}")
                conv = AiConversation(doc)
                # DEBUGGING: Log what we loaded from database
                logging.info(f"LOADED FROM DB: {len(completions)} completions for conv_id={conv_id}")
                for i, c in enumerate(completions):
                    logging.info(f"  DB completion {i}: ID={c.get('completion_id')}, Index={c.get('index')}, User={c.get('user_text')}")
        return conv

    async def find_library(self, name: str | None) -> dict | None:
        lib = None
        if name is not None:
            self.set_container(ConfigService.graph_source_container())
            sql_params = [dict(name="@name", value=name)]
            sql = "select * from c where c.name = @name offset 0 limit 1"
            items = await self.parameterized_query(sql, sql_params, True)
            for doc in items:
                cdf = CosmosDocFilter(doc)
                lib = cdf.filter_library()
        return lib

    async def vector_search(self, embedding_value=None, search_text=None, search_method="vector", embedding_attr="embedding", limit=4):
        """
        Perform search using different methods:
        - vector: Traditional vector similarity search
        - fulltext: Full-text search using FullTextScore
        - rrf: Reciprocal Rank Fusion combining both vector and full-text search
        """
        if search_method == "fulltext":
            return await self.fulltext_search(search_text, limit)
        elif search_method == "rrf":
            return await self.rrf_search(embedding_value, search_text, embedding_attr, limit)
        else:
            # Default vector search
            sql = self.vector_search_sql(embedding_value, embedding_attr, limit)
            docs = list()
            items_paged = self._ctrproxy.query_items(query=sql, parameters=[])
            async for item in items_paged:
                cdf = CosmosDocFilter(item)
                docs.append(cdf.filter_out_embedding(embedding_attr))
            return docs

    async def fulltext_search(self, search_text, limit=4):
        """
        Perform full-text search using FullTextScore function
        Pass all tokenized words as a single string separated by commas for FullTextScore.
        """
        if not search_text:
            return []

        # Tokenize the input text into words longer than one character
        tokens = [word for word in search_text.split() if len(word) > 1]
        if not tokens:
            return []

        # Combine tokens into a single string separated by commas
        search_expr = ','.join(f'"{token}"' for token in tokens)

        # Simplified query using just the description field
        sql = f"""
        SELECT TOP {limit} * 
        FROM c 
        ORDER BY RANK FullTextScore(c.description, {search_expr})
        """

        logging.debug(f"Full-text search SQL: {sql}")
        docs = list()
        try:
            items_paged = self._ctrproxy.query_items(query=sql, parameters=[])
            async for item in items_paged:
                cdf = CosmosDocFilter(item)
                docs.append(cdf.filter_out_embedding("embedding"))
        except Exception as e:
            # If description field doesn't support FullTextScore, try summary field
            logging.error(f"Full-text search on description failed: {e}")
            try:
                sql = f"""
                SELECT TOP {limit} * 
                FROM c 
                ORDER BY RANK FullTextScore(c.summary, {search_expr})
                """
                logging.debug(f"Full-text search SQL: {sql}")
                items_paged = self._ctrproxy.query_items(query=sql, parameters=[])
                async for item in items_paged:
                    cdf = CosmosDocFilter(item)
                    docs.append(cdf.filter_out_embedding("embedding"))
            except Exception as e2:
                # If FullTextScore is not supported, fall back to CONTAINS
                logging.error(f"Full-text search on summary also failed: {e2}")
                docs = await self._fallback_text_search(search_text, limit)

        return docs
    
    async def _fallback_text_search(self, search_text, limit=4):
        """
        Fallback text search using CONTAINS when FullTextScore is not available
        Uses a parameterized query to avoid malformed SQL when the input contains quotes
        """
        docs = list()
        try:
            # Use parameterized CONTAINS for basic text search to avoid injection/errors
            sql = f"""
            SELECT TOP {limit} *
            FROM c 
            WHERE CONTAINS(c.description, @search_text) OR 
                  CONTAINS(c.summary, @search_text) OR 
                  CONTAINS(c.name, @search_text)
            """

            params = [dict(name="@search_text", value=search_text)]
            items_paged = self._ctrproxy.query_items(query=sql, parameters=params)
            async for item in items_paged:
                cdf = CosmosDocFilter(item)
                docs.append(cdf.filter_out_embedding("embedding"))
        except Exception as e:
            logging.error(f"Fallback text search also failed: {e}")
            logging.debug(traceback.format_exc())
        
        return docs

    async def rrf_search(self, embedding_value, search_text, embedding_attr="embedding", limit=10):
        """
        Perform RRF (Reciprocal Rank Fusion) search combining vector and full-text search
        Pass all tokenized words as a single string separated by commas for FullTextScore.
        """
        if not embedding_value or not search_text:
            return []

        # Tokenize the input text into words longer than one character
        tokens = [word for word in search_text.split() if len(word) > 1]
        if not tokens:
            return []

        # Combine tokens into a single string separated by commas
        search_expr = ','.join(f'"{token}"' for token in tokens)

        docs = list()
        try:
            # Build the RRF query using FullTextScore and VectorDistance; use proper RANK(...) syntax
            sql = f"""
            SELECT TOP {limit} *
            FROM c
            ORDER BY RANK(RRF(
                FullTextScore(c.description, {search_expr}), 
                VectorDistance(c.{embedding_attr}, {str(embedding_value)})
            ))
            """

            items_paged = self._ctrproxy.query_items(query=sql, parameters=[])
            async for item in items_paged:
                cdf = CosmosDocFilter(item)
                docs.append(cdf.filter_out_embedding(embedding_attr))

        except Exception as e:
            logging.error(f"RRF search with FullTextScore failed: {e}")
            # Fall back to vector search only
            try:
                sql = f"""
                SELECT TOP {limit} *
                FROM c
                ORDER BY VectorDistance(c.{embedding_attr}, {str(embedding_value)})
                """
                items_paged = self._ctrproxy.query_items(query=sql, parameters=[])
                async for item in items_paged:
                    cdf = CosmosDocFilter(item)
                    docs.append(cdf.filter_out_embedding(embedding_attr))
            except Exception as e2:
                logging.error(f"Fallback vector search in RRF also failed: {e2}")

        return docs

    def vector_search_sql(self, embedding_value, embedding_attr="embedding", limit=4):
        parts = list()
        parts.append("SELECT TOP {}".format(limit))
        parts.append(
            #"c, VectorDistance(c.{}, {}) AS score".format(
            #    embedding_attr, str(embedding_value)
            #)
            "*"
        )
        parts.append(
            "FROM c ORDER BY VectorDistance(c.{}, {})".format(
                embedding_attr, str(embedding_value)
            )
        )
        return " ".join(parts).strip()
        # See https://github.com/AzureCosmosDB/Azure-OpenAI-Python-Developer-Guide/blob/main/diskann/09_Vector_Search_Cosmos_DB/README.md
        # query=f"""SELECT TOP @num_results itm.id, VectorDistance(itm.{vector_field_name}, @embedding) AS SimilarityScore
        #         FROM itm
        #         ORDER BY VectorDistance(itm.{vector_field_name}, @embedding)
        #         """,

    async def save_feedback(self, feedback: AiConvFeedbackModel) -> bool:
        curr_container = self._cname
        result = False
        try:
            self.set_container(ConfigService.feedback_container())
            doc = dict()
            doc["id"] = str(uuid.uuid4())
            doc["conversation_id"] = feedback.conversation_id
            doc["last_question"] = feedback.feedback_last_question
            doc["user"] = feedback.feedback_user_feedback
            logging.info(
                "CosmosNoSQLService#save_feedback: {} -> {}".format(
                    doc, ConfigService.feedback_container()
                )
            )
            await self.create_item(doc)
            result = True
        except Exception as e:
            logging.critical(
                "Exception in CosmosNoSQLService#save_feedback: {} -> {}".format(
                    feedback, str(e)
                )
            )
            logging.exception(e, stack_info=True, exc_info=True)
        finally:
            self.set_container(curr_container)
        return result

    def last_response_headers(self):
        """
        The headers are an instance of class CIMultiDict.
        You can lookup the value of a header by name, like this:
            nosql_svc.last_response_headers()['x-ms-item-count']
        You can also iterate over the headers, like this:
            for two_tup in nosql_svc.last_response_headers().items():
                name, value = two_tup[0], two_tup[1]
        """
        try:
            return self._ctrproxy.client_connection.last_response_headers
        except:
            return None

    def last_request_charge(self):
        try:
            return float(
                self._ctrproxy.client_connection.last_response_headers[
                    LAST_REQUEST_CHARGE_HEADER
                ]
            )
        except:
            return -1.0

    def last_response_header(self, header):
        """
        Return the value of the given header name from the last response, or None.
        The following are some example header names and their values:

        Content-Length -> 62
        Content-Type -> application/json
        Date -> Wed, 21 Aug 2024 10:27:27 GMT
        Server -> Compute
        lsn -> 15386
        x-ms-activity-id -> 61171e8e-83cf-42c3-bf2b-86befec450e6
        x-ms-alt-content-path -> dbs/dev/colls/test
        x-ms-content-path -> hy5tAOrJ4DU=
        x-ms-cosmos-is-partition-key-delete-pending -> false
        x-ms-cosmos-llsn -> 15386
        x-ms-cosmos-physical-partition-id -> 0
        x-ms-cosmos-query-execution-info -> {"reverseRidEnabled":false,"reverseIndexScan":false}
        x-ms-documentdb-partitionkeyrangeid -> 0
        x-ms-gatewayversion -> 2.0.0
        x-ms-global-Committed-lsn -> 15386
        x-ms-item-count -> 1
        x-ms-item-count: 1
        x-ms-last-state-change-utc -> Tue, 20 Aug 2024 20:47:21.072 GMT
        x-ms-number-of-read-regions -> 0
        x-ms-request-charge -> 2.89
        x-ms-request-duration-ms -> 1.207
        x-ms-resource-quota -> documentSize=51200;documentsSize=52428800;documentsCount=-1;collectionSize=52428800;
        x-ms-resource-usage -> documentSize=0;documentsSize=382;documentsCount=63;collectionSize=398;
        x-ms-schemaversion -> 1.18
        x-ms-serviceversion -> version=2.14.0.0
        x-ms-session-token -> 0:-1#15386
        x-ms-throttle-retry-count -> 0
        x-ms-throttle-retry-wait-time-ms -> 0
        x-ms-transport-request-id -> 5133
        x-ms-xp-role -> 2
        """
        try:
            return self._ctrproxy.client_connection.last_response_headers[header]
        except:
            return None
