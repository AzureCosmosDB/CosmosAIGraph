import datetime
import json
import logging
import time
import traceback
import uuid

import asyncio
from azure.cosmos import exceptions, PartitionKey
from azure.cosmos.aio import CosmosClient

from src.services.config_service import ConfigService

# Instances of this class are used to access a Cosmos DB NoSQL
# account/database using the asynchronous SDK methods.
# This module uses the 'azure-cosmos' SDK on PyPi.org, currently version 4.7.0.
# See https://pypi.org/project/azure-cosmos/
# See https://learn.microsoft.com/en-us/python/api/overview/azure/cosmos-readme?view=azure-python
# See https://azuresdkdocs.blob.core.windows.net/$web/python/azure-cosmos/4.7.0/azure.cosmos.html
# See https://github.com/Azure/azure-sdk-for-python/tree/azure-cosmos_4.7.0/sdk/cosmos/azure-cosmos/samples
# See https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search
# Chris Joakim, Microsoft

# azure_logger can be used to set the verbosity of the Azure and Cosmos SDK logging
azure_logger = logging.getLogger('azure')
azure_logger.setLevel(logging.WARNING)


class CosmosNoSQLAsyncService:

    def __init__(self, opts={}):
        # https://www.slingacademy.com/article/python-defining-a-class-with-an-async-constructor/
        # https://stackoverflow.com/questions/33128325/how-to-set-class-attribute-with-await-in-init
        self._opts = opts
        self._dbname = None
        self._dbproxy = None
        self._ctrproxy = None
        self._cname = None
        self._uri = ConfigService.cosmosdb_nosql_uri()
        self._key = ConfigService.cosmosdb_nosql_key1()
        self._client = None
        logging.info("CosmosNoSQLAsyncService - __init__ completed")

    async def initialize(self):
        """ This method should be called after the above constructor. """
        self._client = CosmosClient(
            self._uri, 
            self._key)
        await self._client.__aenter__()  # this piece is important for the SDK to cache account information
        logging.info("CosmosNoSQLAsyncService - initialize() completed")

    async def close(self):
        if self._client is not None:
            await self._client.close()
            logging.info("CosmosNoSQLAsyncService - client closed")

    async def list_databases(self):
        """Return the list of database names in the account."""
        dblist = list()
        async for db in self._client.list_databases():
            dblist.append(db["id"])
        return dblist
    
    def set_db(self, dbname):
        """Set the current database to the given dbname."""
        try:
            self._dbname = dbname
            self._dbproxy = self._client.get_database_client(dbname)
        except Exception as e:
            logging.critical(str(e))
            print(traceback.format_exc())
        return self._dbproxy  # <class 'azure.cosmos.aio._database.DatabaseProxy'>

    def set_container(self, cname):
        """Set the current container in the current database to the given cname."""
        self._ctrproxy = self._dbproxy.get_container_client(cname)
        return self._ctrproxy  # <class 'azure.cosmos.aio._container.ContainerProxy'>

    async def list_containers(self):
        """Return the list of container names in the current database."""
        container_list = list()
        async for container in self._dbproxy.list_containers():
            container_list.append(container["id"])
        return container_list

    async def point_read(self, id, pk):
        return await self._ctrproxy.read_item(item=id, partition_key=pk)

    async def create_item(self, doc):
        return await self._ctrproxy.create_item(body=doc)   

    async def upsert_item(self, doc):
        return await self._ctrproxy.upsert_item(body=doc)
        
    async def delete_item(self, id, pk):
        return await self._ctrproxy.delete_item(item=id, partition_key=pk)
        
    # https://github.com/Azure/azure-sdk-for-python/blob/azure-cosmos_4.7.0/sdk/cosmos/azure-cosmos/samples/document_management_async.py

    async def execute_item_batch(self, item_operations: list, pk: str):
        # example item_operations:
        #   [("create", (get_sales_order("create_item"),)), next op, next op, ...]
        # each operation is a 2-tuple, with the operation name as tup[0]
        # tup[1] is a nested 2-tuple , with the document as tup[0]
        return await self._ctrproxy.execute_item_batch(
            batch_operations=item_operations, partition_key=pk)
        
    async def query_items(self, sql, cross_partition=False, pk=None, max_items=100):
        parameters_list = list()
        parameters_list.append(
            {'name': '@enable_cross_partition_query', 'value': cross_partition})
        parameters_list.append(
            {'name': '@max_item_count', 'value': max_items})
        if pk is not None:
            parameters_list.append(
                {'name': '@partition_key', 'value': pk})
        
        results_list = list()
        query_results = self._ctrproxy.query_items(
            query=sql,
            parameters=parameters_list)
        async for item in query_results:
            results_list.append(item)
        return results_list

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
            header = 'x-ms-request-charge'
            return float(self._ctrproxy.client_connection.last_response_headers[header])
        except:
            return -1.0
        