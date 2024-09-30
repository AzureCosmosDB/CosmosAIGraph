import asyncio
import logging

from src.services.ai_service import AiService
from src.services.entities_service import EntitiesService

# Instances of this class determine the intent of a user natural language
# query and infers from it the "strategy" to be used to obtain the
# appropriate data for the RAG pattern.
#
# See the unit tests in file tests/test_strategy_builder.py for example
# natural language statements and the resulting "strategy" to be applied.
#
# Aleksey Savateyev, Chris Joakim, Microsoft


class StrategyBuilder:
    """Constructor method; call initialize() immediately after this."""

    def __init__(self, ai_svc: AiService):
        self.ai_svc = ai_svc
        self.entities_svc = EntitiesService()

    async def initialize(self):
        """This method should be called immediately after the constructor."""
        await self.entities_svc.initialize()

    async def determine(self, natural_language) -> dict:
        strategy = dict()
        strategy["natural_language"] = natural_language
        strategy["strategy"] = ""
        strategy["entitytype"] = "pypi"
        strategy["name"] = ""
        strategy["algorithm"] = ""

        self.check_for_simple_known_utterances(strategy)
        if len(strategy["strategy"]) > 0:
            # we were able to determine the strategy with fast/simple rules
            # otherwise, fall through and determine the strategy with the LLM.
            logging.warning(
                "StrategyBuilder#determine - simple_known_utterance: {}".format(
                    strategy
                )
            )
            return strategy

        user_prompt = f"""User asked: "{natural_language}". Determine the best data source to address it."""
        strategy["strategy"] = (
            "vector"  # default to vector amongst several possible strategies
        )
        strategy["name"] = self.entities_svc.identify(natural_language).most_frequent()

        try:
            # Generate code to generate entity graph
            # TODO: add historic/user-recommended sample questions at the end of each of the 3 sections below
            system_prompt = f"""You are helping to determine the data source to use while fetching context to help answer a question in the user prompt. There are only 3 sources: database, vector index and graph. Assume that each of these sources has the same data but in different formats and with different degree of fidelity/detail.
            The user may want to obtain information from the database such as PII, transactions, records, incidents, requests, or other specific items. For example, if they want to "look something up" or "find" or "fetch", this would be a database search. Examples of questions that are best answered with the information from a database are:
            "which records are currently open for me",
            "how many transactions have been processed",
            "what is the status of my request X",
            "when was ticket X last updated",
            "look something up",
            "look up record X",
            "find library X".
            The user may also want to ask about similarity or proximity to something, or an open-ended question, in which case the answer should be retrieved from a vector index. Examples of questions that are best answered with the information from a vector index are:
            "how to change my password",
            "how to track X",
            "expense reports procedure".
            The user may also want to ask about well-established facts, such as office locations, or ask about relationship between various entities, which can be retrieved by traversing a knowledge graph or dependency graph or digital twin. Examples of questions that are best answered with the information from a graph are:
            "what is the address of the nearest office",
            "what types of reports exist",
            "who do I report to",
            "what are the dependencies of the python library".
            Classify the data source to use to answer the user's question contained in the user prompt with one of the following: db (for transaction- and record-specific questions best suite for database), vector (for similarity and proximity type of questions best suited for vector index) and graph (for factual and relationship-specific questions best suited for knowledge graph).
            The determination between a database and a knowledge graph should be based on the whether user is looking for specific item(s) (return db in this case) or some set of items (even if only one) connected on certain criteria (return graph).
            Note that output should be only one word: db or vector or graph. Act bold and confident!
            """
            # the AiService#get_completion method is async, therefore we need to await it here.
            # also, therefore, this method needs to be async, and calls to it must be awaited.
            strategy["strategy"] = await self.ai_svc.get_completion(
                natural_language, system_prompt
            )
            strategy["algorithm"] = "llm"
            logging.info(
                "StrategyBuilder:determine got strategy: {} from {}".format(
                    strategy["strategy"], user_prompt
                )
            )
        except Exception as e:
            logging.critical(
                "Exception in StrategyBuilder#determine: {} {}".format(
                    natural_language, str(e)
                )
            )
        return strategy

    def check_for_simple_known_utterances(self, strategy):
        """
        this demonstrates a fast and low-cost optimization; no LLM invocation necessary.
        """
        try:
            tokens = strategy["natural_language"].split(" ")
            if len(tokens) == 3:
                # examples: 'look up python Flask' or 'find pypi Flask'
                if tokens[0].lower() in [
                    "look up",
                    "look up",
                    "find",
                    "fetch",
                    "search",
                    "get",
                    "retrieve",
                    "list",
                    "show",
                ]:
                    if tokens[1].lower() in ["pypi", "python"]:
                        strategy["algorithm"] = "text"
                        strategy["strategy"] = "db"
                        if self.entities_svc.library_present(tokens[2]):
                            strategy["name"] = tokens[2]
                        elif self.entities_svc.library_present(tokens[2].lower()):
                            strategy["name"] = tokens[2].lower()
        except Exception as e:
            pass
