import base64
import json
import logging
import os
import subprocess
import sys
import time
import traceback

# Instances of this class are used to define and obtain all configuration
# values in this solution.  These are typically obtained at runtime via
# environment variables.
#
# Chris Joakim, Aleksey Savateyev


class ConfigService:

    @classmethod
    def envvar(cls, name: str, default: str = "") -> str:
        """
        Return the value of the given environment variable name,
        or the given default value."""
        if name in os.environ:
            return os.environ[name].strip()
        return default

    @classmethod
    def int_envvar(cls, name: str, default: int = -1) -> int:
        """
        Return the int value of the given environment variable name,
        or the given default value.
        """
        if name in os.environ:
            value = os.environ[name].strip()
            try:
                return int(value)
            except Exception as e:
                logging.error(
                    "int_envvar error for name: {} -> {}; returning default.".format(
                        name, value
                    )
                )
                return default
        return default

    @classmethod
    def float_envvar(cls, name: str, default: float = -1.0) -> float:
        """
        Return the float value of the given environment variable name,
        or the given default value.
        """
        if name in os.environ:
            value = os.environ[name].strip()
            try:
                return float(value)
            except Exception as e:
                logging.error(
                    "float_envvar error for name: {} -> {}; returning default.".format(
                        name, value
                    )
                )
                return default
        return default

    @classmethod
    def boolean_envvar(cls, name: str, default: bool) -> bool:
        """
        Return the boolean value of the given environment variable name,
        or the given default value.
        """
        if name in os.environ:
            value = str(os.environ[name]).strip().lower()
            if value == "true":
                return True
            elif value == "t":
                return True
            elif value == "yes":
                return True
            elif value == "y":
                return True
            else:
                return False
        return default

    @classmethod
    def boolean_arg(cls, flag: str) -> bool:
        """Return a boolean indicating if the given arg is in the command-line."""
        for arg in sys.argv:
            if arg == flag:
                return True
        return False

    @classmethod
    def application_version(cls) -> str:
        return "3.0"

    @classmethod
    def application_build(cls) -> str:
        """
        Return the date of the last git commit in the repository.
        """
        try:
            # Get the last commit date in ISO format
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse the date and return in a readable format
                commit_date = result.stdout.strip()
                # Convert from "2025-01-15 14:30:25 -0800" format to "2025-01-15"
                if commit_date:
                    return commit_date.split()[0]  # Get just the date part
            return "unknown"
        except Exception as e:
            logging.warning(f"Could not retrieve git commit date: {e}")
            return "unknown"

    @classmethod
    def defined_environment_variables(cls) -> dict:
        """
        Return a dict with the defined environment variable names and descriptions
        """
        d = dict()
        d["CAIG_HOME"] = (
            "Root directory of the CosmosAIGraph GitHub repository on your system.  (DEV ENV)"
        )
        d["CAIG_GRAPH_SOURCE_TYPE"] = (
            "The RDF graph data source type, either 'cosmos_nosql', or 'json_docs_file' or 'rdf_file'.  (GRAPH RUNTIME)"
        )
        d["CAIG_GRAPH_NAMESPACE"] = "The custom namespace for the RED graph.  (GRAPH RUNTIME)"
        d["CAIG_GRAPH_SOURCE_OWL_FILENAME"] = "The input RDF OWL ontology file.  (GRAPH RUNTIME)"
        d["CAIG_GRAPH_SOURCE_PATH"] = (
            "The RDF input file or folder, if CAIG_GRAPH_SOURCE_TYPE is 'rdf_file'.  (GRAPH RUNTIME)"
        )
        d["CAIG_GRAPH_SOURCE_DB"] = (
            "The graph Cosmos DB database name, if CAIG_GRAPH_SOURCE_TYPE is 'cosmos_nosql'.  (GRAPH RUNTIME)"
        )
        d["CAIG_GRAPH_SOURCE_CONTAINER"] = (
            "The graph Cosmos DB container name, if CAIG_GRAPH_SOURCE_TYPE is 'cosmos_nosql'.  (GRAPH RUNTIME)"
        )
        d["CAIG_CONFIG_CONTAINER"] = (
            "The Cosmos DB container for configuration JSON values.  (RUNTIME)"
        )
        d["CAIG_CONVERSATIONS_CONTAINER"] = (
            "The Cosmos DB container where the chat conversations and history are persisted.  (WEB RUNTIME)"
        )
        d["CAIG_FEEDBACK_CONTAINER"] = (
            "The Cosmos DB container where user feedback is persisted.  (WEB RUNTIME)"
        )
        d["CAIG_COSMOSDB_NOSQL_ACCT"] = "The Name of your Cosmos DB NoSQL account.  (RUNTIME)"
        d["CAIG_COSMOSDB_NOSQL_RG"] = (
            "The Resource Group of your Cosmos DB NoSQL account.  (DEV ENV)"
        )
        d["CAIG_COSMOSDB_NOSQL_URI"] = "The URI of your Cosmos DB NoSQL account.  (RUNTIME)"
        d["CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM"] = (
            "The Cosmos DB NoSQL authentication mechanism; key or rbac.  (RUNTIME)"
        )
        d["CAIG_COSMOSDB_NOSQL_KEY"] = "The key of your Cosmos DB NoSQL account.  (RUNTIME)"

        d["CAIG_AZURE_OPENAI_URL"] = "The URL of your Azure OpenAI account.  (WEB RUNTIME)"
        d["CAIG_AZURE_OPENAI_KEY"] = "The Key of your Azure OpenAI account.  (WEB RUNTIME)"
        d["CAIG_AZURE_OPENAI_VERSION"] = "The Version of your Azure OpenAI account.  (WEB RUNTIME)"
        d["CAIG_AZURE_OPENAI_COMPLETIONS_DEP"] = (
            "The name of your Azure OpenAI completions deployment.  (WEB RUNTIME)"
        )
        d["CAIG_AZURE_OPENAI_EMBEDDINGS_DEP"] = (
            "The name of your Azure OpenAI embeddings deployment.  (WEB RUNTIME)"
        )
        d["CAIG_WEB_APP_NAME"] = "Logical name.  (DEV ENV)"
        d["CAIG_WEB_APP_URL"] = "http://127.0.0.1 or determined by ACA.  (WEB RUNTIME)"
        d["CAIG_WEB_APP_PORT"] = "8000  (WEB RUNTIME)"
        d["CAIG_GRAPH_SERVICE_NAME"] = "Logical app name.  (DEV ENV)"
        d["CAIG_GRAPH_SERVICE_URL"] = "http://127.0.0.1 or determined by ACA.  (WEB RUNTIME)"
        d["CAIG_GRAPH_SERVICE_PORT"] = "8002  (WEB RUNTIME)"
        d["CAIG_GRAPH_DUMP_UPON_BUILD"] = (
            "Boolean true/false to dump the Java/Jena model to CAIG_GRAPH_DUMP_OUTFILE.  (GRAPH RUNTIME)"
        )
        d["CAIG_GRAPH_DUMP_OUTFILE"] = (
            "The file to write to if CAIG_GRAPH_DUMP_UPON_BUILD is true.  (GRAPH RUNTIME)"
        )
        d["CAIG_WEBSVC_AUTH_HEADER"] = "Name of the custom HTTP authentication header; defaults to 'x-caig-auth'.  (RUNTIME)"
        d["CAIG_WEBSVC_AUTH_VALUE"] = "your-secret-value  (RUNTIME)"
        d["CAIG_LOG_LEVEL"] = (
            "A standard python or java logging level name.  (RUNTIME)"
        )
        d["CAIG_PROMPT_SPARQL_PATH"] = "Path to SPARQL generation prompt .txt file. (WEB RUNTIME)"
        d["CAIG_PROMPT_COMPLETION_PATH"] = "Path to completion prompt .txt file. (WEB RUNTIME)"
        return d

    @classmethod
    def graph_runtime_environment_variables(cls) -> list:
        return cls.filter_environment_variables(
            ["(GRAPH RUNTIME)", "(RUNTIME)"])

    @classmethod
    def web_runtime_environment_variables(cls) -> list:
        return cls.filter_environment_variables(
            ["(WEB RUNTIME)", "(RUNTIME)"])
    
    @classmethod
    def filter_environment_variables(cls, literals: list) -> list:
        all_vars = cls.defined_environment_variables()
        runtime_vars = dict()
        for name in all_vars.keys():
            desc = all_vars[name]
            for lit in literals:
                if lit in desc:
                    runtime_vars[name] = desc
        return sorted(runtime_vars.keys())
    
    @classmethod
    def sample_environment_variable_values(cls) -> dict:
        d = dict()
        d["CAIG_HOME"] = ""
        d["CAIG_AZURE_REGION"] = "eastus"
        d["CAIG_GRAPH_NAMESPACE"] = ""
        d["CAIG_GRAPH_SOURCE_TYPE"] = "cosmos_nosql"
        d["CAIG_GRAPH_SOURCE_OWL_FILENAME"] = "ontologies/extracted_ontology.ttl"
        # d["CAIG_GRAPH_SOURCE_PATH"] = ""
        d["CAIG_GRAPH_SOURCE_DB"] = "caig"
        d["CAIG_GRAPH_SOURCE_CONTAINER"] = "libraries"
        d["CAIG_GRAPH_DUMP_UPON_BUILD"] = "false"
        d["CAIG_GRAPH_DUMP_OUTFILE"] = ""
        d["CAIG_CONFIG_CONTAINER"] = "config"
        d["CAIG_CONVERSATIONS_CONTAINER"] = "conversations"
        d["CAIG_COSMOSDB_NOSQL_ACCT"] = "mycosmosdbnosqlacct"
        d["CAIG_COSMOSDB_NOSQL_RG"] = "myresourcegroup"
        d["CAIG_COSMOSDB_NOSQL_URI"] = "https://<your-account>.documents.azure.com:443/"
        d["CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM"] = "key"
        d["CAIG_COSMOSDB_NOSQL_KEY"] = ""
        d["CAIG_AZURE_OPENAI_URL"] = ""
        d["CAIG_AZURE_OPENAI_KEY"] = ""
        d["CAIG_AZURE_OPENAI_COMPLETIONS_DEP"] = "gpt4o"
        d["CAIG_AZURE_OPENAI_EMBEDDINGS_DEP"] = "embeddings"
        d["CAIG_WEB_APP_NAME"] = "caig-web"
        d["CAIG_WEB_APP_URL"] = "http://127.0.0.1"
        d["CAIG_WEB_APP_PORT"] = "8000"
        d["CAIG_GRAPH_SERVICE_NAME"] = "caig-graph"
        d["CAIG_GRAPH_SERVICE_URL"] = "http://127.0.0.1"
        d["CAIG_GRAPH_SERVICE_PORT"] = "8001"
        d["CAIG_LOG_LEVEL"] = "info"
        d["CAIG_PROMPT_SPARQL_PATH"] = "prompts/gen_sparql_generic.txt"
        d["CAIG_PROMPT_COMPLETION_PATH"] = "prompts/gen_completion_generic.txt"
        return d

    @classmethod
    def log_defined_env_vars(cls):
        """Log the defined CAIG_ environment variables as JSON"""
        keys = sorted(cls.defined_environment_variables().keys())
        selected = dict()
        for key in keys:
            value = cls.envvar(key)
            selected[key] = value
        logging.info(
            "log_defined_env_vars: {}".format(
                json.dumps(selected, sort_keys=True, indent=2)
            )
        )

    @classmethod
    def print_defined_env_vars(cls):
        """print() the defined CAIG_ environment variables as JSON"""
        keys = sorted(cls.defined_environment_variables().keys())
        selected = dict()
        for key in keys:
            value = cls.envvar(key)
            selected[key] = value
        print(
            "print_defined_env_vars: {}".format(
                json.dumps(selected, sort_keys=True, indent=2)
            )
        )

    @classmethod
    def graph_service_port(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SERVICE_PORT", "8001")

    @classmethod
    def graph_service_url(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SERVICE_URL", "http://127.0.0.1")

    @classmethod
    def prompt_sparql(cls) -> str:
        return cls.envvar("CAIG_PROMPT_SPARQL_PATH", "prompts/gen_sparql_generic.txt")

    @classmethod
    def prompt_completion(cls) -> str:
        return cls.envvar("CAIG_PROMPT_COMPLETION_PATH", "prompts/gen_completion_generic.txt")

    @classmethod
    def graph_service_ontology_url(cls) -> str:
        return "{}:{}/ontology".format(
            cls.graph_service_url(), cls.graph_service_port()
        ).strip()

    @classmethod
    def graph_source(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SOURCE_TYPE", "cosmos_nosql")

    @classmethod
    def graph_source_owl_filename(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SOURCE_OWL_FILENAME", "ontologies/extracted_ontology.ttl")

    @classmethod
    def graph_source_path(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SOURCE_PATH", "")

    @classmethod
    def graph_source_db(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SOURCE_DB", "caig")

    @classmethod
    def graph_source_container(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SOURCE_CONTAINER", "libraries")

    @classmethod
    def config_container(cls) -> str:
        return cls.envvar("CAIG_CONFIG_CONTAINER", "config")

    @classmethod
    def conversations_container(cls) -> str:
        return cls.envvar("CAIG_CONVERSATIONS_CONTAINER", "conversations")

    @classmethod
    def feedback_container(cls) -> str:
        return cls.envvar("CAIG_FEEDBACK_CONTAINER", "feedback")

    @classmethod
    def cosmosdb_nosql_uri(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_URI", None)

    @classmethod
    def cosmosdb_nosql_auth_mechanism(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM", "key").lower()

    @classmethod
    def cosmosdb_nosql_key(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_KEY", None)

    @classmethod
    def azure_openai_url(cls) -> str:
        return cls.envvar("CAIG_AZURE_OPENAI_URL", None)

    @classmethod
    def azure_openai_key(cls) -> str:
        return cls.envvar("CAIG_AZURE_OPENAI_KEY", None)

    @classmethod
    def azure_openai_version(cls) -> str:
        return cls.envvar("CAIG_AZURE_OPENAI_VERSION", "2023-12-01-preview")

    @classmethod
    def azure_openai_completions_deployment(cls) -> str:
        return cls.envvar("CAIG_AZURE_OPENAI_COMPLETIONS_DEP", "gpt4")

    @classmethod
    def azure_openai_embeddings_deployment(cls) -> str:
        return cls.envvar("CAIG_AZURE_OPENAI_EMBEDDINGS_DEP", "embeddings")

    @classmethod
    def optimize_context_and_history_max_tokens(cls) -> int:
        return cls.int_envvar("CAIG_OPTIMIZE_CONTEXT_AND_HISTORY_MAX_TOKENS", 10000)

    @classmethod
    def get_model_context_window(cls, deployment_name: str | None = None) -> int:
        """
        Get the context window size for a given model/deployment.
        Returns the token limit based on the model name.
        """
        if deployment_name is None:
            deployment_name = cls.azure_openai_completions_deployment()
        
        # Normalize the deployment name to lowercase for comparison
        model_name = deployment_name.lower()
        
        # Map model names to their context windows
        # Source: https://platform.openai.com/docs/models
        if "gpt-4o" in model_name or "gpt4o" in model_name:
            return 128000  # GPT-4o and GPT-4o-mini: 128K tokens
        elif "gpt-4-turbo" in model_name or "gpt4turbo" in model_name:
            return 128000  # GPT-4 Turbo: 128K tokens
        elif "gpt-4-32k" in model_name:
            return 32768   # GPT-4-32K: 32K tokens
        elif "gpt-4" in model_name or "gpt4" in model_name:
            # Check for GPT-4.1 (1M tokens) or standard GPT-4 (8K)
            if "4.1" in model_name or "41" in model_name:
                return 1000000  # GPT-4.1: 1M tokens
            return 8192    # Standard GPT-4: 8K tokens
        elif "gpt-35-turbo-16k" in model_name or "gpt-3.5-turbo-16k" in model_name:
            return 16384   # GPT-3.5-Turbo-16K: 16K tokens
        elif "gpt-35-turbo" in model_name or "gpt-3.5-turbo" in model_name:
            return 16384   # GPT-3.5-Turbo: 16K tokens (updated models)
        else:
            # Default fallback for unknown models
            return 8192

    @classmethod
    def invoke_kernel_max_tokens(cls) -> int:
        """
        Calculate the maximum tokens for invoke_kernel based on the model's context window.
        Uses env var if set, otherwise auto-calculates from model context window.
        Reserves space for: system prompt (~1K), response (~4K), and safety margin (10%).
        """
        # Allow override via environment variable
        env_value = cls.int_envvar("CAIG_INVOKE_KERNEL_MAX_TOKENS", -1)
        if env_value > 0:
            return env_value
        
        # Auto-calculate based on model's context window
        context_window = cls.get_model_context_window()
        
        # Reserve tokens for response and other prompt parts
        response_tokens = 4096      # Reserve for LLM response
        system_prompt_tokens = 1024 # Reserve for system prompt
        safety_margin = int(context_window * 0.1)  # 10% safety margin
        
        max_tokens = context_window - response_tokens - system_prompt_tokens - safety_margin
        
        # Ensure we have a reasonable minimum
        return max(max_tokens, 4096)

    @classmethod
    def invoke_kernel_temperature(cls) -> float:
        return cls.float_envvar("CAIG_INVOKE_KERNEL_TEMPERATURE", 0.4)

    @classmethod
    def moderate_sparql_temperature(cls) -> float:
        return cls.float_envvar("CAIG_MODERATE_SPARQL_TEMPERATURE", 0.0)

    @classmethod
    def get_completion_temperature(cls) -> float:
        return cls.float_envvar("CAIG_GET_COMPLETION_TEMPERATURE", 0.0)

    @classmethod
    def invoke_kernel_top_p(cls) -> float:
        return cls.float_envvar("CAIG_INVOKE_KERNEL_TOP_P", 1.0)

    @classmethod
    def graph_namespace(cls):
        """ " return a URI value like 'http://cosmosdb.com/caig#'"""
        default = "http://cosmosdb.com/caig#"
        return cls.envvar("CAIG_GRAPH_NAMESPACE", default)

    @classmethod
    def graph_namespace_alias(cls):
        """return the value 'xxx' for the namespace 'http://cosmosdb.com/xxx#'"""
        return cls.graph_namespace().split("/")[-1].replace("#", "").strip()

    @classmethod
    def websvc_auth_header(cls):
        return cls.envvar("CAIG_WEBSVC_AUTH_HEADER", "x-caig-auth")

    @classmethod
    def websvc_auth_value(cls):
        return cls.envvar("CAIG_WEBSVC_AUTH_VALUE", "K6ZQw!81<26>")

    @classmethod
    def truncate_llm_context_max_ntokens(cls) -> int:
        """
        Zero indicates no truncation.
        A positive integer is the max number of tokens.
        """
        return cls.int_envvar("CAIG_TRUNCATE_LLM_CONTEXT_MAX_NTOKENS", 0)

    @classmethod
    def epoch(cls) -> float:
        """Return the current epoch time, as time.time()"""
        return time.time()

    @classmethod
    def verbose(cls, override_flags: list = None) -> bool:
        """Return a boolean indicating if --verbose or -v is in the command-line."""
        flags = ["--verbose", "-v"] if override_flags is None else override_flags
        # true_value if condition else false_value
        for arg in sys.argv:
            for flag in flags:
                if arg == flag:
                    return True
        return False

    @classmethod
    def generate_fernet_key(cls) -> str:
        return str(Fernet.generate_key().decode("utf-8"))

    @classmethod
    def set_standard_unit_test_env_vars(cls):
        """Set environment variables for use in unit tests"""
        os.environ["CAIG_GRAPH_SOURCE_TYPE"] = "rdf_file"
        os.environ["CAIG_GRAPH_SOURCE_OWL_FILENAME"] = "ontologies/extracted_ontology.ttl"
        # os.environ["CAIG_GRAPH_SOURCE_PATH"] = ""
        os.environ["CAIG_WEBSVC_AUTH_VALUE"] = "123go"
        os.environ["SAMPLE_INT_VAR"] = "98"
        os.environ["SAMPLE_FLOAT_VAR"] = "98.6"
        os.environ["SAMPLE_BOOLEAN_TRUE_VAR"] = "TRue"
        os.environ["SAMPLE_BOOLEAN_FALSE_VAR"] = "F"

    @classmethod
    def get_strategy_bypass(cls) -> str:
        return cls.envvar("CAIG_STRATEGY_BYPASS", "false")