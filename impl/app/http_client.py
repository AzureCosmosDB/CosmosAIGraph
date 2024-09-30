"""
This script is intended for development use to invoke a locally running
instance of app_graph.
Usage:
  python http_client.py <func>
  python http_client.py get <url>
  python http_client.py get http://localhost:8001/
  python http_client.py get http://localhost:8001/liveness
  python http_client.py get http://localhost:8001/owl_info
  python http_client.py post_sparql_query http://localhost:8001/sparql_query pypi_m26
  python http_client.py post_sparql_bom_query http://localhost:8001/sparql_bom_query pypi flask 2
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import json
import sys
import traceback

import httpx
import jinja2

from docopt import docopt

from src.services.config_service import ConfigService


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


def request_headers():
    header = ConfigService.websvc_auth_header()
    value = ConfigService.websvc_auth_value()
    headers = dict()
    headers["Content-Type"] = "application/json"
    headers[header] = value
    return headers


def get(url):
    r = httpx.get(url, headers=request_headers())
    print(r)
    print(r.json())


def post_sparql_query(url, libtype_libname):
    postdata = post_sparql_query_postdata(libtype_libname)
    print(postdata)
    r = httpx.post(url, headers=request_headers(), data=json.dumps(postdata))
    print("----- response text -----")
    print(r.text)
    print("----- pretty-print JSON response object -----")
    obj = json.loads(r.text)
    print(json.dumps(obj, sort_keys=False, indent=2))


def post_sparql_query_postdata(libtype_libname):
    sparql_template = """
PREFIX c: <http://cosmosdb.com/caig#>
SELECT ?o
WHERE {
    <http://cosmosdb.com/caig/{{ libtype_libname }}> c:developed_by ?o .
}
LIMIT 10
"""
    jenvironment = jinja2.Environment()
    jtemplate = jenvironment.from_string(sparql_template)
    sparql = jtemplate.render(libtype_libname=libtype_libname).strip()
    postdata = dict()
    postdata["sparql"] = sparql
    return postdata


def post_sparql_bom_query(url, libtype, libname, max_depth):
    postdata = post_sparql_bom_query_postdata(libtype, libname, max_depth)
    print("postdata: {}".format(postdata))
    r = httpx.post(url, headers=request_headers(), data=json.dumps(postdata))
    print("----- response status_code -----")
    print(r.status_code)
    print("----- response text -----")
    print(r.text)
    print("----- pretty-print JSON response object -----")
    obj = json.loads(r.text)
    print(json.dumps(obj, sort_keys=False, indent=2))


def post_sparql_bom_query_postdata(libtype, libname, max_depth):
    postdata = dict()
    postdata["libtype"] = libtype
    postdata["libname"] = libname
    postdata["max_depth"] = max_depth
    return postdata


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            func = sys.argv[1].lower()
            if func == "get":
                url = sys.argv[2]
                get(url)
            elif func == "post_sparql_query":
                url = sys.argv[2]
                libtype_libname = sys.argv[3]
                post_sparql_query(url, libtype_libname)
            elif func == "post_sparql_bom_query":
                url = sys.argv[2]
                libtype = sys.argv[3]
                libname = sys.argv[4]
                max_depth = sys.argv[5]
                post_sparql_bom_query(url, libtype, libname, max_depth)
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            print(str(e))
            print(traceback.format_exc())
    else:
        print_options("Error: no command-line args provided")
