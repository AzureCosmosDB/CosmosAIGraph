import os
import sys
import pytest

from src.services.config_service import ConfigService

# pytest -v tests/test_config_service.py

def test_envvar():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.envvar("CAIG_GRAPH_SOURCE_TYPE") == "rdf_file"
    assert ConfigService.envvar("MISSING") == ""
    assert ConfigService.envvar("MISSING", None) == None
    assert ConfigService.envvar("UNIVERSAL_ANSWER", "42") == "42"

def test_int_envvar():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.int_envvar("SAMPLE_INT_VAR") == 98
    assert ConfigService.int_envvar("MISSING") == -1
    assert ConfigService.int_envvar("CAIG_GRAPH_SOURCE_TYPE") == -1
    assert ConfigService.int_envvar("MISSING", 13) == 13

def test_float_envvar():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.float_envvar("SAMPLE_FLOAT_VAR") == 98.6
    assert ConfigService.float_envvar("MISSING") == -1.0
    assert ConfigService.float_envvar("CAIG_GRAPH_SOURCE_TYPE") == -1.0
    assert ConfigService.float_envvar("MISSING", 13.1) == 13.1

def test_boolean_envvar():
    ConfigService.set_standard_unit_test_env_vars()
    os.environ["TRUE_ARG"]  = "TRuE"
    os.environ["FALSE_ARG"] = "FALse"
    os.environ["T_ARG"] = "t"
    os.environ["F_ARG"] = "F"
    os.environ["YES_ARG"] = "yeS"
    os.environ["Y_ARG"] = "Y"
    os.environ["N_ARG"] = "N"
    assert ConfigService.boolean_envvar("MISSING", True) == True
    assert ConfigService.boolean_envvar("MISSING", False) == False
    assert ConfigService.boolean_envvar("TRUE_ARG", False) == True
    assert ConfigService.boolean_envvar("FALSE_ARG", True) == False
    assert ConfigService.boolean_envvar("T_ARG", False) == True
    assert ConfigService.boolean_envvar("F_ARG", True) == False
    assert ConfigService.boolean_envvar("YES_ARG", False) == True
    assert ConfigService.boolean_envvar("Y_ARG", False) == True
    assert ConfigService.boolean_envvar("N_ARG", True) == False

def test_boolean_arg():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.boolean_arg(sys.argv[0]) == True
    assert ConfigService.boolean_arg("MISSING") == False

def test_defined_environment_variables():
    envvars = ConfigService.defined_environment_variables()
    assert "CAIG_GRAPH_SOURCE_TYPE" in envvars.keys()
    assert len(envvars.keys()) > 28
    assert len(envvars.keys()) < 48

def test_sample_environment_variable_values():
    envvars = ConfigService.sample_environment_variable_values()
    assert "CAIG_GRAPH_SOURCE_TYPE" in envvars.keys()
    assert len(envvars.keys()) > 25
    assert len(envvars.keys()) < 45
    assert envvars["CAIG_GRAPH_NAMESPACE"] == "http://cosmosdb.com/caig#"

def test_log_defined_env_vars():
    try:
        ConfigService.log_defined_env_vars()
        assert True
    except Exception as e:
        assert False

def test_graph_namespace():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.graph_namespace() == "http://cosmosdb.com/caig#"

def test_graph_namespace_alias():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.graph_namespace_alias() == "caig"

def test_graph_source():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.graph_source() == "rdf_file"

def test_graph_source_owl_filename():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.graph_source_owl_filename() == "ontologies/libraries.owl"

def test_graph_source_rdf_filename():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.graph_source_rdf_filename() == "rdf/libraries-graph-mini.nt"


def test_graph_source_db():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.graph_source_db() == "caig"


def test_graph_source_container():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.graph_source_container() == "libraries"


def test_feedback_container():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.feedback_container() == "feedback"

def test_mongo_vcore_conn_str():
    ConfigService.set_standard_unit_test_env_vars()
    val = ConfigService.mongo_vcore_conn_str()
    assert val != None
    assert val.startswith("mongodb+srv://")
    assert ".mongocluster.cosmos.azure.com" in val


