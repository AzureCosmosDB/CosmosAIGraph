# Instances of this class are used to return LLM prompt values.
# The prompt template is intentionally externalized as a text file
# so as to allow the development and fine-tuning of the prompt
# without requiring a code change or restarting the web app.
#
# Chris Joakim, Aleksey Savateyev, 2025


import logging

from src.util.fs import FS


class Prompts:
    def __init__(self, opts={}):
        self.opts = opts

    def generate_sparql_system_prompt(self, minimized_owl) -> str | None:
        try:
            # Force fresh file read on every call - no caching
            import os
            prompt_path = os.getenv("CAIG_SPARQL_PROMPT_PATH", "prompts/gen_sparql_generic.txt")
            logging.info(f"Loading SPARQL prompt from: {os.path.abspath(prompt_path)}")
            template = FS.read(prompt_path)
            if template is None:
                logging.error(f"Failed to read prompt file: {prompt_path}")
                return None
            logging.info(f"Prompt loaded successfully, length: {len(template)} chars")
            return template.format(minimized_owl)
        except Exception as e:
            logging.critical(
                "Exception in generate_sparql_system_prompt: {}".format(str(e))
            )
            return None
