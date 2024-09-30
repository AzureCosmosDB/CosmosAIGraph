import datetime
import json
import logging
import time
import uuid

from typing import Any, Dict, Final, Iterator, List, Optional, Tuple, Type, Union

from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from semantic_kernel.exceptions import ContentSerializationError

from src.services.ai_completion import AiCompletion
from src.services.config_service import ConfigService

# Instances of this class represent an growing AI conversation with ChatHistory
# and related completions and token usage.  Instances are JSON-serializable and
# can be persisted and read from Cosmos DB.
# Chris Joakim, Microsoft


class AiConversation:

    def __init__(self, json_obj=None):
        try:
            if json_obj is not None:
                self.created_at = json_obj["created_at"]
                self.created_date = json_obj["created_date"]
                self.updated_at = json_obj["updated_at"]
                self.conversation_id = json_obj["conversation_id"]
                self.pk = self.conversation_id
                self.id = self.conversation_id
                self.last_user_message = json_obj["conversation_id"]

                if "prompts" in json_obj.keys():
                    self.prompts = json_obj["prompts"]
                else:
                    self.prompts = list()

                if "completions" in json_obj.keys():
                    self.completions = json_obj["completions"]
                else:
                    self.completions = list()

                if "chat_history" in json_obj.keys():
                    hist_json = json_obj["chat_history"]
                    self.chat_history = ChatHistory.restore_chat_history(
                        json.dumps(hist_json)
                    )
                else:
                    self.chat_history = ChatHistory()

                if "diagnostic_messages" in json_obj.keys():
                    self.diagnostic_messages = json_obj["diagnostic_messages"]
                else:
                    self.diagnostic_messages = list()

                if "ai_config" in json_obj.keys():
                    self.ai_config = json_obj["ai_config"]
                else:
                    self.ai_config = self.current_ai_configuration()
            else:
                self.created_at = time.time()
                self.created_date = str(
                    datetime.datetime.fromtimestamp(self.created_at)
                )
                self.updated_at = self.created_at
                self.conversation_id = str(uuid.uuid4())
                self.pk = self.conversation_id
                self.id = self.conversation_id
                self.prompts = list()
                self.completions = list()
                self.chat_history = ChatHistory()
                self.diagnostic_messages = list()
                self.last_user_message = ""
                self.ai_config = self.current_ai_configuration()
        except Exception as e:
            logging.critical("Exception in AiConversation#__init__: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)

    def get_conversation_id(self):
        return self.conversation_id

    def set_conversation_id(self, conv_id):
        self.conversation_id = conv_id
        self.pk = conv_id

    def get_chat_history(self):
        return self.chat_history

    def set_updated_at(self):
        self.updated_at = time.time()

    def get_message_count(self):
        try:
            return len(self.chat_history.messages)
        except Exception as e:
            return -1

    def add_diagnostic_message(self, msg):
        if msg is not None:
            self.diagnostic_messages.append(msg)

    def add_prompt(self, ptxt: str):
        if ptxt is not None:
            self.prompts.append(ptxt)

    def add_user_message(self, msg) -> None:
        try:
            if (msg is not None) and (len(msg) > 0):
                self.last_user_message = msg
                self.chat_history.add_user_message(msg)
        except Exception as e:
            logging.critical(
                "Exception in AiConversation#add_user_message: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    def get_last_user_message(self):
        return self.last_user_message

    def add_system_message(self, msg) -> None:
        try:
            if msg is not None:
                if len(str(msg)) > 0:
                    self.chat_history.add_system_message(msg)
        except Exception as e:
            logging.critical(
                "Exception in AiConversation#add_system_message: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    def add_assistant_message(self, msg) -> None:
        try:
            if msg is not None:
                self.chat_history.add_assistant_message(msg)
        except Exception as e:
            logging.critical(
                "Exception in AiConversation#add_assistant_message: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    def add_tool_message(self, msg) -> None:
        try:
            return self.chat_history.add_tool_message(msg)
        except Exception as e:
            logging.critical(
                "Exception in AiConversation#add_tool_message: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    def add_message(
        self,
        message: Union[ChatMessageContent, Dict[str, Any]],
        encoding: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            return self.chat_history.add_message(message, encoding, metadata)
        except Exception as e:
            logging.critical(
                "Exception in AiConversation#add_message: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)

    def add_completion(self, completion: AiCompletion):
        if completion is not None:
            completion.set_user_text(self.last_user_message)
            self.completions.append(completion.get_data())

    def formatted_prompts_text(self) -> str:
        """return a formatted string of the prompts for display in the UI"""
        all_lines = list()
        if self.prompts is not None:
            for idx, ptxt in enumerate(self.prompts):
                all_lines.append("")
                all_lines.append("=== PROMPT {} ===".format(idx + 1))
                all_lines.append("")
                lines = ptxt.split("\n")
                for line in lines:
                    all_lines.append(line)
        return "\n".join(all_lines)

    def current_ai_configuration(self) -> dict:
        config = dict()
        config["completions_deployment"] = (
            ConfigService.azure_openai_completions_deployment()
        )
        config["embeddings_deployment"] = (
            ConfigService.azure_openai_embeddings_deployment()
        )
        config["invoke_kernel_max_tokens"] = ConfigService.invoke_kernel_max_tokens()
        config["invoke_kernel_temperature"] = ConfigService.invoke_kernel_temperature()
        config["invoke_kernel_top_p"] = ConfigService.invoke_kernel_top_p()
        config["html_summarize_max_tokens"] = ConfigService.html_summarize_max_tokens()
        config["html_summarize_temperature"] = (
            ConfigService.html_summarize_temperature()
        )
        config["html_summarize_top_p"] = ConfigService.html_summarize_top_p()
        config["get_completion_temperature"] = (
            ConfigService.get_completion_temperature()
        )
        config["moderate_sparql_temperature"] = (
            ConfigService.moderate_sparql_temperature()
        )
        config["optimize_context_and_history_max_tokens"] = (
            ConfigService.optimize_context_and_history_max_tokens()
        )
        config["truncate_llm_context_max_ntokens"] = (
            ConfigService.truncate_llm_context_max_ntokens()
        )
        config["generate_graph_temperature"] = (
            ConfigService.generate_graph_temperature()
        )
        return config

    def serialize(self) -> str:
        try:
            obj = dict()
            obj["created_at"] = self.created_at
            obj["created_date"] = self.created_date
            obj["updated_at"] = self.updated_at
            obj["conversation_id"] = self.conversation_id
            obj["pk"] = self.pk
            obj["id"] = self.id
            obj["prompts"] = self.prompts
            obj["completions"] = self.completions
            obj["chat_history"] = json.loads(self.chat_history.serialize())
            obj["diagnostic_messages"] = self.diagnostic_messages
            obj["ai_config"] = self.ai_config
            return json.dumps(obj, sort_keys=False, indent=2)
        except Exception as e:
            raise ContentSerializationError(
                f"Unable to serialize ChatHistory to JSON: {e}"
            )

    def last_completion(self) -> dict:
        last_completion = None
        for c in self.completions:
            last_completion = c
        return last_completion

    def last_completion_content(self):
        c = self.last_completion()
        if c is None:
            return ""
        else:
            return c["content"]

    def print_summary(self, include_prompts=True):
        print("========== ")
        print("conversation_id:  {}".format(self.conversation_id))
        print("completion count: {}".format(len(self.completions)))
        for idx, c in enumerate(self.completions):
            print("---")
            print("completion {} at {}".format(idx + 1, c["created_date"]))
            print("completion; user_text: {}".format(c["user_text"]))
            print("completion; usage: {}".format(c["usage"]))
            print("completion; content: {}".format(c["content"]))

        if include_prompts == True:
            print("\nprompts: {}".format(len(self.prompts)))
            for idx, ptxt in enumerate(self.prompts):
                print("\n--- prompt {}:".format(idx))
                lines = ptxt.split("\n")
                for line in lines:
                    print("prompt: {}".format(line))
