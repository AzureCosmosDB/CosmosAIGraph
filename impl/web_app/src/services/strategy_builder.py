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
# Aleksey Savateyev & Chris Joakim, Microsoft, 2025


class StrategyBuilder:
    """Constructor method; call initialize() immediately after this."""

    def __init__(self, ai_svc: AiService):
        self.ai_svc = ai_svc

    def determine(self, natural_language) -> dict:
        strategy = {
            "natural_language": natural_language,
            "strategy": "",
            "name": "",
            "algorithm": "",
        }

        # quick rule-based detection
        self.check_for_simple_known_utterances(strategy)
        if len(strategy.get("strategy", "")) > 0:
            logging.warning(
                "StrategyBuilder#determine - simple_known_utterance: {}".format(
                    strategy
                )
            )
            return strategy

        user_prompt = f"{natural_language}"
        # default to vector amongst several possible strategies
        strategy["strategy"] = "vector"
        try:
            strategy["name"] = (
                EntitiesService.identify(natural_language).most_frequent() or ""
            )
        except Exception:
            strategy["name"] = ""

        try:
            system_prompt = (
                "You are helping to determine the data source to use while fetching context "
                "to help answer a question in the user prompt. There are only 3 sources: "
                "database, vector index and graph. Assume that each of these sources has the "
                "same data but in different formats and with different degree of fidelity/detail. "
                "The user may want to obtain information from the database such as PII, transactions, "
                "records, incidents, requests, or other specific items. For example, if they want to \"look something up\" "
                "or \"find\" or \"fetch\", this would be a database search. The user may also want to ask about similarity "
                "or proximity to something, or an open-ended question, in which case the answer should be retrieved from a vector index. "
                "The user may also want to ask about relationship between entities, which can be retrieved by traversing a knowledge graph. "
                "Classify the data source with one word: db, vector, or graph."
            )
            raw = self.ai_svc.get_completion(natural_language, system_prompt)
            strategy["strategy"] = self._normalize_strategy_output(raw)
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

    def _normalize_strategy_output(self, raw) -> str:
        """Normalize LLM output to one of 'db', 'vector', or 'graph'."""
        try:
            valid = {"db", "vector", "graph"}
            if raw is None:
                return "vector"
            text = str(raw).strip().lower()
            # Attempt JSON parse if looks like JSON
            if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
                import json
                try:
                    obj = json.loads(text)
                    if isinstance(obj, dict):
                        for k in ("source", "strategy", "data_source", "result"):
                            v = obj.get(k)
                            if v:
                                text = str(v).strip().lower()
                                break
                    elif isinstance(obj, list) and len(obj) > 0:
                        text = str(obj[0]).strip().lower()
                except Exception:
                    # fall back to plain text handling
                    pass
            # Map common variants
            if text in ("database", "db", "dbms"):
                return "db"
            if text in valid:
                return text
            # Heuristic containment
            if "graph" in text:
                return "graph"
            if "vector" in text or "embedding" in text:
                return "vector"
            if "db" in text or "database" in text or "sql" in text or "lookup" in text or "find" in text or "fetch" in text:
                return "db"
            # Default safe choice
            return "vector"
        except Exception:
            return "vector"

    def check_for_simple_known_utterances(self, strategy):
        """
        this demonstrates a fast and low-cost optimization; no LLM invocation necessary.
        """
        try:
            nl_words = strategy["natural_language"].split(" ")
            if len(nl_words) < 4:
                # examples: 'lookup python Flask' or 'find library Flask'
                lookup_words = "lookup,find,fetch,search,get,retrieve,show".split(",")
                if nl_words[0].lower() in lookup_words:
                    for word in nl_words[1:]:
                        if EntitiesService.library_present(word):
                            strategy["strategy"] = "db"
                            strategy["name"] = word.lower()
        except Exception as e:
            pass
