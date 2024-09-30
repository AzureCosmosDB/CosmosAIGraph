import json
import logging
import os
import sys
import time

# Instances of this class are used to define and obtain all configuration
# values in this solution.  These are typically obtained at runtime via
# environment variables.
# Chris Joakim, Microsoft


class ConfigService:

    @classmethod
    def envvar(cls, name: str, default: str = "") -> str:
        """
        Return the value of the given environment variable name,
        or the given default value."""
        if name in os.environ:
            return os.environ[name]
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
    def code_version(cls) -> str:
        return "2024/09/30"

    @classmethod
    def defined_environment_variables(cls) -> dict:
        """
        Return a dict with the defined environment variable names and descriptions
        """
        d = dict()
        d["CAIG_HOME"] = (
            "Root directory of the CosmosAIGraph GitHub repository on your system"
        )
        d["CAIG_AZURE_REGION"] = "The Azure region where the ACA app is deployed to"
        d["CAIG_GRAPH_SOURCE_TYPE"] = (
            "The RDF graph data source type, either 'rdf_file' or 'cosmos_vcore' or 'cosmos_nosql'"
        )
        d["CAIG_GRAPH_NAMESPACE"] = "The custom namespace for the RED graph"
        d["CAIG_GRAPH_SOURCE_OWL_FILENAME"] = "The input RDF OWL ontology file"
        d["CAIG_GRAPH_SOURCE_RDF_FILENAME"] = (
            "The RDF input file, if CAIG_GRAPH_SOURCE_TYPE is 'rdf_file'"
        )
        d["CAIG_GRAPH_SOURCE_DB"] = (
            "The graph vCore database name, if CAIG_GRAPH_SOURCE_TYPE is 'cosmos_vcore'"
        )
        d["CAIG_GRAPH_SOURCE_CONTAINER"] = (
            "The graph vCore container name, if CAIG_GRAPH_SOURCE_TYPE is 'cosmos_vcore'"
        )
        d["CAIG_CONFIG_CONTAINER"] = "The vCore container for configuration JSON values"
        d["CAIG_CONVERSATIONS_CONTAINER"] = (
            "The vCore container where the chat conversations and history are persisted"
        )
        d["CAIG_FEEDBACK_CONTAINER"] = (
            "The vCore container where user feedback is persisted"
        )
        d["CAIG_AZURE_MONGO_VCORE_CONN_STR"] = (
            "The full connection string for the Cosmos DB Mongo vCore account"
        )
        d["CAIG_COSMOSDB_NOSQL_ACCT"] = "The Name of your Cosmos DB NoSQL account"
        d["CAIG_COSMOSDB_NOSQL_RG"] = "The Resource Group of your Cosmos DB NoSQL account"
        d["CAIG_COSMOSDB_NOSQL_URI"] = "The URI of your Cosmos DB NoSQL account"
        d["CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM"] = "The Cosmos DB NoSQL authentication mechanism; key or aad"
        d["CAIG_COSMOSDB_NOSQL_KEY1"] = "The key of your Cosmos DB NoSQL account"
        d["CAIG_COSMOSDB_NOSQL_PRIN_OBJ_ID"] = "Principal Oject ID for Cosmos DB NoSQL AAD Authentication"
        d["CAIG_COSMOSDB_NOSQL_RBAC_ROLE_ID"] = "RBAC Role ID for Cosmos DB NoSQL AAD Authentication"

        d["CAIG_AZURE_OPENAI_URL"] = "The URL of your Azure OpenAI account"
        d["CAIG_AZURE_OPENAI_KEY"] = "The Key of your Azure OpenAI account"
        d["CAIG_AZURE_OPENAI_COMPLETIONS_DEP"] = (
            "The name of your Azure OpenAI completions deployment"
        )
        d["CAIG_AZURE_OPENAI_EMBEDDINGS_DEP"] = (
            "The name of your Azure OpenAI embeddings deployment"
        )
        d["CAIG_ACA_ENVIRONMENT_NAME"] = (
            "The Azure Container App (ACA) environment name"
        )
        d["CAIG_LA_WORKSPACE_NAME"] = (
            "The Log Analytics workspace name used by the Azure Container App (ACA)"
        )
        d["CAIG_DEFINED_AUTH_USERS"] = ""
        d["CAIG_WEB_APP_NAME"] = ""
        d["CAIG_WEB_APP_URL"] = ""
        d["CAIG_WEB_APP_PORT"] = ""
        d["CAIG_GRAPH_SERVICE_NAME"] = ""
        d["CAIG_GRAPH_SERVICE_URL"] = ""
        d["CAIG_GRAPH_SERVICE_PORT"] = ""

        # These three are experimental; possible future use
        d["CAIG_PG_FLEX_SERVER"] = "Azure PostgreSQL Flex Server hostname"
        d["CAIG_PG_FLEX_USER"] = "Azure PostgreSQL Flex Server user"
        d["CAIG_PG_FLEX_PASS"] = "Azure PostgreSQL Flex Server user password"

        d["CAIG_WEBSVC_AUTH_HEADER"] = "x-caig-auth"
        d["CAIG_WEBSVC_AUTH_VALUE"] = "K6ZQw!81"

        d["CAIG_LOG_LEVEL"] = (
            "a python logging standard-lib level name: notset, debug, info, warning, error, or critical"
        )
        return d

    @classmethod
    def sample_environment_variable_values(cls) -> dict:
        d = dict()
        d["CAIG_HOME"] = ""
        d["CAIG_AZURE_REGION"] = "eastus"
        d["CAIG_GRAPH_NAMESPACE"] = "http://cosmosdb.com/caig#"
        d["CAIG_GRAPH_SOURCE_TYPE"] = "cosmos_vcore"
        d["CAIG_GRAPH_SOURCE_OWL_FILENAME"] = "ontologies/libraries.owl"
        d["CAIG_GRAPH_SOURCE_RDF_FILENAME"] = "rdf/libraries-graph.nt"
        d["CAIG_GRAPH_SOURCE_DB"] = "caig"
        d["CAIG_GRAPH_SOURCE_CONTAINER"] = "libraries"
        d["CAIG_CONFIG_CONTAINER"] = "config"
        d["CAIG_CONVERSATIONS_CONTAINER"] = "conversations"
        d["CAIG_AZURE_MONGO_VCORE_CONN_STR"] = "mongodb+srv://..."

        d["CAIG_COSMOSDB_NOSQL_ACCT"] = "mycosmosdbnosqlacct"
        d["CAIG_COSMOSDB_NOSQL_RG"]   = "myresourcegroup"
        d["CAIG_COSMOSDB_NOSQL_URI"]  = "https://<your-account>.documents.azure.com:443/"
        d["CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM"] = "key"  # key or aad
        d["CAIG_COSMOSDB_NOSQL_KEY1"] = ""
        d["CAIG_COSMOSDB_NOSQL_PRIN_OBJ_ID"] = ""
        d["CAIG_COSMOSDB_NOSQL_RBAC_ROLE_ID"] = ""

        d["CAIG_USE_ALT_SPARQL_CONSOLE"] = ""
        d["CAIG_AZURE_OPENAI_URL"] = ""
        d["CAIG_AZURE_OPENAI_KEY"] = ""
        d["CAIG_AZURE_OPENAI_COMPLETIONS_DEP"] = "gpt4"
        d["CAIG_AZURE_OPENAI_EMBEDDINGS_DEP"] = "embeddings"
        d["CAIG_DEFINED_AUTH_USERS"] = "guest:secret"
        d["CAIG_ACA_ENVIRONMENT_NAME"] = "caig"
        d["CAIG_LA_WORKSPACE_NAME"] = "caig"
        d["CAIG_WEB_APP_NAME"] = "caig-web"
        d["CAIG_WEB_APP_URL"] = "http://127.0.0.1"
        d["CAIG_WEB_APP_PORT"] = "8000"
        d["CAIG_GRAPH_SERVICE_NAME"] = "caig-graph"
        d["CAIG_GRAPH_SERVICE_URL"] = "http://graph_service"
        d["CAIG_GRAPH_SERVICE_PORT"] = "8001"
        d["CAIG_LOG_LEVEL"] = "info"
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
    def using_nosql(cls) -> str:
        db_api = cls.envvar("CAIG_GRAPH_SOURCE_TYPE", "cosmos_vcore").lower()
        return "cosmos_nosql" in db_api

    @classmethod
    def using_vcore(cls) -> str:
        db_api = cls.envvar("CAIG_GRAPH_SOURCE_TYPE", "cosmos_vcore").lower()
        return "cosmos_vcore" in db_api

    @classmethod
    def graph_source(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SOURCE_TYPE", "cosmos_vcore")

    @classmethod
    def graph_source_owl_filename(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SOURCE_OWL_FILENAME", "ontologies/libraries.owl")

    @classmethod
    def graph_source_rdf_filename(cls) -> str:
        return cls.envvar("CAIG_GRAPH_SOURCE_RDF_FILENAME", "rdf/libraries-graph.nt")

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
    def mongo_vcore_conn_str(cls) -> str:
        return cls.envvar("CAIG_AZURE_MONGO_VCORE_CONN_STR", None)

    @classmethod
    def cosmosdb_nosql_acct(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_ACCT", None)
    
    @classmethod
    def cosmosdb_nosql_resource_group(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_RG", None)
    
    @classmethod
    def cosmosdb_nosql_uri(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_URI", None)

    @classmethod
    def cosmosdb_nosql_auth_mechanism(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_AUTH_MECHANISM", None)
    
    @classmethod
    def cosmosdb_nosql_key1(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_KEY1", None)

    @classmethod
    def cosmosdb_nosql_principal_object_id(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_PRIN_OBJ_ID", None)
    
    @classmethod
    def cosmosdb_nosql_rbac_role_id(cls) -> str:
        return cls.envvar("CAIG_COSMOSDB_NOSQL_RBAC_ROLE_ID", None)
    
    @classmethod
    def pg_flex_server(cls) -> str:
        return cls.envvar("CAIG_PG_FLEX_SERVER", None)

    @classmethod
    def pg_flex_user(cls) -> str:
        return cls.envvar("CAIG_PG_FLEX_USER", None)

    @classmethod
    def pg_flex_password(cls) -> str:
        return cls.envvar("CAIG_PG_FLEX_PASS", None)

    @classmethod
    def use_alt_sparql_console(cls) -> str:
        return len(cls.envvar("CAIG_USE_ALT_SPARQL_CONSOLE", "")) > 0

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
    def html_summarize_max_tokens(cls) -> str:
        return cls.int_envvar("CAIG_HTML_SUMMARIZE_MAX_TOKENS", 2000)

    @classmethod
    def html_summarize_temperature(cls) -> str:
        return cls.float_envvar("CAIG_HTML_SUMMARIZE_TEMPERATURE", 0.7)

    @classmethod
    def html_summarize_top_p(cls) -> str:
        return cls.float_envvar("CAIG_HTML_SUMMARIZE_TOP_P", 0.8)

    @classmethod
    def optimize_context_and_history_max_tokens(cls) -> str:
        return cls.int_envvar("CAIG_OPTIMIZE_CONTEXT_AND_HISTORY_MAX_TOKENS", 10000)

    @classmethod
    def invoke_kernel_max_tokens(cls) -> str:
        return cls.int_envvar("CAIG_INVOKE_KERNEL_MAX_TOKENS", 4096)

    @classmethod
    def invoke_kernel_temperature(cls) -> str:
        return cls.float_envvar("CAIG_INVOKE_KERNEL_TEMPERATURE", 0.4)

    @classmethod
    def generate_graph_temperature(cls) -> str:
        return cls.float_envvar("CAIG_GENERATE_GRAPH_TEMPERATURE", 0.0)

    @classmethod
    def moderate_sparql_temperature(cls) -> str:
        return cls.float_envvar("CAIG_MODERATE_SPARQL_TEMPERATURE", 0.0)

    @classmethod
    def get_completion_temperature(cls) -> str:
        return cls.float_envvar("CAIG_GET_COMPLETION_TEMPERATURE", 0.1)

    @classmethod
    def invoke_kernel_top_p(cls) -> str:
        return cls.float_envvar("CAIG_INVOKE_KERNEL_TOP_P", 0.5)

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
    def use_msal_auth(cls):
        return cls.envvar("CAIG_MSAL_AUTH", False)

    @classmethod
    def msal_client_id(cls):
        return cls.envvar("CAIG_MSAL_CLIENT_ID", None)

    @classmethod
    def msal_client_credential(cls):
        return cls.envvar("CAIG_MSAL_CLIENT_CRED", None)

    @classmethod
    def msal_tenant(cls):
        return cls.envvar("CAIG_MSAL_TENANT", None)

    @classmethod
    def msal_ssh_key(cls):
        """obtain the SSH key from an environment variable or a file"""
        key = cls.envvar("CAIG_MSAL_SSH_KEY", None)
        if key is None:
            key_filename = cls.envvar("CAIG_MSAL_SSH_KEY_FILE", None)
            if key_filename is not None:
                if os.path.isfile(key_filename):
                    with open(file=key_filename, mode="rt") as file:
                        return file.read()
                else:
                    return None
            else:
                return None
        else:
            return key

    @classmethod
    def websvc_auth_header(cls):
        return cls.envvar("CAIG_WEBSVC_AUTH_HEADER", "x-caig-auth")

    @classmethod
    def websvc_auth_value(cls):
        return cls.envvar("CAIG_WEBSVC_AUTH_VALUE", "K6ZQw!81")

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
    def set_standard_unit_test_env_vars(cls):
        """Set environment variables for use in unit tests"""
        os.environ["CAIG_GRAPH_SOURCE_TYPE"] = "rdf_file"
        os.environ["CAIG_GRAPH_SOURCE_OWL_FILENAME"] = "ontologies/libraries.owl"
        os.environ["CAIG_GRAPH_SOURCE_RDF_FILENAME"] = "rdf/libraries-graph-mini.nt"
        # os.environ["CAIG_MSAL_SSH_KEY_FILE"] = "keys/example-msal-ssh-key.txt"
        os.environ["SAMPLE_INT_VAR"] = "98"
        os.environ["SAMPLE_FLOAT_VAR"] = "98.6"
        os.environ["SAMPLE_BOOLEAN_TRUE_VAR"] = "TRue"
        os.environ["SAMPLE_BOOLEAN_FALSE_VAR"] = "F"
