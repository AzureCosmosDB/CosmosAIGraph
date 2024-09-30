"""
This program is EXPERIMENTAL at this time.  CosmosAIGraph may add
Azure PostgreSQL support sometime in the future.
Usage:
    python main_pg.py delete_define_libraries_table <envname> <dbname>
    python main_pg.py delete_define_libraries_table azure dev
    python main_pg.py load_pg_libraries_table <envname> <dbname>
    python main_pg.py load_pg_libraries_table azure dev
    python main_pg.py vector_search_similar_libraries <envname> <dbname> <libname>
    python main_pg.py vector_search_similar_libraries azure dev flask
    python main_pg.py vector_search_words <envname> <dbname> <word1> <word2> <word3> ...
    python main_pg.py vector_search_words azure dev asynchronous web framework with pydantic
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

# See https://learn.microsoft.com/en-us/azure/postgresql/single-server/connect-python


import json
import sys
import time
import logging
import traceback

from docopt import docopt
from dotenv import load_dotenv

from src.services.ai_service import AiService
from src.services.pg_service import PGService
from src.util.fs import FS


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


def delete_define_libraries_table(envname, dbname):
    logging.info(
        "delete_define_libraries_table, envname: {} dbname: {}".format(envname, dbname)
    )
    try:
        pg_svc = PGService(envname, dbname)
        cursor = pg_svc.get_cursor()
        cursor.execute(libraries_table_def())

        if True:
            cursor.execute(
                "select * FROM information_schema.tables WHERE table_schema='public'"
            )
            rows = cursor.fetchall()
            for row in rows:
                logging.info("row: {}".format(row))
        if True:
            cursor.execute(
                "SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'libraries';"
            )
            rows = cursor.fetchall()
            for row in rows:
                logging.info("row: {}".format(row))
        pg_svc.close()
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())


def libraries_table_def():
    return """
DROP TABLE IF EXISTS libraries CASCADE;

