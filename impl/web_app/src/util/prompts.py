# Instances of this class are used to return LLM prompt values.
# The prompt template is intentionally externalized as a text file
# so as to allow the development and fine-tuning of the prompt
# without requiring a code change or restarting the web app.
#
# Chris Joakim, Aleksey Savateyev, Microsoft, 2025


import logging

from src.util.fs import FS


class Prompts:
    def __init__(self, opts={}):
        self.opts = opts

    def generate_sparql_system_prompt(self, minimized_owl) -> str | None:
        try:
            template = FS.read("prompts/gen_sparql_v2.txt")
            return template.format(minimized_owl)
        except Exception as e:
            logging.critical(
                "Exception in generate_sparql_system_prompt: {}".format(str(e))
            )
            return None
