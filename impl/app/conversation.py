"""
This module is for ad-hoc development and testing of "conversational ai"
functionality outside of the UI.
Usage:
    python conversation.py conv1
    python conversation.py conv2 > tmp/conv2.txt
    python conversation.py summarize_html
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import asyncio
import faker
import json
import logging
import sys
import time

from docopt import docopt
from dotenv import load_dotenv

# Services with Business Logic
from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.ai_service import AiService
from src.services.config_service import ConfigService
from src.services.cosmos_vcore_service import CosmosVCoreService
from src.services.logging_level_service import LoggingLevelService
from src.util.fs import FS
from src.services.ontology_service import OntologyService
from src.services.rag_data_service import RAGDataService


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


async def conversation1():
    user_queries = [
        "who invented the telephone",
        "when was he born",
        "what other three historic events happened that year",
    ]
    await have_conversation(user_queries)


async def conversation2():
    # See file impl/data/testdata/strategy_builder_examples.json
    # where these user queries were copied from.
    user_queries = [
        "find the PyPi Flask Library",
        "get dependencies of the pypi flask lib",
        "what are the top two asynchronous alternatives to it",
        "show bill of materials for the pypi flask library",
        # "what movies did kevin bacon appear in in 1984?"
    ]
    await have_conversation(user_queries)


async def have_conversation(user_queries):
    # setup the various services used in the conversation
    ai_svc = AiService()
    ontology_svc = OntologyService()
    owl_xml = ontology_svc.get_owl_content()
    logging.info("owl_xml:\n{}".format(owl_xml))
    vcore_opts = dict()
    vcore_opts["conn_string"] = ConfigService.mongo_vcore_conn_str()
    logging.info("vcore_opts: {}".format(vcore_opts))
    vcore = CosmosVCoreService(vcore_opts)
    vcore.set_db(ConfigService.graph_source_db())
    rds = RAGDataService(ai_svc, vcore)
    conversation_id = "test-conv-{}".format(int(time.time()))
    outfile = "tmp/{}.json".format(conversation_id)
    sleep_seconds = 3.0

    # start the conversation
    conv = vcore.load_conversation(
        conversation_id
    )  # returns a new or existing conversation
    logging.warning("load_conversation: {} {}".format(conv, conv.serialize()))
    conv.conversation_id = conversation_id
    vcore.save_conversation(conv)
    logging.warning("new conversation saved: {}".format(conversation_id))
    context: str = ""

    for user_query in user_queries:
        print("====================================")
        logging.info("user_query: {}".format(user_query))
        conv.add_user_message(user_query)
        prompt_template = ai_svc.generic_prompt_template()
        completion: AiCompletion = await ai_svc.invoke_kernel(
            conv, prompt_template, user_query, context=context
        )
        context = completion.get_content()
        print("completion.get_content(): {}\n{}".format(str(type(context)), context))
        vcore.save_conversation(conv)
        FS.write_json(json.loads(conv.serialize()), outfile)
        time.sleep(sleep_seconds)

    print("mongosh lookup command for Cosmos DB vCore:")
    print("db.conversations.find({conversation_id: '" + conversation_id + "'})")
    conv.print_summary(True)
    print("see outfile: {}".format(outfile))


async def summarize_html():
    ai_svc = AiService()
    infile = "../data/pypi/html_pages/pypi_pydantic_27464.json"
    data = FS.read_json(infile)
    html = data["html"]
    for n in range(0, 3):
        print("==========")
        print("{} html: \n{}".format(n, html))
        output = await ai_svc.summarize_html(html)
        print("\n---\noutput: \n{}".format(output))


if __name__ == "__main__":
    load_dotenv(override=True)
    logging.basicConfig(
        format="%(asctime)s - %(message)s", level=LoggingLevelService.get_level()
    )
    ConfigService.log_defined_env_vars()

    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        try:
            func = sys.argv[1].lower()
            if func == "conv1":
                asyncio.run(conversation1())
            elif func == "conv2":
                asyncio.run(conversation2())
            elif func == "summarize_html":
                asyncio.run(summarize_html())
            elif func == "ad_hoc":
                fake = faker.Faker()
                for n in range(0, 10):
                    print("---")
                    print(fake.text())
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.critical(str(e))
            logging.exception(e, stack_info=True, exc_info=True)
