import asyncio
import json
import logging

import httpx
from typing import Optional

from src.services.ai_service import AiService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.config_service import ConfigService
from src.services.ontology_service import OntologyService
from src.services.rag_data_result import RAGDataResult
from src.services.strategy_builder import StrategyBuilder
from src.util.cosmos_doc_filter import CosmosDocFilter
from src.util.sparql_query_response import SparqlQueryResponse
from src.util.fs import FS

# Instances of this class are used to identify and retrieve contextual data
# in OmniRAG pattern. The data will be read from one or more of the following:
# 1) Directly from Cosmos DB documents
# 2) From in-memory graph
# 3) From Cosmos DB documents identified per a vector search to Cosmos DB
#
# Chris Joakim & Aleksey Savateyev, Microsoft, 2025


class RAGDataService:

    def __init__(self, ai_svc: AiService, nosql_svc: CosmosNoSQLService):
        try:
            self.ai_svc = ai_svc
            self.nosql_svc = nosql_svc

            # web service authentication with shared secrets
            websvc_auth_header = ConfigService.websvc_auth_header()
            websvc_auth_value = ConfigService.websvc_auth_value()
            self.websvc_headers = dict()
            self.websvc_headers["Content-Type"] = "application/json"
            self.websvc_headers[websvc_auth_header] = websvc_auth_value
            logging.debug(
                "RAGDataService websvc_headers: {}".format(
                    json.dumps(self.websvc_headers, sort_keys=False)
                )
            )
        except Exception as e:
            logging.critical("Exception in RagDataService#__init__: {}".format(str(e)))

    async def get_rag_data(self, user_text, max_doc_count=10, strategy_override: Optional[str] = None) -> RAGDataResult:
        """
        Return a RAGDataResult object which contains an array of documents to
        be used as a system prompt of a completion call to Azure OpenAI.
        In this OmniRAG implementation, the RAG data will be read,
        per the given user_text, from one of the following:
        1) Directly from Cosmos DB documents
        2) From in-memory graph
        3) From Cosmos DB documents identified per a vector search to Cosmos DB
        """
        rdr = RAGDataResult()
        rdr.set_user_text(user_text)
        rdr.set_attr("max_doc_count", max_doc_count)

        sb = StrategyBuilder(self.ai_svc)
        strategy_obj = sb.determine(user_text)
        # honor explicit user choice when provided and valid; still use name/context from builder
        valid_choices = {"db", "vector", "graph"}
        strategy = strategy_obj["strategy"]
        if strategy_override and strategy_override in valid_choices:
            strategy = strategy_override
        rdr.add_strategy(strategy)
        rdr.set_context(strategy_obj["name"])

        if strategy == "db":
            name = strategy_obj["name"]
            rdr.set_attr("name", name)
            await self.get_database_rag_data(user_text, name, rdr, max_doc_count)
            if rdr.has_no_docs() and not (strategy_override and strategy_override in valid_choices): #don't fall back if was overridden
                rdr.add_strategy("vector")
                await self.get_vector_rag_data(user_text, rdr, max_doc_count)

        elif strategy == "graph":
            await self.get_graph_rag_data(user_text, rdr, max_doc_count)
            if rdr.has_no_docs() and not (strategy_override and strategy_override in valid_choices): #don't fall back if was overridden
                rdr.add_strategy("vector")
                await self.get_vector_rag_data(user_text, rdr, max_doc_count)
        else:
            await self.get_vector_rag_data(user_text, rdr, max_doc_count)

        rdr.finish()
        return rdr

    async def get_database_rag_data(
        self, user_text: str, name: str, rdr: RAGDataResult, max_doc_count=10
    ) -> None:
        rag_docs_list = list()
        try:
            logging.warning(
                "RagDataService#get_database_rag_data, name: {}, user_text: {}".format(
                    name, user_text
                )
            )
            self.nosql_svc.set_db(ConfigService.graph_source_db())
            self.nosql_svc.set_container(ConfigService.graph_source_container())
            rag_docs_list = await self.nosql_svc.get_documents_by_name([name])
            #pertinent_attributes = "libtype,name, summary, documentation_summary"
            for doc in rag_docs_list:
                #rdr.add_doc(self.filtered_cosmosdb_lib_doc(doc))
                doc_copy = dict(doc)  # shallow copy
                doc_copy.pop("embedding", None)
                rdr.add_doc(doc_copy)

        except Exception as e:
            logging.critical(
                "Exception in RagDataService#get_database_rag_data: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    def filtered_cosmosdb_lib_doc(self, cosmos_db_doc):
        """
        Reduce the given Cosmos DB document to only the pertinent attributes,
        and truncate those if they're long.
        """
        cdf = CosmosDocFilter(cosmos_db_doc)
        return cdf.filter_for_rag_data()

    async def get_vector_rag_data(
        self, user_text, rdr: RAGDataResult = None, max_doc_count=10
    ) -> None:
        try:
            logging.warning(
                "RagDataService#get_vector_rag_data, user_text: {}".format(user_text)
            )
            create_embedding_response = self.ai_svc.generate_embeddings(user_text)
            embedding = create_embedding_response.data[0].embedding
            self.nosql_svc.set_db(ConfigService.graph_source_db())
            self.nosql_svc.set_container(ConfigService.graph_source_container())
            vs_result = await self.nosql_svc.vector_search(
                embedding_value=embedding, search_text=user_text, search_method="rrf", embedding_attr="embedding", limit=max_doc_count
            )
            for vs_doc in vs_result:
                doc_copy = dict(vs_doc)  # shallow copy
                doc_copy.pop("embedding", None)
                rdr.add_doc(doc_copy)
        except Exception as e:
            logging.critical(
                "Exception in RagDataService#get_vector_rag_data: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    async def get_graph_rag_data(
        self, user_text, rdr: RAGDataResult, max_doc_count=10
    ) -> None:
        try:
            logging.warning(
                "RagDataService#get_graph_rag_data, user_text: {}".format(user_text)
            )
            # first generate and execute the SPARQL query vs the in-memory RDF graph
            info = dict()
            info["natural_language"] = user_text
            info["owl"] = OntologyService().get_owl_content()
            sparql = self.ai_svc.generate_sparql_from_user_prompt(info)["sparql"]
            rdr.set_sparql(sparql)
            logging.warning("get_graph_rag_data - sparql:\n{}".format(sparql))

            # HTTP POST to the graph microservice to execute the generated SPARQL query
            sqr: SparqlQueryResponse | None = await self.post_sparql_to_graph_microsvc(sparql)
            if sqr is not None and sqr.response_obj is not None:
                FS.write_json(
                    sqr.response_obj,
                    "tmp/get_graph_rag_data_get_graph_rag_data_response_obj.json",
                )
                for doc in sqr.binding_values():
                    doc_copy = dict(doc)  # shallow copy
                    doc_copy.pop("embedding", None)
                    rdr.add_doc(doc_copy)
                FS.write_json(rdr.get_data(), "tmp/rdr.json")
            else:
                logging.warning("Graph microservice call failed - sqr is None or has no response_obj")
        except Exception as e:
            logging.critical(
                "Exception in RagDataService#get_graph_rag_data: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    # ========== private methods below ==========

    async def post_sparql_to_graph_microsvc(self, sparql: str) -> SparqlQueryResponse | None:
        """
        Execute a HTTP POST to the graph microservice with the given SPARQL query.
        Return a SparqlQueryResponse object or None if the request fails.
        """
        sqr = None
        try:
            url = self.graph_microsvc_sparql_query_url()
            postdata = dict()
            postdata["sparql"] = sparql
            
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    url,
                    headers=self.websvc_headers,
                    content=json.dumps(postdata),
                )
                sqr = SparqlQueryResponse(r)
                sqr.parse()
                    
        except Exception as e:
            logging.error(f"Graph microservice error: {str(e)}")
            logging.exception(e, stack_info=True, exc_info=True)
                
        return sqr

    def graph_microsvc_sparql_query_url(self):
        return "{}:{}/sparql_query".format(
            ConfigService.graph_service_url(), ConfigService.graph_service_port()
        )

    # def _parse_sparql_rag_query_results(self, sparql_query_results):
    #     libtype_name_pairs = list()
    #     try:
    #         result_rows = sparql_query_results["results"]["results"]
    #         logging.warning(
    #             "sparql rag query result_rows count: {}".format(len(result_rows))
    #         )
    #         for result in result_rows:
    #             attr_key = sorted(result.keys())[0]
    #             value = result[attr_key]
    #             tokens = value.split("/")
    #             if len(tokens) == 0:
    #                 libtype_name = value
    #             else:
    #                 last_idx = len(tokens) - 1
    #                 libtype_name = tokens[last_idx]
    #             pair = libtype_name.split("_")
    #             if len(pair) == 2:
    #                 libtype_name_pairs.append(pair)
    #             else:
    #                 libtype_name_pairs.append(["pypi", libtype_name])
    #     except Exception as e:
    #         logging.critical(
    #             "Exception in RagDataService#_parse_sparql_rag_query_results: {}".format(
    #                 str(e)
    #             )
    #         )
    #         logging.exception(e, stack_info=True, exc_info=True)
    #     return libtype_name_pairs
