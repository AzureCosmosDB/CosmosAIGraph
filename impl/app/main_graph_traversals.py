"""
This is an experimental module used for exploring the Cosmos DB NoSQL
as a "graph database" for Sitecore in advance of an upcoming POC.
Usage:
    python main_graph_traversals.py dependencies_traversal1 caig libraries flask 3
    python main_graph_traversals.py dependencies_traversal2 caig libraries flask 3
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

"""

- Minimize the number of Cosmos DB containers; non-relational
- Single Container Design, generally
- Store dissimilar documents in the same container, with a 'doctype' attribute
- Group related documents in the same logical partition for efficiency/costs
- Use the "Aggregation Pipeline" pattern instead of a graph query syntax
  - Each stage of the pipeline uses the results of the previous stage
  - This logic can use fast/efficient Cosmos DB point-reads
- Converting from a LPG "Vertices and Edges" model
  - "Fold" the edges into the source vertex as an array of edges
- Use materialized view documents to optimize common queries

"""

# 
# Sample libraries document in Cosmos DB
# {
#   "id": "pypi_flask",
#   "pk": "pypi",
#   "name": "flask",
#   "libtype": "pypi",
#   "dependency_ids": [
#     "pypi_asgiref",
#     "pypi_blinker",
#     "pypi_click",
#     "pypi_importlib_metadata",
#     "pypi_itsdangerous",
#     "pypi_jinja2",
#     "pypi_python_dotenv",
#     "pypi_werkzeug"
#   ],
#   ...
# }

import asyncio
import json
import sys
import time
import logging
import traceback
import uuid

from docopt import docopt
from dotenv import load_dotenv

from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.util.counter import Counter
from src.util.fs import FS


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


async def dependencies_traversal1(dbname, cname, libname, depth):
    logging.info("dependencies_traversal1, {} {} {} {}".format(
        dbname, cname, libname, depth))
    collected_libraries, stats = dict(), dict()
    stats['method'] = 'dependencies_traversal1'
    stats['dbname'] = dbname
    stats['cname'] = cname
    stats['libname'] = libname
    stats['depth'] = depth
    try:
        # Connect to Cosmos DB - account, db, and container
        opts = dict()
        opts["enable_diagnostics_logging"] = True
        nosql_svc = CosmosNoSQLService(opts)
        await nosql_svc.initialize()
        dbproxy = nosql_svc.set_db(dbname)
        print("dbproxy: {}".format(dbproxy))
        ctrproxy = nosql_svc.set_container(cname)
        print("ctrproxy: {}".format(ctrproxy))
        stats['start_epoch'] = time.time()  # start the clock here

        # First, find the given root library
        root_library_doc = await find_by_name(ctrproxy, libname)
        if root_library_doc is not None:
            root_library_doc['__traversal_depth'] = 0
            doc_id = root_library_doc['id']  # example: "pypi_flask"
            collected_libraries[doc_id] = root_library_doc
            # Now, traverse the dependencies to the given depth
            for depth in range(1, depth + 1):
                await traverse_at_depth1(
                    ctrproxy, collected_libraries, stats, depth)
        else:
            print("Error: root library not found: {}".format(libname))
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    finally:
        stats['finish_epoch'] = time.time()
        stats['elapsed_seconds'] = stats['finish_epoch'] - stats['start_epoch']
        stats['collected_libraries_count'] = len(collected_libraries)
        collected_libraries["__stats"] = stats
        await nosql_svc.close()
        FS.write_json(collected_libraries, "tmp/dependencies_traversal1.json")
        print("stats: {}".format(json.dumps(stats, sort_keys=False, indent=2)))

async def traverse_at_depth1(ctrproxy, collected_libraries, stats, depth):
    # get the list of libraries at the previous depth, then execute
    # a series of POINT READS to fetch them.
    libs_to_get = dict()  # key is id, value is pk
    for libname in collected_libraries.keys():
        libdoc = collected_libraries[libname]
        if libdoc == 0:
            pass  # previously attempted but not found
        else:
            if libdoc['__traversal_depth'] == depth - 1:
                for dep_id in libdoc['dependency_ids']:
                    if dep_id in collected_libraries.keys():
                        pass  # already collected or attempted
                    else:
                        libs_to_get[dep_id] = "pypi"  # all python docs are in pk "pypi"

    for id in libs_to_get.keys():
        pk = libs_to_get[id]
        libdoc = await point_read(ctrproxy, id, pk)
        if libdoc is not None:
            libdoc['__traversal_depth'] = depth
            collected_libraries[id] = libdoc
        else:
            collected_libraries[id] = 0  # mark as attempted

    stats["depth_{}_libs_to_get".format(depth)] = len(libs_to_get)
    stats["depth_{}_collected_libs".format(depth)] = len(collected_libraries)

# === impl 2 below 

async def dependencies_traversal2(dbname, cname, libname, depth):
    logging.info("dependencies_traversal2, {} {} {} {}".format(
        dbname, cname, libname, depth))
    collected_libraries, stats = dict(), dict()
    stats['method'] = 'dependencies_traversal2'
    stats['dbname'] = dbname
    stats['cname'] = cname
    stats['libname'] = libname
    stats['depth'] = depth
    try:
        # Connect to Cosmos DB - account, db, and container
        opts = dict()
        opts["enable_diagnostics_logging"] = True
        nosql_svc = CosmosNoSQLService(opts)
        await nosql_svc.initialize()
        dbproxy = nosql_svc.set_db(dbname)
        print("dbproxy: {}".format(dbproxy))
        ctrproxy = nosql_svc.set_container(cname)
        print("ctrproxy: {}".format(ctrproxy))
        stats['start_epoch'] = time.time()  # start the clock here

        # First, find the given root library
        root_library_doc = await find_by_name(ctrproxy, libname)
        if root_library_doc is not None:
            root_library_doc['__traversal_depth'] = 0
            doc_id = root_library_doc['id']  # example: "pypi_flask"
            collected_libraries[doc_id] = root_library_doc
            # Now, traverse the dependencies to the given depth
            for depth in range(1, depth + 1):
                await traverse_at_depth2(
                    ctrproxy, collected_libraries, stats, depth)
        else:
            print("Error: root library not found: {}".format(libname))
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    finally:
        stats['finish_epoch'] = time.time()
        stats['elapsed_seconds'] = stats['finish_epoch'] - stats['start_epoch']
        stats['collected_libraries_count'] = len(collected_libraries)
        collected_libraries["__stats"] = stats
        await nosql_svc.close()
        FS.write_json(collected_libraries, "tmp/dependencies_traversal2.json")
        print("stats: {}".format(json.dumps(stats, sort_keys=False, indent=2)))

async def traverse_at_depth2(ctrproxy, collected_libraries, stats, depth):
    # get the list of libraries at the previous depth, then execute
    # a SINGLE QUERY WITH IN CLAUSE to fetch them.
    libs_to_get = dict()  # key is id, value is pk
    for libname in collected_libraries.keys():
        libdoc = collected_libraries[libname]
        if libdoc == 0:
            pass  # previously attempted but not found
        else:
            if libdoc['__traversal_depth'] == depth - 1:
                for dep_id in libdoc['dependency_ids']:
                    if dep_id in collected_libraries.keys():
                        pass  # already collected or attempted
                    else:
                        libs_to_get[dep_id] = "pypi"  # all python docs are in pk "pypi"

    if len(libs_to_get) > 0:
        for id in libs_to_get.keys():
            collected_libraries[id] = 0  # flag them as not found, but overlay below if found
        sql = find_by_ids_in_pk("pypi", list(libs_to_get.keys()))
        query_results = ctrproxy.query_items(query=sql)
        async for libdoc in query_results:
            doc_id = libdoc['id']
            libdoc['__traversal_depth'] = depth
            collected_libraries[doc_id] = libdoc

    stats["depth_{}_libs_to_get".format(depth)] = len(libs_to_get)
    stats["depth_{}_collected_libs".format(depth)] = len(collected_libraries)


async def find_by_name(ctrproxy, libname) -> dict | None:
    try:
        sql = lookup_by_name_sql(libname)
        query_results = ctrproxy.query_items(query=sql)
        print(ctrproxy.client_connection.last_response_headers)
        async for item in query_results:
            return item
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    return None 

async def point_read(ctrproxy, id, pk) -> dict | None:
    try:
        sql = point_read_sql(id, pk)
        query_results = ctrproxy.query_items(query=sql)
        async for item in query_results:
            return item
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    return None 

def lookup_by_name_sql(name):
    return "select c.id, c.pk, c.dependency_ids from c where c.name = '{}'".format(name)

def point_read_sql(id, pk):
    return "select * from c where c.id = '{}' and c.pk = '{}'".format(id, pk)

def find_by_ids_in_pk(pk, ids):
    # where c.name in ('flask','m26')
    ids_str = json.dumps(ids).replace("[", "").replace("]", "").strip()
    return "select * from c where c.pk = '{}' and c.id in ({})".format(pk, ids_str)

if __name__ == "__main__":
    # standard initialization of env and logger
    load_dotenv(override=True)
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        try:
            func = sys.argv[1].lower()
            if func == "dependencies_traversal1":
                dbname, cname = sys.argv[2], sys.argv[3]
                libname, depth = sys.argv[4], int(sys.argv[5])
                asyncio.run(dependencies_traversal1(dbname, cname, libname, depth))
            elif func == "dependencies_traversal2":
                dbname, cname = sys.argv[2], sys.argv[3]
                libname, depth = sys.argv[4], int(sys.argv[5])
                asyncio.run(dependencies_traversal2(dbname, cname, libname, depth))
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.info(str(e))
            logging.info(traceback.format_exc())


# stats: {
#   "method": "dependencies_traversal1",
#   "dbname": "caig",
#   "cname": "libraries",
#   "libname": "flask",
#   "depth": 3,
#   "start_epoch": 1731353376.375386,
#   "depth_1_libs_to_get": 8,
#   "depth_1_collected_libs": 9,
#   "depth_2_libs_to_get": 27,
#   "depth_2_collected_libs": 36,
#   "depth_3_libs_to_get": 95,
#   "depth_3_collected_libs": 131,
#   "finish_epoch": 1731353385.4101925,
#   "elapsed_seconds": 9.034806489944458,
#   "collected_libraries_count": 131
# }

# stats: {
#   "method": "dependencies_traversal2",
#   "dbname": "caig",
#   "cname": "libraries",
#   "libname": "flask",
#   "depth": 3,
#   "start_epoch": 1731353323.572402,
#   "depth_1_libs_to_get": 8,
#   "depth_1_collected_libs": 9,
#   "depth_2_libs_to_get": 27,
#   "depth_2_collected_libs": 36,
#   "depth_3_libs_to_get": 95,
#   "depth_3_collected_libs": 131,
#   "finish_epoch": 1731353325.9584138,
#   "elapsed_seconds": 2.386011838912964,
#   "collected_libraries_count": 131
# }
