import json
import logging
import time
import os

import tiktoken

from openai import AzureOpenAI

import semantic_kernel as sk

from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureTextEmbedding,
    OpenAITextPromptExecutionSettings,
)
from semantic_kernel.functions.kernel_arguments import (
    KernelArguments,
)
from semantic_kernel.prompt_template import (
    PromptTemplateConfig,
    InputVariable,
)

from src.models.internal_models import SparqlGenerationResult
from src.services.ai_completion import AiCompletion
from src.services.ai_conversation import AiConversation
from src.services.config_service import ConfigService
from src.services.cosmos_nosql_service import CosmosNoSQLService
from src.services.ontology_service import OntologyService
from src.util.owl_formatter import OwlFormatter
from src.util.prompts import Prompts
from src.util.prompt_optimizer import PromptOptimizer

# Instances of this class are used to execute AzureOpenAI and
# semantic_kernel functionality.
# See docs at https://devblogs.microsoft.com/semantic-kernel/now-in-beta-explore-the-enhanced-python-sdk-for-semantic-kernel/
# Chris Joakim & Aleksey Savateyev, Microsoft, 2025


class AiService:
    """Constructor method; call initialize() immediately after this."""

    def __init__(self, opts={}):
        """
        Get the necessary environment variables and initialze an AzureOpenAI client.
        Also read the OWL file.
        """
        try:
            self.opts = opts
            self.aoai_endpoint = ConfigService.azure_openai_url()
            self.aoai_api_key = ConfigService.azure_openai_key()
            self.aoai_version = ConfigService.azure_openai_version()
            self.chat_function = None
            self.max_ntokens = ConfigService.truncate_llm_context_max_ntokens()

            # tiktoken, for token estimation, doesn't work with gpt-4 at this time
            self.tiktoken_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            self.enc = tiktoken.get_encoding("cl100k_base")
            self.nosql_svc = CosmosNoSQLService()

            self.aoai_client = AzureOpenAI(
                azure_endpoint=self.aoai_endpoint,
                api_key=self.aoai_api_key,
                api_version=self.aoai_version,
            )
            self.completions_deployment = (
                # deployment name/model = gpt4/gpt-4
                ConfigService.azure_openai_completions_deployment()
            )
            self.embeddings_deployment = (
                # deployment name/model = embeddings/text-embedding-ada-002
                ConfigService.azure_openai_embeddings_deployment()
            )
            self.sk_kernel = sk.Kernel()
            self.sk_kernel.add_service(
                AzureChatCompletion(
                    service_id="chat_completion",
                    deployment_name=self.completions_deployment,
                    endpoint=self.aoai_endpoint,
                    api_key=self.aoai_api_key,
                )
            )
            self.sk_kernel.add_service(
                AzureTextEmbedding(
                    service_id="text_embedding",
                    deployment_name=self.embeddings_deployment,
                    endpoint=self.aoai_endpoint,
                    api_key=self.aoai_api_key,
                )
            )

            logging.info("aoai endpoint:     {}".format(self.aoai_endpoint))
            logging.info("aoai version:      {}".format(self.aoai_version))
            logging.info("aoai client:  {}".format(self.aoai_client))
            logging.info(
                "aoai completions_deployment: {}".format(self.completions_deployment)
            )
            logging.info(
                "aoai embeddings_deployment:  {}".format(self.embeddings_deployment)
            )
            logging.info("sk_kernel: {}".format(self.sk_kernel))
        except Exception as e:
            logging.critical("Exception in AiService#__init__: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    async def initialize(self):
        """This method should be called immediately after the constructor."""
        logging.info("AiService#initialize()")
        await self.nosql_svc.initialize()

    def num_tokens_from_string(self, s: str) -> int:
        try:
            return len(self.tiktoken_encoding.encode(s))
        except Exception as e:
            logging.critical(
                "Exception in AiService#num_tokens_from_string: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return 10000

    def generate_sparql_from_user_prompt(
        self, resp_obj: dict
    ) -> SparqlGenerationResult:
        try:
            user_prompt = resp_obj["natural_language"]
            raw_owl = resp_obj["owl"]
            owl = OwlFormatter().minimize(raw_owl)
            logging.info(
                "AiService#generate_sparql_from_user_prompt - user_prompt: {}".format(
                    user_prompt
                )
            )
            if self.validate_sparql_gen_input(user_prompt, owl):
                t1 = time.perf_counter()
                system_prompt = Prompts().generate_sparql_system_prompt(owl)
                logging.info(
                    "AiService#generate_sparql_from_user_prompt - system_prompt: {}".format(
                        system_prompt
                    )
                )
                completion = self.aoai_client.chat.completions.create(
                    model=self.completions_deployment,
                    temperature=ConfigService.moderate_sparql_temperature(),
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                t2 = time.perf_counter()
                logging.info(
                    "AiService#generate_sparql_from_user_prompt - Completion: {}".format(
                        completion.choices[0].message.content
                    )
                )
                # completion is an instance of <class 'openai.types.chat.chat_completion.ChatCompletion'>
                # https://platform.openai.com/docs/api-reference/chat/object
                sparql = json.loads(completion.choices[0].message.content).get("sparql")
                if sparql == "":
                    sparql = json.loads(completion.choices[0].message.content).get("query")
                if sparql == "":
                    sparql = json.loads(completion.choices[0].message.content).get("SPARQL")
                resp_obj["completion_id"] = completion.id
                resp_obj["completion_model"] = completion.model
                resp_obj["prompt_tokens"] = completion.usage.prompt_tokens
                resp_obj["completion_tokens"] = completion.usage.completion_tokens
                resp_obj["total_tokens"] = completion.usage.total_tokens
                resp_obj["elapsed"] = t2 - t1
                resp_obj["sparql"] = sparql
                if resp_obj["sparql"] == None:
                    resp_obj["sparql"] = ""
                logging.info(
                    "AiService#generate_sparql_from_user_prompt - sparql: {}".format(
                        sparql
                    )
                )
            else:
                resp_obj["error"] = "content moderation failed"
        except Exception as e:
            resp_obj["error"] = str(e)
            logging.critical(
                "Exception in AiService#generate_sparql_from_user_prompt: {}".format(
                    str(e)
                )
            )
            logging.exception(e, stack_info=True, exc_info=True)
        return resp_obj

    def validate_sparql_gen_input(self, user_prompt, owl):
        """Return True if the input should be processed, else return False."""
        try:
            if user_prompt == None:
                return False
            if owl == None:
                return False
            if len(user_prompt.strip()) < 10:
                return False
            if len(owl.strip()) < 10:
                return False
            # Note: optionally implement content moderation for profanity, etc
            return True
        except Exception as e:
            return False

    def generate_embeddings(self, text):
        """
        Generate an embeddings array from the given text.
        Return an CreateEmbeddingResponse object or None.
        Invoke 'resp.data[0].embedding' to get the array of 1536 floats.
        """
        try:
            # <class 'openai.types.create_embedding_response.CreateEmbeddingResponse'>
            return self.aoai_client.embeddings.create(
                input=text, model=self.embeddings_deployment
            )
        except Exception as e:
            logging.critical(
                "Exception in AiService#generate_embeddings: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    def text_to_chunks(self, text):
        max_chunk_size = 2048
        chunks = []
        current_chunk = ""
        for sentence in text.split("."):
            if len(current_chunk) + len(sentence) < max_chunk_size:
                current_chunk += sentence + "."
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    async def invoke_kernel(
        self,
        conversation: AiConversation,
        prompt_template: str,
        user_query: str,
        context: str,
        max_tokens: int = ConfigService.invoke_kernel_max_tokens(),
        temperature: float = ConfigService.invoke_kernel_temperature(),
        top_p: float = ConfigService.invoke_kernel_top_p(),
    ) -> AiCompletion | None:

        try:
            logging.info(
                "AiService#invoke_kernel, user_query: {} {}".format(
                    user_query, len(user_query)
                )
            )
            result_obj = self.optimize_context_and_history(
                prompt_template,
                context,
                conversation.get_chat_history().serialize(),
                user_query,
                max_tokens,
            )

            # The result_obj is created by a PromptOptimizer, and is a
            # dictionary with several keys.  Some of these are for unit-testing
            # and diagnostic purposes.  The following four are the most pertinent.
            # See class PromptOptimizer for details.
            pruned_context = result_obj["pruned_context"]
            pruned_history = result_obj["pruned_history"]
            actual_prompt = result_obj["actual_prompt"]
            actual_tokens = result_obj["pruned_tokens"]

            # prev history -> conversation.get_chat_history().serialize()

            conversation.add_user_message(user_query)
            conversation.add_system_message(pruned_context)
            conversation.add_prompt(actual_prompt)
            conversation.add_diagnostic_message(
                "expected tokens: {} vs max_tokens: {}".format(
                    actual_tokens, max_tokens
                )
            )

            execution_settings = OpenAITextPromptExecutionSettings(
                service_id="chat_completion",
                ai_model_id=self.completions_deployment,
                max_tokens=abs(max_tokens),
                temperature=abs(temperature),
                top_p=abs(top_p),
            )

            # The InputVariables here must to be defined in the prompt_template
            chat_prompt_template_config = PromptTemplateConfig(
                template=prompt_template,
                name="chat",
                template_format="semantic-kernel",
                input_variables=[
                    InputVariable(
                        name="history",
                        description="The conversation ChatHistory",
                        is_required=True,
                    ),
                    InputVariable(
                        name="user_query",
                        description="The user input",
                        is_required=True,
                    ),
                    InputVariable(
                        name="context",
                        description="RAG data to augment the LLM",
                        is_required=True,
                    ),
                ],
                execution_settings=execution_settings,
            )

            if self.chat_function is None:
                self.chat_function = self.sk_kernel.add_function(
                    function_name="chat",
                    plugin_name="chatPlugin",
                    prompt_template_config=chat_prompt_template_config,
                )

            kernel_args = KernelArguments(
                user_query=user_query,
                context=pruned_context,
                history=pruned_history,
            )

            invoke_result = await self.sk_kernel.invoke(self.chat_function, kernel_args)

            conversation.add_assistant_message(str(invoke_result))
            completion = AiCompletion(conversation.get_conversation_id(), invoke_result)
            conversation.add_completion(completion)
            await self.nosql_svc.save_conversation(conversation)
            return completion
        except Exception as e:
            conversation.add_assistant_message("exception: {}".format(str(e)))
            logging.critical("Exception in AiService#invoke_kernel: {}".format(str(e)))
            logging.exception(e, stack_info=True, exc_info=True)
            return None

    def generic_prompt_template(self) -> str:
        ptxt = """You can have a conversation on any topic.
Context:
{{$context}}

Chat history:
{{$history}}

User: {{$user_query}}
ChatBot: """
        return ptxt

    def get_completion(self, user_prompt, system_prompt):
        # await asyncio.wait(0.1)
        completion = self.aoai_client.chat.completions.create(
            model=self.completions_deployment,
            temperature=ConfigService.get_completion_temperature(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        result = completion.choices[0].message.content
        return result

    def optimize_context_and_history(
        self,
        prompt_template: str,
        full_context: str,
        full_history,
        user_query: str,
        max_tokens: int = ConfigService.optimize_context_and_history_max_tokens(),
    ):
        try:
            optimizer = PromptOptimizer()
            return optimizer.generate_and_truncate(
                prompt_template, full_context, full_history, user_query, max_tokens
            )
        except Exception as e:
            logging.critical(
                "Exception in AiService#optimize_context_and_history: {}".format(str(e))
            )
            logging.exception(e, stack_info=True, exc_info=True)
            return None
