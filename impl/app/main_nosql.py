"""
This program is for CLI functionality related to Cosmos DB NoSQL API.
When you run this program it is assumed that you have your
CAIG_GRAPH_SOURCE_TYPE environment variable set to "cosmos_nosql".
Usage:
    python main_nosql.py test_cosmos_service <dbname>
    python main_nosql.py test_cosmos_service dev
    python main_nosql.py load_entities <dbname> <cname>
    python main_nosql.py load_entities caig config
    python main_nosql.py load_libraries <dbname> <cname> <max_docs>
    python main_nosql.py load_libraries caig libraries 999999
    python main_nosql.py vector_search_words <word1> <word2> <word3> ...
    python main_nosql.py vector_search_words asynchronous web framework with pydantic
    python main_nosql.py ad_hoc dev
    python main_nosql.py test_db_service cosmos_nosql caig
    python main_nosql.py test_db_service cosmos_vcore caig
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

# See https://learn.microsoft.com/en-us/azure/postgresql/single-server/connect-python


import asyncio
import json
import sys
import time
import logging
import traceback
import uuid

from docopt import docopt
from dotenv import load_dotenv

from faker import Faker

from src.services.ai_service import AiService
from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.db_service import DBService
from src.services.graph_service import GraphService
from src.util.counter import Counter
from src.util.fs import FS

fake = Faker()


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


async def ad_hoc(dbname):
    """ad_hoc and exploratory logic"""
    logging.info("ad_hoc, dbname: {}".format(dbname))
    try:
        if False:
            try:
                cname = "libraries_v1"
                opts = dict()
                opts["enable_diagnostics_logging"] = False
                nosql_svc = CosmosNoSQLService(opts)
                await nosql_svc.initialize()
                dbname = ConfigService.graph_source_db()
                cname = ConfigService.graph_source_container()
                dbproxy = nosql_svc.set_db(dbname)
                print("dbproxy: {}".format(dbproxy))
                ctrproxy = nosql_svc.set_container(cname)
                print("ctrproxy: {}".format(ctrproxy))

                sql = "select c.id, c.name, c.libtype, c.license_kwds, c.kwds, c.developers, c.dependency_ids from c offset 0 limit 999999"
                query_results = ctrproxy.query_items(query=sql)
                doc_count = 0
                async for item in query_results:
                    doc_count = doc_count + 1
                    print(json.dumps(item, sort_keys=False, indent=2))
            finally:
                print("docs read: {}".format(doc_count))
                await nosql_svc.close()

        if True:
            print("initializing GraphService ...")
            gs_opts = dict()
            gs_opts["persist_graph"] = True
            gs_opts["iterate_graph"] = True
            gs = GraphService(gs_opts)
            await gs.initialize()
            print("GraphService initialized")
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    logging.info("end of ad_hoc")


async def test_cosmos_service(dbname):
    """This method invokes the various functionality of class CosmosNoSQLService."""
    logging.info("test_cosmos_service, dbname: {}".format(dbname))
    try:
        cname = "libraries"
        opts = dict()
        opts["enable_diagnostics_logging"] = True
        nosql_svc = CosmosNoSQLService(opts)
        await nosql_svc.initialize()

        dbs = await nosql_svc.list_databases()
        logging.info("databases: {}".format(dbs))

        dbproxy = nosql_svc.set_db(dbname)
        print("dbproxy: {}".format(dbproxy))
        # print(str(type(dbproxy)))  # <class 'azure.cosmos.aio._database.DatabaseProxy'>

        containers = await nosql_svc.list_containers()
        print("containers: {}".format(containers))

        ctrproxy = nosql_svc.set_container(cname)
        print("ctrproxy: {}".format(ctrproxy))
        # print(str(type(ctrproxy)))  # <class 'azure.cosmos.aio._container.ContainerProxy'>

        cname = "test"
        ctrproxy = nosql_svc.set_container(cname)
        print("ctrproxy: {}".format(ctrproxy))

        id = str(uuid.uuid4())
        pk = "test"

        doc = await nosql_svc.upsert_item(create_random_document(id, pk))
        print("upsert_item doc: {}".format(doc))
        print("last_response_headers: {}".format(nosql_svc.last_response_headers()))
        print("last_request_charge: {}".format(nosql_svc.last_request_charge()))

        doc = await nosql_svc.point_read(id, pk)
        print("point_read doc: {}".format(doc))
        print("last_request_charge: {}".format(nosql_svc.last_request_charge()))

        doc["name"] = "updated"
        updated = await nosql_svc.upsert_item(doc)
        print("updated doc: {}".format(updated))

        response = await nosql_svc.delete_item(id, pk)
        print("delete_item response: {}".format(response))

        try:
            doc = await nosql_svc.point_read(id, pk)
            print("point_read of deleted doc: {}".format(doc))
        except Exception as e:
            print("point_read of deleted doc threw an exception")
        operations, pk = list(), "bulk_pk"
        for n in range(3):
            # example: ("create", (get_sales_order("create_item"),))
            # each operation is a 2-tuple, with the operation name as tup[0]
            # tup[1] is a nested 2-tuple , with the document as tup[0]
            op = ("create", (create_random_document(None, pk),))
            operations.append(op)
        results = await nosql_svc.execute_item_batch(operations, pk)
        for idx, result in enumerate(results):
            print("batch result {}: {}".format(idx, result))

        results = await nosql_svc.query_items(
            "select * from c where c.doctype = 'sample'", True
        )
        for idx, result in enumerate(results):
            print("select * query result {}: {}".format(idx, result))

        results = await nosql_svc.query_items(
            "select * from c where c.name = 'Sean Cooper'", True
        )
        for idx, result in enumerate(results):
            print("cooper query result {}: {}".format(idx, result))

        results = await nosql_svc.query_items(
            "select * from c where c.pk = 'bulk_pk'", False
        )
        for idx, result in enumerate(results):
            print("test pk query result {}: {}".format(idx, result))

        results = await nosql_svc.query_items("SELECT VALUE COUNT(1) FROM c", False)
        for idx, result in enumerate(results):
            print("test count result: {}".format(result))

        print("last_response_headers: {}".format(nosql_svc.last_response_headers()))
        print("last_request_charge: {}".format(nosql_svc.last_request_charge()))

        headers = nosql_svc.last_response_headers()  # an instance of CIMultiDict
        for two_tup in headers.items():
            name, value = two_tup[0], two_tup[1]
            print("{} -> {}".format(name, value))

        print(
            "x-ms-item-count: {}".format(
                nosql_svc.last_response_headers()["x-ms-item-count"]
            )
        )

        sql_parameters = [dict(name="@pk", value="bulk_pk")]

        results = await nosql_svc.parameterized_query(
            "select * from c where c.pk = @pk", sql_parameters, True
        )
        for idx, result in enumerate(results):
            print("parameterized query result {}: {}".format(idx, result))

        # vector search
        cname = "libraries_v1"
        ctrproxy = nosql_svc.set_container(cname)
        print("ctrproxy: {}".format(ctrproxy))
        flask_doc = FS.read_json("../data/pypi/wrangled_libs/flask.json")
        embedding = flask_doc["embedding"]
        sql_parameters = [dict(name="@embedding", value=embedding)]
        sql_template = """