CREATE TABLE libraries (
  id                   bigserial primary key,
  name                 VARCHAR(255),
  libtype              VARCHAR(10),
  description          TEXT,
  keywords             TEXT,
  license              TEXT,
  release_count        INTEGER,
  package_url          VARCHAR(255),
  project_url          VARCHAR(255),
  docs_url             VARCHAR(255),
  release_url          VARCHAR(255),
  requires_python      VARCHAR(255),
  classifiers          JSONB,
  project_urls         JSONB,
  developers           JSONB,
  embedding            vector(1536)
);
""".strip()


def load_pg_libraries_table(envname, dbname):
    logging.info(
        "load_pg_libraries_table, envname: {} dbname: {}".format(envname, dbname)
    )
    try:
        pg_svc = PGService(envname, dbname)
        load_docs_from_directory(pg_svc, "../data/pypi/wrangled_libs")
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    pg_svc.close()


def load_docs_from_directory(pg_svc, wrangled_libs_dir):
    files_list = FS.list_files_in_dir(wrangled_libs_dir)
    filtered_files_list = filter_files_list(files_list, ".json")
    max_idx = len(filtered_files_list) - 1

    cursor = pg_svc.get_cursor()

    for idx, filename in enumerate(filtered_files_list):
        fq_name = "{}/{}".format(wrangled_libs_dir, filename)
        if fq_name.endswith(".json"):
            try:
                if idx < 999999:
                    logging.info(
                        "processing {} of {}: {}".format(idx, max_idx, fq_name)
                    )
                    doc = FS.read_json(fq_name)
                    sql = build_insert_library_sql(doc)
                    if sql.endswith(",[]);"):
                        pass  # skip due to empty embedding
                    else:
                        cursor.execute(sql)
            except Exception as e:
                logging.info("error processing {}: {}".format(fq_name, str(e)))
                logging.info(traceback.format_exc())
                return


def filter_files_list(files_list, suffix):
    filtered = list()
    for f in files_list:
        if f.endswith(suffix):
            filtered.append(f)
    return filtered


def build_insert_library_sql(doc):
    try:
        sql_parts = list()
        sql_parts.append("INSERT INTO libraries (")
        sql_parts.append(",".join(libraries_column_names(False)))
        sql_parts.append(") ")
        sql_parts.append("VALUES (")
        sql_parts.append(quoted_attr_value(doc, "name"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "libtype"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "description"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "keywords"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "license"))
        sql_parts.append(",")
        sql_parts.append(str(doc["release_count"]))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "package_url"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "project_url"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "docs_url"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "release_url"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "requires_python"))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "classifiers", True))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "project_urls", True))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "developers", True))
        sql_parts.append(",")
        sql_parts.append(quoted_attr_value(doc, "embedding", True))
        sql_parts.append(");")
        return "".join(sql_parts)
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())


def quoted_attr_value(doc, attr, jsonb=False):
    if attr in doc.keys():
        if jsonb:
            return "'{}'".format(json.dumps(doc[attr]))
        else:
            return "'{}'".format(str(doc[attr]).replace("'", ""))
    else:
        if attr == "embedding":
            return "[]"
        else:
            return "'?'"


def libraries_column_names(include_id=True):
    names = list()
    if include_id == True:
        names.append("id")
    names.append("name")
    names.append("libtype")
    names.append("description")
    names.append("keywords")
    names.append("license")
    names.append("release_count")
    names.append("package_url")
    names.append("project_url")
    names.append("docs_url")
    names.append("release_url")
    names.append("requires_python")
    names.append("classifiers")
    names.append("project_urls")
    names.append("developers")
    names.append("embedding")
    return names


def vector_search_similar_libraries(envname, dbname, libname):
    logging.info(f"vector_search_similar_libraries: {envname} {dbname} {libname}")
    outfile = "tmp/vector_search_similar_libraries_{}.json".format(libname)
    pg_svc = None
    search_result_docs = []
    try:
        pg_svc = PGService(envname, dbname)
        cursor = pg_svc.get_cursor()
        sql = f"select id, embedding from libraries where name = '{libname}'"
        embedding = None

        cursor.execute(sql)
        rows = cursor.fetchall()
        for row_idx, row in enumerate(rows):
            if row_idx == 0:
                id, embedding = (
                    row[0],
                    row[1],
                )  # row is a tuple of n-column values per sql

        if embedding == None:
            logging.info("library not found or no embedding: {}".format(libname))
        else:
            sql = vector_query_sql(embedding)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row_idx, row in enumerate(rows):
                result_doc = {}
                result_doc["seq"] = row_idx + 1
                result_doc["id"] = row[0]
                result_doc["name"] = row[1]
                result_doc["keywords"] = row[2]
                # result_doc['description'] = row[3]
                search_result_docs.append(result_doc)
                logging.info(result_doc)
        FS.write_json(search_result_docs, outfile)
    except Exception as excp:
        print(str(excp))
        print(traceback.format_exc())
    finally:
        if pg_svc != None:
            pg_svc.close()


def vector_search_words(envname, dbname, natural_language):
    logging.info(f"vector_search_words: {envname} {dbname} nl: {words}")
    outfile = "tmp/vector_search_words.json"
    pg_svc = None
    search_result_docs = []
    try:
        ai_svc = AiService()
        response = ai_svc.generate_embeddings(natural_language)
        embedding = response.data[0].embedding

        pg_svc = PGService(envname, dbname)
        cursor = pg_svc.get_cursor()

        if embedding == None:
            logging.info("no embedding generated")
        else:
            sql = vector_query_sql(embedding)
            cursor.execute(sql)
            rows = cursor.fetchall()
            for row_idx, row in enumerate(rows):
                result_doc = {}
                result_doc["seq"] = row_idx + 1
                result_doc["id"] = row[0]
                result_doc["name"] = row[1]
                result_doc["keywords"] = row[2]
                search_result_docs.append(result_doc)
                logging.info(result_doc)
            FS.write_json(search_result_docs, outfile)
    except Exception as excp:
        print(str(excp))
        print(traceback.format_exc())
    finally:
        if pg_svc != None:
            pg_svc.close()


def vector_query_sql(embedding):
    return """
select id, name, keywords, description
from libraries
order by embedding <-> '{}'
limit 10;
    """.format(
        embedding
    ).strip()


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
            if func == "delete_define_libraries_table":
                envname = sys.argv[2]
                dbname = sys.argv[3]
                delete_define_libraries_table(envname, dbname)
            elif func == "load_pg_libraries_table":
                envname = sys.argv[2]
                dbname = sys.argv[3]
                load_pg_libraries_table(envname, dbname)
            elif func == "vector_search_similar_libraries":
                envname = sys.argv[2]
                dbname = sys.argv[3]
                libname = sys.argv[4]
                vector_search_similar_libraries(envname, dbname, libname)
            elif func == "vector_search_words":
                envname = sys.argv[2]
                dbname = sys.argv[3]
                words = list()
                for idx, arg in enumerate(sys.argv):
                    if idx > 3:
                        words.append(sys.argv[idx])
                natural_language = " ".join(words).strip()
                vector_search_words(envname, dbname, natural_language)
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.info(str(e))
            logging.info(traceback.format_exc())
