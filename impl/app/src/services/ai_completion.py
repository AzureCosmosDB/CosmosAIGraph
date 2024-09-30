import datetime
import logging
import time
import uuid

from semantic_kernel.functions.function_result import FunctionResult

# Instances of this class represent an immutable Completion result from Azure OpenAI.
# It collects the contents of the various Semantic Kernel and OpenAI objects
# from a completion into a single JSON-serializable object that can be persisted
# in Cosmos DB.
# Chris Joakim, Microsoft


class AiCompletion:

    def __init__(self, conversation_id: str, invoke_result: FunctionResult):
        try:
            self.data = dict()
            self.data["conversation_id"] = conversation_id
            self.data["completion_id"] = str(uuid.uuid4())
            t = time.time()
            self.data["created_at"] = t
            self.data["created_date"] = str(datetime.datetime.fromtimestamp(t))
            self.data["model"] = None
            self.data["usage"] = dict()
            self.data["usage"]["completion_tokens"] = 0
            self.data["usage"]["prompt_tokens"] = 0
            self.data["usage"]["total_tokens"] = 0
            self.data["content"] = ""
            self.data["user_text"] = ""
            self.data["rag_strategy"] = ""
            self.data["rag_data"] = ""

            # invoke_result is an instance of class
            # semantic_kernel.functions.function_result.FunctionResult
            if invoke_result is not None:
                # cc is a openai.types.chat.chat_completion.ChatCompletion
                cc = invoke_result.get_inner_content()
                self.data["model"] = cc.model
                self.data["usage"]["completion_tokens"] = cc.usage.completion_tokens
                self.data["usage"]["prompt_tokens"] = cc.usage.prompt_tokens
                self.data["usage"]["total_tokens"] = cc.usage.total_tokens
                if len(cc.choices) > 0:
                    c = cc.choices[0]  # openai.types.chat.chat_completion.Choice
                    ccm = c.message  # ChatCompletionMessage
                    self.data["content"] = ccm.content  # str
        except Exception as e:
            logging.critical("Exception in AiCompletion#__init__: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    def get_data(self):
        return self.data

    def get_model(self):
        return self.data["model"]

    def get_usage(self):
        return self.data["usage"]

    def get_content(self):
        return self.data["content"]

    def set_content(self, data):
        if data is not None:
            self.data["content"] = data

    def get_user_text(self):
        return self.data["user_text"]

    def set_user_text(self, text):
        if text is not None:
            self.data["user_text"] = text

    def set_rag_strategy(self, rs: str):
        if rs is not None:
            self.data["rag_strategy"] = rs

    def set_rag_data(self, rd):
        if rd is not None:
            self.data["rag_data"] = rd
