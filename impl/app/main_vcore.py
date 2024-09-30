"""
This program is for CLI functionality related to Cosmos DB Mongo vCore API.
When you run this program it is assumed that you have your
CAIG_GRAPH_SOURCE_TYPE environment variable set to "cosmos_vcore".
Usage:
    python main_vcore.py create_vcore_collections_and_indexes
    python main_vcore.py load_vcore_with_library_documents
    python main_vcore.py create_entities
    python main_vcore.py persist_entities
    python main_vcore.py identify_entities
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import asyncio
import json
import sys
import time
import logging
import traceback

from xml.sax import make_parser

from docopt import docopt
from dotenv import load_dotenv

from src.services.config_service import ConfigService
from src.services.cosmos_vcore_service import CosmosVCoreService
from src.services.entities_service import EntitiesService
from src.util.fs import FS


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


def connect_to_vcore_graph_source():
    """
    connect to the vcore account, and return a 3-tuple of
    (vcore, dbname, cname), where vcore is an instance of
    class CosmosVCoreService.
    """
    opts = dict()
    opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
    vcore = CosmosVCoreService(opts)
    if "pymongo.mongo_client.MongoClient" in str(type(vcore.get_client())):
        logging.info("connected to vcore")
    else:
        logging.info("unable to connect to vcore; exiting")
        return
    dbname = ConfigService.graph_source_db()
    cname = ConfigService.graph_source_container()
    vcore.set_db(dbname)
    vcore.set_coll(cname)
    return (vcore, dbname, cname)


def load_vcore_with_library_documents():
    vcore, dbname, cname = connect_to_vcore_graph_source()
    logging.info("using vcore db: {}, collection: {}".format(dbname, cname))
    pause_seconds = 10
    logging.info(
        "pausing {} seconds before loading the documents...".format(pause_seconds)
    )
    time.sleep(pause_seconds)
    max_load_idx = 999999
    load_docs_from_directory(vcore, max_load_idx, "../data/pypi/wrangled_libs")


def load_docs_from_directory(vcore, max_load_idx, wrangled_libs_dir):
    files_list = FS.list_files_in_dir(wrangled_libs_dir)
    filtered_files_list = filter_files_list(files_list, ".json")
    max_idx = len(filtered_files_list) - 1
    for idx, filename in enumerate(filtered_files_list):
        fq_name = "{}/{}".format(wrangled_libs_dir, filename)
        if fq_name.endswith(".json"):
            if idx < max_load_idx:
                try:
                    logging.info(
                        "processing {} of {}: {}".format(idx, max_idx, fq_name)
                    )
                    doc = FS.read_json(fq_name)
                    vcore.insert_doc(doc)
                except Exception as e:
                    logging.info("error processing {}: {}".format(fq_name, str(e)))
                    continue


def filter_files_list(files_list, suffix):
    filtered = list()
    for f in files_list:
        if f.endswith(suffix):
            filtered.append(f)
    return filtered


def create_vcore_collections_and_indexes():
    vcore, dbname, cname = connect_to_vcore_graph_source()
    logging.info("using vcore db: {}, collection: {}".format(dbname, cname))

    # create the primary graph or libraries container, per the CAIG_GRAPH_SOURCE_CONTAINER env var.
    indexes = vcore.get_coll_indexes(cname)
    logging.info(
        "indexes before:\n{}".format(json.dumps(indexes, sort_keys=False, indent=2))
    )
    vcore.create_simple_index("id")
    vcore.create_simple_index("name")
    vcore.create_simple_index("libtype")
    indexes = vcore.get_coll_indexes(cname)
    logging.info(
        "{} indexes after:\n{}".format(
            cname, json.dumps(indexes, sort_keys=False, indent=2)
        )
    )

    # config container, per env var CAIG_CONFIG_CONTAINER
    cname = ConfigService.config_container()
    vcore.set_db(dbname)
    vcore.set_coll(cname)
    logging.info("using vcore db: {}, collection: {}".format(dbname, cname))
    vcore.create_simple_index("id")
    indexes = vcore.get_coll_indexes(cname)
    logging.info(
        "{} indexes after:\n{}".format(
            cname, json.dumps(indexes, sort_keys=False, indent=2)
        )
    )

    # conversations container, per env var CAIG_CONVERSATIONS_CONTAINER
    cname = ConfigService.conversations_container()
    vcore.set_db(dbname)
    vcore.set_coll(cname)
    logging.info("using vcore db: {}, collection: {}".format(dbname, cname))
    vcore.create_simple_index("conversation_id")
    vcore.create_simple_index("created_date")
    vcore.create_simple_index("created_at")
    indexes = vcore.get_coll_indexes(cname)
    logging.info(
        "{} indexes after:\n{}".format(
            cname, json.dumps(indexes, sort_keys=False, indent=2)
        )
    )

    # feedback container, per env var CAIG_FEEDBACK_CONTAINER
    cname = ConfigService.feedback_container()
    vcore.set_db(dbname)
    vcore.set_coll(cname)
    logging.info("using vcore db: {}, collection: {}".format(dbname, cname))
    vcore.create_simple_index("conversation_id")
    indexes = vcore.get_coll_indexes(cname)
    logging.info(
        "{} indexes after:\n{}".format(
            cname, json.dumps(indexes, sort_keys=False, indent=2)
        )
    )


async def create_entities():
    entities_svc = EntitiesService()
    await entities_svc.initialize()
    entities_doc = await entities_svc.create()
    FS.write_json(entities_doc, entities_doc_filename())
    await entities_svc.close()


async def persist_entities():
    entities_svc = EntitiesService()
    await entities_svc.initialize()
    vcore = entities_svc.vcore
    vcore.set_db(ConfigService.graph_source_db())
    vcore.set_coll(ConfigService.config_container())
    entities_doc = FS.read_json(entities_doc_filename())
    query_spec = {"id": "entities"}
    vcore.replace_one(query_spec, entities_doc)
    print("document replaced")
    cursor = vcore.get_coll().find(query_spec, skip=0, limit=999999)
    docs_found = 0
    for result_doc in cursor:
        print(result_doc)
        docs_found = docs_found + 1
    print("docs_found: {}".format(docs_found))
    await entities_svc.close()


async def identify_entities():
    """This method is used for an ad-hoc test of the entitites service."""
    entities_svc = EntitiesService()
    await entities_svc.initialize()
    sentences = [
        None,
        "",
        "Chris, Aleksey, Luciano",
        "I want to express how much I like Fastapi, pydantic, you, and fastapi",
    ]
    for text in sentences:
        counter = entities_svc.identify(text)
        print("---")
        print("sentence: {}".format(text))
        print("entities: {}".format(counter.get_data()))
        print("most_frequent: {}".format(counter.most_frequent()))
    await entities_svc.close()


def entities_doc_filename():
    return "../data/entities/entities_doc.json"


if __name__ == "__main__":
    # standard initialization of env and logger
    load_dotenv(override=True)
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        if ConfigService.using_vcore():
            pass
        else:
            print(
                "Invalid value of environment variable CAIG_GRAPH_SOURCE_TYPE for this script; terminating"
            )
            exit(2)
        try:
            func = sys.argv[1].lower()
            if func == "load_vcore_with_library_documents":
                load_vcore_with_library_documents()
            elif func == "create_vcore_collections_and_indexes":
                create_vcore_collections_and_indexes()
            elif func == "create_entities":
                asyncio.run(create_entities())
            elif func == "persist_entities":
                persist_entities()
            elif func == "identify_entities":
                asyncio.run(identify_entities())
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.info(str(e))
            logging.info(traceback.format_exc())
