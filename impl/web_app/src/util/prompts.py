# Instances of this class are used to return LLM prompt values.
# The prompt template is intentionally externalized as a text file
# so as to allow the development and fine-tuning of the prompt
# without requiring a code change or restarting the web app.
#
# Chris Joakim, Aleksey Savateyev, 2025


import logging

from src.util.fs import FS
from src.services.config_service import ConfigService

class Prompts:
    def __init__(self, opts={}):
        self.opts = opts

    def generate_sparql_system_prompt(self, minimized_owl, custom_rules=None) -> str | None:
        try:
            logging.warning("=" * 80)
            logging.warning(f"PROMPTS.PY - generate_sparql_system_prompt called")
            logging.warning(f"PROMPTS.PY - custom_rules parameter: {repr(custom_rules)}")
            logging.warning(f"PROMPTS.PY - custom_rules type: {type(custom_rules)}")
            logging.warning("=" * 80)
            
            # Force fresh file read on every call - no caching
            import os
            prompt_path = ConfigService.prompt_sparql()
            logging.info(f"Loading SPARQL prompt from: {os.path.abspath(prompt_path)}")
            template = FS.read(prompt_path)
            if template is None:
                logging.error(f"Failed to read prompt file: {prompt_path}")
                return None
            logging.info(f"Prompt loaded successfully, length: {len(template)} chars")
            
            # Format custom rules section
            rules_section = ""
            if custom_rules and custom_rules.strip():
                rules_section = f"\n**CUSTOM DOMAIN-SPECIFIC RULES:**\n{custom_rules.strip()}\n"
                logging.warning("=" * 80)
                logging.warning(f"PROMPTS.PY - Custom rules detected! Length: {len(custom_rules)} chars")
                logging.warning(f"PROMPTS.PY - Rules content: {custom_rules}")
                logging.warning(f"PROMPTS.PY - Formatted rules section: {rules_section}")
                logging.warning("=" * 80)
            else:
                logging.warning("PROMPTS.PY - No custom rules provided or rules are empty")
            
            # First inject custom_rules placeholder, then ontology
            prompt_with_rules = template.replace("{custom_rules}", rules_section)
            logging.warning(f"PROMPTS.PY - Placeholder replacement complete. Looking for '{{custom_rules}}' in template...")
            logging.warning(f"PROMPTS.PY - Placeholder found in template: {'{custom_rules}' in template}")
            logging.warning(f"PROMPTS.PY - Rules section in final prompt: {rules_section in prompt_with_rules if rules_section else 'N/A (no rules)'}")
            return prompt_with_rules.format(minimized_owl)
        except Exception as e:
            logging.critical(
                "Exception in generate_sparql_system_prompt: {}".format(str(e))
            )
            return None
