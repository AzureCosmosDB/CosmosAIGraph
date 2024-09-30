"""
This module is for ad-hoc tasks not related to the actual working app,
and it uses asynchronous programming with asyncio and the await/async keywords.
Usage:
    python async_main.py invoke_strategy_builder
Options:
  -h --help     Show this screen.
  --version     Show version.
"""

import asyncio
import json
import logging
import os
import psutil
import sys
import time
import traceback

from docopt import docopt
from dotenv import load_dotenv

from src.services.ai_service import AiService
from src.services.logging_level_service import LoggingLevelService
from src.services.strategy_builder import StrategyBuilder
from src.util.fs import FS


logging.basicConfig(
    format="%(asctime)s - %(message)s", level=LoggingLevelService.get_level()
)


def print_options(msg):
    print(msg)
    arguments = docopt(__doc__, version="1.0.0")
    print(arguments)


async def invoke_strategy_builder():
    logging.info("invoke_strategy_builder")
    ai_svc = AiService()
    sb = StrategyBuilder(ai_svc)

    examples_list = FS.read_json("../data/testdata/strategy_builder_examples.json")
    for example in examples_list:
        natural_language = example["natural_language"]
        expected_strategy = example["strategy"]
        strategy_obj = await sb.determine(natural_language)
        actual_strategy = strategy_obj["strategy"]
        print(
            "=== actual: {}, expected: {}, nl: {}".format(
                actual_strategy, expected_strategy, natural_language
            )
        )

    # Results 5/28:
    # === actual: vector, expected: db,    nl: lookup PyPi Flask
    # === actual: graph,  expected: db,    nl:   find the PyPi Flask Library
    # === actual: vector, expected: db,    nl: get the Python M26 Library
    # === actual: graph,  expected: graph, nl: dependencies of the pypi flask lib
    # === actual: graph,  expected: graph, nl: authors of the pypi pydantic library
    # === actual: graph,  expected: graph, nl: bill of materials for the pypi flask library
    # === actual: graph,  expected: graph, nl: bill of materials for the python pydantic library


if __name__ == "__main__":
    load_dotenv(override=True)

    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        try:
            func = sys.argv[1].lower()
            if func == "invoke_strategy_builder":
                asyncio.run(invoke_strategy_builder())
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.critical(str(e))
            logging.exception(e, stack_info=True, exc_info=True)
