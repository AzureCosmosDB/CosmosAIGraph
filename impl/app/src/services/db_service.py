import asyncio
import json
import logging
import traceback

from typing import List

from src.models.webservice_models import AiConvFeedbackModel

from src.services.ai_conversation import AiConversation
from src.services.base_db_service import BaseDBService
from src.services.config_service import ConfigService

# Instances of this class are a wrapper for one of several possible underlying databases,
# including:
# 1) Cosmos DB Mongo vCore API
# 2) Cosmos DB NoSQL API
# 3) Azure PostgreSQL (future implementation)
# All methods are asynchronous for consistency between NoSQL (async) and vCore (sync).
# Chris Joakim, Microsoft


class DBService(BaseDBService):

    def __init__(self, override_graph_source=None):
        """Constructor method; call initialize() immediately after this."""
        try:
            super().__init__(override_graph_source)  # call BaseDBService constructor
            logging.info(
                "DBService constructor complete; source: {}".format(self.graph_source)
            )
        except Exception as e:
            logging.critical((str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    async def initialize(self):
        """This method should be called immediately after the constructor."""
        if self.using_nosql():
            await self.initialize_cosmos_nosql()
        else:
            await self.initialize_cosmos_vcore()
        logging.info("DBService initialize() complete")

    async def save_conversation(self, conv: AiConversation | None):
        """
        Example mongosh query:
        db.conversations.findOne({"conversation_id": "09d2aa6a-2f0e-4d8c-9a51-d393fd42c19b"})
        """
        if conv is not None:
            conv_id = conv.get_conversation_id()
            logging.info(
                "DBService#save_conversation - {} {}".format(self.graph_source, conv_id)
            )
            if self.using_nosql():
                self.set_container(self.conversations_container)
                doc = json.loads(conv.serialize())
                resp = await self.nosql_svc.upsert_item(doc)
            else:
                self.set_container(self.conversations_container)
                self.vcore_svc.save_conversation(conv)

    async def load_conversation(
        self, conversation_id: str | None
    ) -> AiConversation | None:
        """
        Example mongosh query:
        db.conversations.findOne({"conversation_id": "09d2aa6a-2f0e-4d8c-9a51-d393fd42c19b"})
        """
        logging.info("DBService#load_conversation - {}".format(conversation_id))
        if conversation_id == None:
            return AiConversation(None)  # return a new empty conversation
        docs = list()

        if self.using_nosql():
            self.nosql_svc.set_container(self.conversations_container)
            sql_params = [dict(name="@conversation_id", value=conversation_id)]
            sql = "select * from c where c.conversation_id = @conversation_id offset 0 limit 1"
            items = await self.nosql_svc.parameterized_query(sql, sql_params, True)
            for doc in items:
                docs.append(doc)
        else:
            self.vcore_svc.set_container(self.conversations_container)
            filter = {"conversation_id": conversation_id}
            cursor = self.vcore_svc.get_coll().find(filter, limit=2)
            for doc in cursor:
                docs.append(doc)

        if len(docs) > 0:
            return AiConversation(docs[0])
        else:
            conv = AiConversation(None)
            conv.conversation_id = conversation_id
            return conv

    async def rag_find_library(self, libname, libtype="pypi", max_doc_count=10):
        """Find the given library document(s) in the DB for the purpose of RAG data."""
        docs_list = list()
        try:
            if self.using_nosql():
                self.nosql_svc.set_container(ConfigService.graph_source_container())
                sql_params = [
                    dict(name="@name", value=libname),
                    dict(name="@libtype", value=libtype),
                ]
                sql = """
select c.libtype, c.name, c.summary, c.documentation_summary
 from c where c.name = @name and c.libtype = @libtype offset 0 limit {}
                """.format(
                    max_doc_count
                ).strip()
                results = await self.nosql_svc.parameterized_query(
                    sql, sql_params, True
                )
                for doc in results:
                    docs_list.append(doc)
            else:
                self.vcore_svc.set_coll(ConfigService.graph_source_container())
                attrs = "libtype,name,summary,documentation_summary".split(",")
                filter = {"libtype": libtype, "name": libname}
                cursor = self.vcore_svc.get_coll().find(
                    filter, projection=attrs, limit=max_doc_count
                )
                for doc in cursor:
                    docs_list.append(doc)
        except Exception as e:
            logging.critical(
                "Exception in DBService#rag_find_library: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return docs_list

    async def rag_vector_search(self, embedding, k=10):
        docs_list = list()
        try:
            if self.using_nosql():
                sql = """
select top {} c.pk, c.id, c.name, c.libtype, VectorDistance(c.embedding, {}) as score 
from c
ORDER BY VectorDistance(c.embedding, {})""".strip().format(
                    k, json.dumps(embedding), json.dumps(embedding)
                )
                results = await self.nosql_svc.query_items(sql, True)
                for doc in results:
                    docs_list.append(doc)
            else:
                self.vcore_svc.set_coll(ConfigService.graph_source_container())
                vs_result = self.vcore_svc.vector_search(embedding, k=k)
                docs_list = vs_result["results"]
        except Exception as e:
            logging.critical(
                "Exception in DBService#rag_vector_search: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return docs_list

    async def get_documents_by_libtype_and_names(self, libtype: str, names: List[str]):
        """Lookup in the database the given docs returned from a GraphRAG search."""
        docs_list = list()
        try:
            if self.using_nosql():
                quoted_values = self.quoted_values_string(names)
                sql = "select * from c where c.libtype = 'pypi' and c.name in ({})".format(
                    quoted_values
                )
                logging.info(sql)
                items = await self.nosql_svc.query_items(sql, True)
                for doc in items:
                    docs_list.append(doc)
            else:
                self.vcore_svc.set_coll(ConfigService.graph_source_container())
                filter = {"libtype": libtype, "name": {"$in": names}}
                cursor = self.vcore_svc.get_coll().find(filter)
                for doc in cursor:
                    docs_list.append(doc)
        except Exception as e:
            logging.critical(
                "Exception in DBService#get_documents_by_libtype_and_names: {}".format(
                    str(e)
                )
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return docs_list

    async def save_feedback(self, req_model: AiConvFeedbackModel):
        try:
            if self.using_nosql():
                await self.nosql_svc.save_feedback(req_model)
            else:
                self.vcore_svc.save_feedback(req_model)
        except Exception as e:
            logging.critical("Exception in DBService#save_feedback: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    def quoted_values_string(self, list_of_strings: List[str]):
        """This method is useful for providing the list of values for a NoSQL query with an IN clause"""
        result, last_idx = "", len(list_of_strings) - 1
        for idx, s in enumerate(list_of_strings):
            if idx < last_idx:
                result = result + "'{}',".format(s)
            else:
                result = result + "'{}'".format(s)
        return result

    async def close(self):
        logging.info("DBService#close()")
        if self.using_nosql():
            await self.nosql_svc.close()
        else:
            self.vcore_svc.close()