select top 10 c.pk, c._id, VectorDistance(c.embedding, {}) as score 
from c  
ORDER BY VectorDistance(c.embedding, {})""".strip().format(
            json.dumps(embedding), json.dumps(embedding)
        )
        print(sql_template)

        results = await nosql_svc.query_items(sql_template, True)
        for idx, result in enumerate(results):
            print("vector query result {}: {}".format(idx, result))

        # parameterized vector search
        cname = "libraries_v1"
        ctrproxy = nosql_svc.set_container(cname)
        print("ctrproxy: {}".format(ctrproxy))
        flask_doc = FS.read_json("../data/pypi/wrangled_libs/flask.json")
        embedding = flask_doc["embedding"]
        sql_parameters = [dict(name="@embedding", value=embedding)]
        sql_template = """
select top {} c.pk, c._id, VectorDistance(c.embedding, @embedding) as score 
from c  
ORDER BY VectorDistance(c.embedding, @embedding)""".strip().format(
            5
        )
        print(sql_template)

        sql_parameters = [dict(name="@embedding", value=embedding)]
        results = await nosql_svc.parameterized_query(
            sql_template, sql_parameters, True
        )
        for idx, result in enumerate(results):
            print("parameterized vector query result {}: {}".format(idx, result))
        print("last_response_headers: {}".format(nosql_svc.last_response_headers()))
        print("last_request_charge: {}".format(nosql_svc.last_request_charge()))

    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await nosql_svc.close()
    logging.info("end of test_cosmos_service")


async def load_entities(dbname, cname):
    logging.info("load_entities, dbname: {}, cname: {}".format(dbname, cname))
    try:
        opts = dict()
        nosql_svc = CosmosNoSQLService(opts)
        await nosql_svc.initialize()
        nosql_svc.set_db(dbname)
        nosql_svc.set_container(cname)
        doc = FS.read_json("../data/entities/entities_doc.json")
        print(doc)
        resp = await nosql_svc.upsert_item(doc)
        print(resp)

        # impl/app/src/services/entities_service.py
        # impl/app/tests/test_entities_service.py
        # impl/data/entities/entities_doc.json

    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await nosql_svc.close()


async def load_libraries(dbname, cname, max_docs):
    logging.info(
        "load_libraries, dbname: {}, cname: {}, max_docs: {}".format(
            dbname, cname, max_docs
        )
    )
    try:
        opts = dict()
        nosql_svc = CosmosNoSQLService(opts)
        await nosql_svc.initialize()
        nosql_svc.set_db(dbname)
        nosql_svc.set_container(cname)
        await load_docs_from_directory(
            nosql_svc, "../data/pypi/wrangled_libs", max_docs
        )
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await nosql_svc.close()


async def load_docs_from_directory(nosql_svc, wrangled_libs_dir, max_docs):
    files_list = FS.list_files_in_dir(wrangled_libs_dir)
    filtered_files_list = filter_files_list(files_list, ".json")
    max_idx = len(filtered_files_list) - 1
    batch_number, batch_size, batch_operations = 0, 10, list()
    load_counter = Counter()
    pk = "pypi"  # libtype is 'pypi'; dataset easily fits into one physical partition

    for idx, filename in enumerate(filtered_files_list):
        if filename.endswith(".json"):
            if idx < max_docs:
                fq_name = "{}/{}".format(wrangled_libs_dir, filename)
                try:
                    logging.info(
                        "reading file {} of {}: {}".format(idx, max_idx, fq_name)
                    )
                    doc = FS.read_json(fq_name)
                    load_counter.increment("document_files_read")
                    doc["_id"] = (
                        "{}_{}".format(doc["libtype"].strip(), doc["name"].strip())
                        .replace("-", "_")
                        .lower()
                    )
                    doc["pk"] = pk

                    op = ("upsert", (doc,))  # create, upsert
                    batch_operations.append(op)
                    if len(batch_operations) >= batch_size:
                        batch_number = batch_number + 1
                        await load_batch(
                            nosql_svc, load_counter, batch_number, batch_operations, pk
                        )
                        batch_operations = list()
                except Exception as e:
                    logging.info("error processing {}: {}".format(fq_name, str(e)))
                    logging.info(traceback.format_exc())
                    return

    if len(batch_operations) > 0:
        batch_number = batch_number + 1
        await load_batch(nosql_svc, load_counter, batch_number, batch_operations, pk)

    logging.info(
        "load_docs_from_directory completed; results: {}".format(
            json.dumps(load_counter.get_data())
        )
        # load_docs_from_directory completed; results: {"document_files_read": 10855, "201": 10761, "200": 94}
    )


async def load_batch(nosql_svc, load_counter, batch_number, batch_operations, pk):
    batch_counter = Counter()
    results = await nosql_svc.execute_item_batch(batch_operations, pk)
    for result in results:
        try:
            status_code = str(result["statusCode"])
            batch_counter.increment(status_code)
        except:
            batch_counter.increment("exceptions")
    load_counter.merge(batch_counter)
    logging.info(
        "load_batch {} with {} documents, results: {}".format(
            batch_number, len(batch_operations), json.dumps(batch_counter.get_data())
        )
    )
    logging.info("current totals: {}".format(json.dumps(load_counter.get_data())))
    time.sleep(1.0)


def filter_files_list(files_list, suffix):
    filtered = list()
    for f in files_list:
        if f.endswith(suffix):
            filtered.append(f)
    return filtered


async def vector_search_words(natural_language):
    try:
        ai_svc = AiService()
        resp = ai_svc.generate_embeddings(natural_language)
        embedding = resp.data[0].embedding

        db_svc = DBService()
        await db_svc.initialize()

        docs = await db_svc.rag_vector_search(embedding, 4)
        for idx, doc in enumerate(docs):
            print("doc {}: {}".format(idx, doc))

    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await db_svc.close()


async def test_db_service(source, dbname):
    try:
        db_svc = DBService(source)
        await db_svc.initialize()
        db_svc.set_db(dbname)
        db_svc.set_container(ConfigService.graph_source_container())
    finally:
        await db_svc.close()


def create_random_document(id, pk):
    doc_id, doc_pk, state = id, pk, fake.state()
    if doc_id == None:
        doc_id = str(uuid.uuid4())
    if doc_pk == None:
        doc_pk = state
    return {
        "id": doc_id,
        "pk": doc_pk,
        "name": fake.name(),
        "address": fake.address(),
        "city": fake.city(),
        "state": state,
        "email": fake.email(),
        "phone": fake.phone_number(),
        "doctype": "sample",
    }


if __name__ == "__main__":
    # standard initialization of env and logger
    load_dotenv(override=True)
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        if ConfigService.using_nosql():
            pass
        else:
            print(
                "Invalid value of environment variable CAIG_GRAPH_SOURCE_TYPE for this script; terminating"
            )
            exit(2)
        try:
            func = sys.argv[1].lower()
            if func == "test_cosmos_service":
                dbname = sys.argv[2]
                asyncio.run(test_cosmos_service(dbname))
            elif func == "load_entities":
                dbname = sys.argv[2]
                cname = sys.argv[3]
                asyncio.run(load_entities(dbname, cname))
            elif func == "load_libraries":
                dbname = sys.argv[2]
                cname = sys.argv[3]
                max_docs = int(sys.argv[4])
                asyncio.run(load_libraries(dbname, cname, max_docs))
            elif func == "test_db_service":
                source = sys.argv[2]
                dbname = sys.argv[3]
                asyncio.run(test_db_service(source, dbname))
            elif func == "vector_search_words":
                words = list()
                for idx, arg in enumerate(sys.argv):
                    if idx > 1:
                        words.append(sys.argv[idx])
                natural_language = " ".join(words).strip()
                asyncio.run(vector_search_words(natural_language))
            elif func == "ad_hoc":
                dbname = sys.argv[2]
                asyncio.run(ad_hoc(dbname))
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.info(str(e))
            logging.info(traceback.format_exc())