def test_azure_openai_url():
    ConfigService.set_standard_unit_test_env_vars()
    val = ConfigService.azure_openai_url()
    assert val != None
    assert val.startswith("https://")
    assert ".openai.azure.com/" in val


def test_azure_openai_key():
    ConfigService.set_standard_unit_test_env_vars()
    val = ConfigService.azure_openai_key()
    assert val != None
    assert len(val) > 30
    assert len(val) < 50


def test_azure_openai_version():
    ConfigService.set_standard_unit_test_env_vars()
    val = ConfigService.azure_openai_version()
    assert val.startswith("2023")


def test_azure_openai_deployment_names():
    ConfigService.set_standard_unit_test_env_vars()
    completions = ConfigService.azure_openai_completions_deployment()
    embeddings = ConfigService.azure_openai_embeddings_deployment()
    assert completions == "gpt4"
    assert embeddings == "embeddings"


def test_use_alt_sparql_console():
    ConfigService.set_standard_unit_test_env_vars()
    envvar = ConfigService.envvar("CAIG_USE_ALT_SPARQL_CONSOLE")
    bool = ConfigService.use_alt_sparql_console()
    if len(envvar) == 0:
        assert bool == False
    else:
        assert bool == True

def test_invoke_kernel_max_tokens():
    ConfigService.set_standard_unit_test_env_vars()
    val = ConfigService.invoke_kernel_max_tokens()
    assert val > 100
    assert val < 100_000

def test_invoke_kernel_top_p():
    ConfigService.set_standard_unit_test_env_vars()
    val = ConfigService.invoke_kernel_top_p()
    assert val == 0.5

def test_invoke_kernel_temperature():
    ConfigService.set_standard_unit_test_env_vars()
    val = ConfigService.invoke_kernel_temperature()
    assert val == 0.4

def test_use_msal_auth():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.use_msal_auth() == False

def test_msal_client_id():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.msal_client_id() == None

def test_msal_client_credential():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.msal_client_credential() == None

def test_msal_tenant():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.msal_tenant() == None

def test_msal_ssh_key():

    # case 1: MSAL is disabled due to no envvars set
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.msal_ssh_key() == None

    # case 2: MSAL is enabled with ssh key file
    os.environ["CAIG_MSAL_SSH_KEY_FILE"] = "keys/example-msal-ssh-key.txt"
    key = ConfigService.msal_ssh_key()
    assert key.startswith("-----BEGIN RSA PRIVATE KEY-----")
    assert key.endswith("-----END RSA PRIVATE KEY-----")

    # case 2b: MSAL is disabled due to missing file
    os.environ["CAIG_MSAL_SSH_KEY_FILE"] = "keys/example-msal-ssh-key-not-present.txt"
    assert ConfigService.msal_ssh_key() == None

    # case 3: MSAL is enabled with ssh key env var
    os.environ["CAIG_MSAL_SSH_KEY"] = "777888"
    assert ConfigService.msal_ssh_key() == "777888"

def test_websvc_auth_header():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.websvc_auth_header() == "x-caig-auth"

def test_websvc_auth_value():
    ConfigService.set_standard_unit_test_env_vars()
    assert ConfigService.websvc_auth_value() == "K6ZQw!81"

def test_truncate_llm_context_max_ntokens():
    os.environ["CAIG_TRUNCATE_LLM_CONTEXT_MAX_NTOKENS"] = "0"
    assert 0 == ConfigService.truncate_llm_context_max_ntokens()
    os.environ["CAIG_TRUNCATE_LLM_CONTEXT_MAX_NTOKENS"] = "6789"
    assert 6789 == ConfigService.truncate_llm_context_max_ntokens()

def test_verbose():
    # this is a challenge to test as tests.ps1 contains -v itself!
    # pytest -v --cov=pysrc/ --cov-report html tests/
    if "-v" in sys.argv:
        assert ConfigService.verbose() == True
    else:
        assert ConfigService.verbose() == False

    assert ConfigService.verbose(["-wordy"]) == False

def test_epoch():
    e = ConfigService.epoch()
    assert e > 1717765187  # 2024-06-07
    assert e < 1800000000
