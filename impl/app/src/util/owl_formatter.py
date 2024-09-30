import logging
import xmlformatter

# Instances of this class are used to return a minimized version of
# a given OWL file content in order to be passed efficiently in an
# AzureOpenAI system prompt.
# Chris Joakim, Microsoft


class OwlFormatter:
    def __init__(self, opts={}):
        self.opts = opts

    def minimize(self, owl_xml: str) -> str:
        try:
            formatter = xmlformatter.Formatter(
                compress=True,
                selfclose=True,
                indent="0",
                indent_char="\t",
                encoding_output="utf-8",
                preserve=["literal"],
            )
            return formatter.format_string(owl_xml).decode("utf-8")
        except Exception as e:
            logging.critical("Exception in minimize: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
            return owl_xml
