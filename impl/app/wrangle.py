"""
Usage:
    python wrangle.py wrangle_docs_phase1
    python wrangle.py wrangle_docs_phase2
    python wrangle.py wrangle_docs_phase3 <resume_lib>
    python wrangle.py wrangle_docs_phase3 BEGINNING > tmp/phase3.txt 2>&1 &
    python wrangle.py wrangle_docs_phase3 autorepr > tmp/phase3.txt 2>&1 &
    python wrangle.py wrangle_docs_phase4
    python wrangle.py wrangle_docs_phase4b
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

# This script was used to wrangle the original raw data into the
# data files that are present in this repo.  This script is obsolete now.
# Chris Joakim, Microsoft

import asyncio
import json
import sys
import time
import logging
import traceback

from bs4 import BeautifulSoup

from docopt import docopt
from dotenv import load_dotenv

from src.services.ai_service import AiService
from src.util.fs import FS


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


def wrangle_docs_phase1():
    """
    collect the document html filenames and keys for matching later
    persist the resulting info as tmp json files
    """
    html_files_info = collect_html_page_files_info()
    print("html_files_info count: {}".format(len(html_files_info.keys())))
    FS.write_json(html_files_info, "tmp/html_files_info.json")

    wrangled_files_info = collect_wrangled_files_info()
    print("wrangled_files_info count: {}".format(len(wrangled_files_info.keys())))
    FS.write_json(wrangled_files_info, "tmp/wrangled_files_info.json")


def collect_html_page_files_info() -> dict:
    files_info = dict()
    dirs = ["../data/pypi/html_pages"]
    for dir in dirs:
        files_list = FS.list_files_in_dir(dir)
        for fidx, f in enumerate(files_list):
            fpath = "{}/{}".format(dir, f)
            if fidx < 999999:
                try:
                    print("collecting html file {} {}".format(fidx, fpath))
                    doc = FS.read_json(fpath)
                    libtype = doc["libtype"]
                    libname = doc["libname"]
                    key = (
                        "{}_{}".format(libtype, libname)
                        .replace("-", "_")
                        .replace(".", "_")
                    )
                    files_info[key] = fpath
                except Exception as e:
                    pass
    return files_info


def collect_wrangled_files_info() -> dict:
    files_info = dict()
    dirs = ["../data/pypi/wrangled_libs"]
    for dir in dirs:
        files_list = FS.list_files_in_dir(dir)
        for fidx, f in enumerate(files_list):
            fpath = "{}/{}".format(dir, f)
            if fidx < 999999:
                try:
                    print("collecting doc file {} {}".format(fidx, fpath))
                    doc = FS.read_json(fpath)
                    key = doc["id"].replace("-", "_").replace(".", "_")
                    files_info[key] = fpath
                except Exception as e:
                    pass
    return files_info


def wrangle_docs_phase2():
    """
    Sanity-check that the keys match between the two files
    """
    html_files_info = FS.read_json("tmp/html_files_info.json")
    wrangled_files_info = FS.read_json("tmp/wrangled_files_info.json")
    key_hits, key_misses = 0, 0
    for key in sorted(wrangled_files_info.keys()):
        if key in html_files_info.keys():
            key_hits = key_hits + 1
            print("key_hit:  {}".format(key))
        else:
            key_misses = key_misses + 1
            print("key_miss: {}".format(key))
    print("key_hits:   {}".format(key_hits))
    print("key_misses: {}".format(key_misses))


async def wrangle_docs_phase3(resume_lib):
    """
    iterate the keys per the file info json files
    read the doc and html file for each key
    summarize the html value in the html doc using AiService
    populate the doc['documentation'] with the summarized html value
    concat the doc['description'] and doc['summary'] into a text value
    summarize that value if necessary, with AiService
    update the doc['documentation_summary'] with the summarized/concatinated value
    save the doc file - this will be later loaded into Cosmos DB as before
    """

    ai_svc = AiService()
    html_files_info = FS.read_json("tmp/html_files_info.json")
    wrangled_files_info = FS.read_json("tmp/wrangled_files_info.json")
    sorted_doc_keys = sorted(wrangled_files_info.keys())
    file_count = len(sorted_doc_keys)
    file_num, files_processed, resume = 0, 0, False
    if "BEGINNING" in resume_lib:
        resume = True

    for key in sorted_doc_keys:
        file_num = file_num + 1
        if "pypi" in key:
            if resume_lib in key:
                print("resuming on library {}".format(resume_lib))
                resume = True
            if (resume == True) and (file_num < 999999):
                print("---")
                doc_filename = wrangled_files_info[key]
                print("processing file  {} of {}".format(file_num, file_count))
                print("doc_filename:    {}".format(doc_filename))
                if key in html_files_info.keys():
                    files_processed = files_processed + 1
                    html_filename = html_files_info[key]
                    print("files_processed: {}".format(files_processed))
                    print("html_filename:   {}".format(html_filename))
                    try:
                        doc = FS.read_json(doc_filename)
                        attrs = doc.keys()
                        html_doc = FS.read_json(html_filename)
                        doc_changed = False
                        if "description" in attrs:
                            if "summary" in attrs:
                                doc["description"] = "{}\n{}".format(
                                    doc["summary"], doc["description"]
                                )
                                doc_changed = True
                        if "html" in html_doc.keys():
                            html = html_doc["html"]
                            if len(html) > 0:
                                text = bs4_extract_text(html)
                                summarized = await summarize_text(ai_svc, text)
                                print("summarized: {}".format(summarized))
                                if len(str(summarized)) > 10:
                                    doc["documentation_summary"] = summarized
                                    doc_changed = True
                        if doc_changed == True:
                            FS.write_json(doc, doc_filename)
                    except Exception as e:
                        logging.critical(
                            "Exception in wrangle_docs_phase3: {}".format(str(e))
                        )
                        logging.exception(e, stack_info=True, exc_info=True)
                    time.sleep(0.1)
                else:
                    print("key '{}' missing in html_files_info".format(key))


async def summarize_text(ai_svc, text) -> str:
    try:
        return str(await ai_svc.summarize_html(text))
    except Exception as e:
        print(str(e))
        return ""


def bs4_extract_text(html):
    extracted_text = ""
    try:
        if html != None:
            soup = BeautifulSoup(html, "html.parser")
            text = soup.find_all(string=True)
            output = ""
            blacklist = bs4_blacklist()
            for t in text:
                if t.parent.name not in blacklist:
                    output += "{} ".format(t.strip())
            output.replace("\rn", " ").replace("\r", " ").replace("\n", " ").replace(
                "\t", " "
            )
            r = range(10)
            for n in r:
                output = output.replace("  ", " ")
            extracted_text = output.strip()
    except:
        print(traceback.format_exc())
    return extracted_text


def bs4_blacklist():
    """return the list of html page sections to ignore by BeautifulSoup"""
    # https://chase-seibert.github.io/blog/2011/01/28/sanitize-html-with-beautiful-soup.html
    return ["meta", "link", "comment", "script", "style", "textarea", "hr"]


def wrangle_docs_phase4():
    """
    read the document files, which were updated in phase3.
    calculate a vector string from several known attributes in each document
    then call the AiService to produce embeddings for that string value
    populate the 'embedding' attribute in each document, and save the updated document JSON to disk
    """
    ai_svc = AiService()
    wrangled_files_info = FS.read_json("tmp/wrangled_files_info.json")
    sorted_doc_keys = sorted(wrangled_files_info.keys())
    attrs_of_interest = "name,description,summary,documentation_summary".split(",")
    print("wrangled_files_info count: {}".format(len(wrangled_files_info.keys())))

    for key_idx, key in enumerate(sorted_doc_keys):
        try:
            if key_idx < 999999:
                filename = wrangled_files_info[key]
                print("\nprocessing file {} {} {}".format(key_idx, key, filename))
                doc = FS.read_json(filename)
                text = collect_vector_string_for_doc(doc, attrs_of_interest)
                resp = ai_svc.generate_embeddings(text)
                embedding = resp.data[0].embedding
                if (embedding is not None) and (len(embedding) == 1536):
                    doc["embedding"] = embedding
                    FS.write_json(doc, filename)
                time.sleep(1.0)
        except:
            print(traceback.format_exc())


def collect_vector_string_for_doc(doc: str, attrs_of_interest: list):
    """
    collect the vector string for a document
    """
    strings = list()
    try:
        for attr_name in attrs_of_interest:
            if attr_name in doc.keys():
                value = doc[attr_name].strip()
                if len(value) > 0:
                    strings.append("")
                    strings.append(attr_name)
                    strings.append(value)
    except:
        print(traceback.format_exc())
    return "\n".join(strings)


def wrangle_docs_phase4b():
    """
    this phase is very similar to phase4.
    it identifies the documents that did NOT get their embedding attribute
    added in phase4 (probably due to 'description' too long), and will attempt to produce
    an embedding value from a subset of source attributes (i.e. - without 'description')
    """
    ai_svc = AiService()
    wrangled_files_info = FS.read_json("tmp/wrangled_files_info.json")
    sorted_doc_keys = sorted(wrangled_files_info.keys())
    attrs_of_interest = "name,summary,documentation_summary".split(",")
    print("wrangled_files_info count: {}".format(len(wrangled_files_info.keys())))

    for key_idx, key in enumerate(sorted_doc_keys):
        try:
            if key_idx < 999999:
                filename = wrangled_files_info[key]
                print("\nprocessing file {} {} {}".format(key_idx, key, filename))
                doc = FS.read_json(filename)
                if "embedding" not in doc.keys():
                    print("updating file {} {} {}".format(key_idx, key, filename))
                    text = collect_vector_string_for_doc(doc, attrs_of_interest)
                    resp = ai_svc.generate_embeddings(text)
                    embedding = resp.data[0].embedding
                    if (embedding is not None) and (len(embedding) == 1536):
                        doc["embedding"] = embedding
                        FS.write_json(doc, filename)
                time.sleep(0.1)
        except:
            print(traceback.format_exc())


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
            if func == "wrangle_docs_phase1":
                wrangle_docs_phase1()
            elif func == "wrangle_docs_phase2":
                wrangle_docs_phase2()
            elif func == "wrangle_docs_phase3":
                resume_lib = sys.argv[2]
                asyncio.run(wrangle_docs_phase3(resume_lib))
            elif func == "wrangle_docs_phase4":
                wrangle_docs_phase4()
            elif func == "wrangle_docs_phase4b":
                wrangle_docs_phase4b()
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.info(str(e))
            logging.info(traceback.format_exc())
