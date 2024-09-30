import jinja2
import logging

# Instances of this class are used to return 'pretty' version of
# a given (AI-generated) SPARQL query.
# Chris Joakim, Microsoft


class SparqlFormatter:

    def __init__(self, opts={}):
        self.opts = opts

    def default_prefix(self) -> str:
        return "PREFIX caig: <http://cosmosdb.com/caig#>"

    def pretty(self, sparql: str) -> str:
        try:
            if sparql.lower().strip().startswith("prefix "):
                pass
            else:
                # inject the default PREFIX and namespace if missing
                sparql = "{}\n{}".format(self.default_prefix(), sparql.strip())
                logging.warning(
                    "SparqlFormatter#pretty - prefix injected: {}".format(sparql)
                )

            if "limit " in sparql.lower().strip():
                pass
            else:
                # inject a LIMIT clause
                sparql = "{} LIMIT 100".format(sparql.strip())
                logging.warning(
                    "SparqlFormatter#pretty - limit injected: {}".format(sparql)
                )

            words, buffer, prev_word = sparql.strip().split(), list(), ""
            for word in words:
                if word in ["PREFIX", "SELECT", "WHERE"]:
                    buffer.append("\n")
                    buffer.append(word)
                    buffer.append(" ")
                elif word in ["OPTIONAL"]:
                    # buffer.append("\n")
                    buffer.append(word)
                    buffer.append(" ")
                elif word in ["."]:
                    buffer.append(word)
                    buffer.append(" ")
                    buffer.append("\n    ")
                elif word in ["{"]:
                    if prev_word == "WHERE":
                        buffer.append(word)
                        buffer.append(" ")
                        buffer.append("\n    ")
                    else:
                        buffer.append(word)
                        buffer.append(" ")
                else:
                    buffer.append(word)
                    buffer.append(" ")
                prev_word = word
            joined = "".join(buffer).strip()
            return joined.replace("    }", "}").replace("} }", "}}")
        except Exception as e:
            logging.critical("Exception in pretty_sparql: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
            return sparql
