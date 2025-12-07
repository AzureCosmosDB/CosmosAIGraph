"""
Usage:
    python main_nosql.py test_cosmos_service <dbname>
    python main_nosql.py test_cosmos_service dev
    python main_nosql.py load_data <dbname> <cname> <max_docs>
    python main_nosql.py load_data caig libraries 999999
    python main_nosql.py vector_search_words <word1> <word2> <word3> ...
    python main_nosql.py vector_search_words asynchronous web framework with pydantic
    python main_nosql.py ad_hoc dev
    python main_nosql.py test_db_service cosmos_nosql caig
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

# This program is for CLI functionality related to Cosmos DB NoSQL API.
# Chris Joakim, Aleksey Savateyev, 2025


import asyncio
import json
import sys
import time
import logging
import traceback
import uuid
import os

from docopt import docopt
from dotenv import load_dotenv

from faker import Faker

from src.util.cosmos_doc_filter import CosmosDocFilter
from src.services.ai_service import AiService
from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
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
        flask_doc = FS.read_json("{}/flask.json".format(ConfigService.data_source_dir()))
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
        flask_doc = FS.read_json("{}/flask.json".format(ConfigService.data_source_dir()))
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


# async def load_entities(dbname, cname):
#     logging.info("load_entities, dbname: {}, cname: {}".format(dbname, cname))
#     try:
#         opts = dict()
#         nosql_svc = CosmosNoSQLService(opts)
#         await nosql_svc.initialize()
#         nosql_svc.set_db(dbname)
#         nosql_svc.set_container(cname)
#         doc = FS.read_json("../../data/entities/entities_doc.json")
#         print(doc)
#         resp = await nosql_svc.upsert_item(doc)
#         print(resp)

#     except Exception as e:
#         logging.info(str(e))
#         logging.info(traceback.format_exc())
#     await nosql_svc.close()


async def load_data(dbname, cname, max_docs):
    logging.info("load_data, dbname: %s, cname: %s, max_docs: %s", dbname, cname, max_docs)
    try:
        opts = dict()
        nosql_svc = CosmosNoSQLService(opts)
        await nosql_svc.initialize()
        nosql_svc.set_db(dbname)
        nosql_svc.set_container(cname)
        data_dir = ConfigService.data_source_dir()
        print(f"DEBUG load_data: data_dir = {data_dir}")
        print(f"DEBUG load_data: os.environ CAIG_DATA_SOURCE_DIR = {os.environ.get('CAIG_DATA_SOURCE_DIR', 'NOT SET')}")
        await load_docs_from_directory(
            nosql_svc, data_dir, max_docs
        )
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await nosql_svc.close()


async def load_single_doc(nosql_svc, fq_name, filename, pk_field, ai_svc=None, max_retries=3, retry_delay=2):
    """Load a single document with retry logic and automatic embedding generation."""
    result = {"success": False, "error": None}
    try:
        doc = FS.read_json(fq_name)
        
        # Validate partition key field exists
        if pk_field not in doc:
            result["error"] = f"missing_pk_{pk_field}"
            return result
        
        # Ensure id field exists, using filename without extension as default
        if "id" not in doc:
            doc["id"] = filename.replace(".json", "")
        
        # Check for embedding field and generate if missing or empty
        embedding_field = ConfigService.embedding_field_name()
        if embedding_field not in doc or not doc[embedding_field]:
            if ai_svc is None:
                ai_svc = AiService()
            
            # Create text to embed from document fields
            text_to_embed = ""
            for field in ConfigService.fulltext_search_fields():
                if field in doc and doc[field]:
                    text_to_embed += str(doc[field]) + "\n"
            
            if text_to_embed.strip():
                # Limit text size to avoid exceeding token limit (8192 tokens)
                # Using ~3 chars per token as conservative estimate: 8192 * 3 = ~24576 chars
                # Using 20000 chars to be safe and leave room for overhead
                max_chars = 16000
                text_to_embed = text_to_embed.strip()
                if len(text_to_embed) > max_chars:
                    text_to_embed = text_to_embed[:max_chars]
                    #logging.info(f"Truncated text for embedding generation in {filename} from {len(text_to_embed)} to {max_chars} chars")
                
                try:
                    resp = ai_svc.generate_embeddings(text_to_embed)
                    doc[embedding_field] = resp.data[0].embedding
                    #logging.info(f"Generated embedding for document: {filename}")
                except Exception as embed_error:
                    logging.warning(f"Failed to generate embedding for {filename}: {str(embed_error)}")
                    # Continue without embedding - don't fail the entire document load
        
        # Create the document with retry logic
        for attempt in range(max_retries):
            try:
                await nosql_svc.create_item(doc)
                result["success"] = True
                return result
            except Exception as create_error:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logging.warning(
                        "Create failed for {} (attempt {}/{}), retrying in {} seconds: {}".format(
                            fq_name, attempt + 1, max_retries, wait_time, str(create_error)
                        )
                    )
                    await asyncio.sleep(wait_time)
                else:
                    result["error"] = f"create_failed: {str(create_error)}"
                    return result
    except Exception as e:
        result["error"] = f"read_failed: {str(e)}"
    return result


async def load_docs_from_directory(nosql_svc, source_dir, max_docs):
    # Use walk() to recursively find all files in subdirectories
    walked_files = FS.walk(source_dir)
    if walked_files is None:
        logging.error(f"Directory not found or inaccessible: {source_dir}")
        return
    
    # Extract just the full file paths and filter for .json files
    all_files = [f["full"] for f in walked_files]
    filtered_files_list = filter_files_list(all_files, ".json")
    
    total_files = len(filtered_files_list)
    files_to_process = min(max_docs, total_files)
    load_counter = Counter()
    pk_field = ConfigService.graph_source_pk()
    ai_svc = AiService()  # Initialize once for all documents
    
    logging.info(f"Found {total_files} JSON files (recursively), will process {files_to_process} files")
    
    # Process documents in concurrent batches for better performance
    # Reduced batch size to avoid timeouts when sending large documents with embeddings
    batch_size = 44  # Number of concurrent operations
    
    for batch_start in range(0, files_to_process, batch_size):
        batch_end = min(batch_start + batch_size, files_to_process)
        tasks = []
        
        for idx in range(batch_start, batch_end):
            fq_name = filtered_files_list[idx]  # Already has full path from walk()
            filename = os.path.basename(fq_name)  # Extract just the filename for id
            
            tasks.append(load_single_doc(nosql_svc, fq_name, filename, pk_field, ai_svc))
        
        # Execute batch concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update counters
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                load_counter.increment("exception")
                logging.error("Batch task %d raised exception: %s", batch_start + idx, result)
            elif result.get("success"):
                load_counter.increment("create_success")
            elif result.get("error"):
                if "missing_pk" in result["error"]:
                    load_counter.increment("missing_partition_key")
                elif "read_failed" in result["error"]:
                    load_counter.increment("file_read_error")
                else:
                    load_counter.increment("create_failure")
        
        logging.info(
            "Processed batch {}-{} of {}, cumulative results: {}".format(
                batch_start, batch_end - 1, files_to_process - 1, json.dumps(load_counter.get_data())
            )
        )
        
        # Small delay between batches to prevent server timeout
        await asyncio.sleep(0.1)
    
    logging.info(
        "load_docs_from_directory completed; results: {}".format(
            json.dumps(load_counter.get_data())
        )
    )

async def load_batch(nosql_svc, load_counter, batch_number, batch_operations):
    batch_counter = Counter()
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            results = await nosql_svc.execute_item_batch(batch_operations)
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
            return  # Success, exit retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logging.warning(
                    "Batch {} failed (attempt {}/{}), retrying in {} seconds: {}".format(
                        batch_number, attempt + 1, max_retries, wait_time, str(e)
                    )
                )
                await asyncio.sleep(wait_time)
            else:
                logging.error(
                    "Batch {} failed after {} attempts: {}".format(
                        batch_number, max_retries, str(e)
                    )
                )
                raise  # Re-raise after all retries exhausted
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

        nosql_svc = CosmosNoSQLService()
        await nosql_svc.initialize()
        nosql_svc.set_db(ConfigService.graph_source_db())
        nosql_svc.set_container(ConfigService.graph_source_container())

        docs = await nosql_svc.vector_search(embedding_value=embedding, limit=4)
        for idx, doc in enumerate(docs):
            # cdf = CosmosDocFilter(doc["c"])
            # print("doc {}: {} Score: {}".format(idx, cdf.filter_out_embedding("embedding"), doc["score"]))
            print("doc {}:\n{}\n".format(idx, json.dumps(doc, indent=2)))
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await nosql_svc.close()


async def test_db_service(source, dbname):
    try:
        nosql_svc = CosmosNoSQLService(source)
        await nosql_svc.initialize()
        nosql_svc.set_db(dbname)
        nosql_svc.set_container(ConfigService.graph_source_container())
    finally:
        await nosql_svc.close()


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
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(script_dir, '.env')
    
    # Load .env file with explicit path
    load_dotenv(dotenv_path=env_file, override=True)
    
    # Force logging configuration (in case it was already configured by imported modules)
    logging.basicConfig(
        format="%(asctime)s - %(message)s", 
        level=logging.INFO,
        force=True
    )
    
    # Silence verbose HTTP logging from OpenAI/httpx libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Debug: Print configuration after logging is set up
    logging.info(f"Loaded .env from: {env_file}")
    logging.info(f"CAIG_DATA_SOURCE_DIR from env: {os.getenv('CAIG_DATA_SOURCE_DIR')}")
    logging.info(f"CAIG_DATA_SOURCE_DIR from ConfigService: {ConfigService.data_source_dir()}")
    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        try:
            func = sys.argv[1].lower()
            if func == "test_cosmos_service":
                dbname = sys.argv[2]
                asyncio.run(test_cosmos_service(dbname))
            # elif func == "load_entities":
            #     dbname = sys.argv[2]
            #     cname = sys.argv[3]
            #     asyncio.run(load_entities(dbname, cname))
            elif func == "load_data":
                dbname = sys.argv[2]
                cname = sys.argv[3]
                max_docs = int(sys.argv[4])
                asyncio.run(load_data(dbname, cname, max_docs))
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
