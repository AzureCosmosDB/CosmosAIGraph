# Instances of this class are used to optimize prompt input
# for the LLM, and also render a high-fidelity version of the
# actual prompt used by semantic-kernel when calling the LLM.
# This class is created and used in class AiService.
#
# The single public method, 'generate_and_truncate()', returns
# a results dictionary with well-defined keys after optionally truncating
# the context and history to fit within the given max_tokens.
#
# The keys in the results dictionary include:
# - pruned_context - An optionally truncated version of the given context.
# - pruned_history - An optionally truncated version of the given history.
# - actual_prompt - The final prompt rendered with the pruned context and history.
# - actual_tokens - The token count of the actual_prompt, calculated by tiktoken.
#
# Chris Joakim, Microsoft

import json
import logging
import jinja2
import tiktoken

MAX_ITERATIONS = 8


class PromptOptimizer:

    def __init__(self):
        self.jinja_env = jinja2.Environment()
        # tiktoken, for token estimation, doesn't work with gpt-4 at this time
        self.tiktoken_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.enc = tiktoken.get_encoding("cl100k_base")

    def generate_and_truncate(
        self,
        prompt_template: str,
        full_context: str,
        full_history: str,
        user_query: str,
        max_tokens: int,
    ):
        """
        Return a results dictionary with well-defined keys after optionally truncating
        the context and history to fit within max_tokens.
        """
        continue_to_prune, ntokens = True, -1

        pruned_context: str = str(full_context)
        pruned_history: str = str(full_history)

        result_obj = dict()
        result_obj["full_context"] = full_context
        result_obj["full_history"] = full_history
        result_obj["user_query"] = user_query
        result_obj["max_tokens"] = max_tokens
        result_obj["initial_context_words_ratio"] = -1.0
        result_obj["initial_history_ratio"] = -1.0
        result_obj["initial_tokens"] = -1
        result_obj["pruned_tokens"] = -1
        result_obj["pruned_context"] = pruned_context
        result_obj["pruned_history"] = pruned_history
        result_obj["actual_prompt"] = ""
        result_obj["iteration_count"] = 0
        result_obj["exception"] = ""

        while continue_to_prune == True:
            try:
                result_obj["iteration_count"] = result_obj["iteration_count"] + 1
                if result_obj["iteration_count"] >= MAX_ITERATIONS:
                    continue_to_prune = False
                else:
                    # produce the prompt test from the current context and history data
                    result_obj["actual_prompt"] = self.merge_prompt_template(
                        prompt_template,
                        pruned_context,
                        json.dumps(pruned_history),
                        user_query,
                    )
                    ntokens = len(
                        self.tiktoken_encoding.encode(result_obj["actual_prompt"])
                    )
                    if result_obj["iteration_count"] == 1:
                        result_obj["initial_tokens"] = ntokens
                    result_obj["pruned_tokens"] = ntokens

                if max_tokens < 1:
                    # execute just one iteration through this loop, to produce prompt_text,
                    # if the max_tokens is unlimited (i.e. - zero).
                    continue_to_prune = False
                else:
                    if ntokens > max_tokens:
                        # we need to prune the context and history as they are too large
                        # set pruned_xxx state variables for the next loop iteration
                        context_words_ratio = (
                            (float(max_tokens) / float(ntokens))
                        ) - 0.05
                        if result_obj["iteration_count"] == 1:
                            result_obj["initial_context_words_ratio"] = (
                                context_words_ratio
                            )
                        context_words = pruned_context.split()
                        history_messages = json.loads(pruned_history)["messages"]

                        # retain the tail-end of the context words
                        retain_index = int(
                            float(len(context_words)) * context_words_ratio
                        )
                        retained_words_list = list()
                        for idx, word in enumerate(context_words):
                            if idx >= retain_index:
                                retained_words_list.append(word)
                        pruned_context = (" ".join(retained_words_list)).strip()
                        result_obj["pruned_context"] = pruned_context

                        # retain the tail-end of the history messages
                        history_ratio = (
                            context_words_ratio + 0.2
                        )  # include more history than context
                        if result_obj["iteration_count"] == 1:
                            result_obj["initial_history_ratio"] = history_ratio
                        history_messages = json.loads(pruned_history)["messages"]
                        retain_index = int(float(len(history_messages)) * history_ratio)
                        if retain_index < 1:
                            retain_index = 2
                        retained_history_list = list()
                        for idx, hist in enumerate(history_messages):
                            if idx >= retain_index:
                                retained_history_list.append(hist)

                        # the history is a json string with messages, not an array of messages
                        new_history = dict()
                        new_history["messages"] = retained_history_list
                        pruned_history = json.dumps(new_history)
                        result_obj["pruned_history"] = pruned_history
                    else:
                        continue_to_prune = False
            except Exception as e:
                logging.critical(
                    "Exception in AiService#truncate_context_and_history: {}".format(
                        str(e)
                    )
                )
                logging.exception(e, stack_info=True, exc_info=True)
                result_obj["exception"] = str(e)
        return result_obj

    # private methods below

    def merge_prompt_template(
        self, prompt_template, context, history, user_query
    ) -> str:
        """
        SK and LangChain do a poor job of exposing the actual used prompt.
        This method works around that by using Jinga2 to produce a
        high-fidelity version of the actual used prompt.  This merged prompt
        is stored in the AiConversaion and is thus exposed to the UI.
        """
        try:
            values = dict()
            values["context"] = context
            values["history"] = history
            values["user_query"] = user_query
            template = self.jinja_env.from_string(prompt_template.replace("$", ""))
            return template.render(values)
        except Exception as e:
            logging.critical(
                "Exception in AiService#merge_prompt_template: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return "exception in merge_prompt_template"
