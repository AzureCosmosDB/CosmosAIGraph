import json

from semantic_kernel.contents.chat_history import ChatHistory

from src.services.ai_conversation import AiConversation
from src.util.fs import FS

# pytest -v tests/test_ai_conversation.py

def test_chat_history():
    """ This test just explores and verifies the SK ChatHistory functionality. """
    hist1 = ChatHistory()
    hist1.add_user_message("this is a user message")
    hist1.add_system_message("this is a system message")
    hist1.add_assistant_message("this is an assistant message")
    hist1.add_tool_message("this is an assistant message")
    jstr = hist1.serialize()
    print(jstr)
    assert len(hist1.messages) == 4

    hist2 = ChatHistory.restore_chat_history(jstr)
    assert len(hist2.messages) == 4

def test_constructor_and_messages():
    conv1 = AiConversation()
    conv1.add_user_message("this is a user message")
    conv1.add_system_message("this is a system message")
    conv1.add_assistant_message("this is an assistant message")
    conv1.add_tool_message("this is an assistant message")

    jstr = conv1.serialize()
    print(jstr)
    assert jstr is not None
    json_obj = json.loads(jstr)
    assert json_obj["conversation_id"] is not None
    assert json_obj["chat_history"] is not None
    assert len(json_obj["chat_history"]["messages"]) == 4

    conv2 = AiConversation(json_obj)
    assert conv1.get_conversation_id() == conv2.get_conversation_id()
    assert conv1.get_message_count() == conv2.get_message_count()
    assert conv2.get_message_count() == 4

    conv2.add_user_message("this is another user message")
    conv3 = AiConversation(json.loads(conv2.serialize()))
    assert conv3.get_message_count() == 5
    assert conv1.get_conversation_id() == conv3.get_conversation_id()

    print(conv3.serialize())
    FS.write_json(json.loads(conv3.serialize()), "tmp/test_ai_conversation_conv3.json")

    ai_config = conv3.ai_config
    assert ai_config is not None
    assert "completions_deployment" in ai_config.keys()
    assert "embeddings_deployment" in ai_config.keys()
    assert "invoke_kernel_max_tokens" in ai_config.keys()
    assert "invoke_kernel_temperature" in ai_config.keys()
    assert "invoke_kernel_top_p" in ai_config.keys()
    assert "html_summarize_max_tokens" in ai_config.keys()
    assert "html_summarize_temperature" in ai_config.keys()
    assert "html_summarize_top_p" in ai_config.keys()
    assert "get_completion_temperature" in ai_config.keys()
    assert "moderate_sparql_temperature" in ai_config.keys()
    assert "optimize_context_and_history_max_tokens" in ai_config.keys()
    assert "truncate_llm_context_max_ntokens" in ai_config.keys()
    assert "generate_graph_temperature" in ai_config.keys()

    assert ai_config["embeddings_deployment"] == "embeddings"
    assert ai_config["html_summarize_temperature"] == 0.7

    # the ai_config attribute of an AiConversation looks like this:
    # "ai_config": {
    #     "completions_deployment": "gpt4",
    #     "embeddings_deployment": "embeddings",
    #     "invoke_kernel_max_tokens": 4096,
    #     "invoke_kernel_temperature": 0.4,
    #     "invoke_kernel_top_p": 0.5,
    #     "html_summarize_max_tokens": 2000,
    #     "html_summarize_temperature": 0.7,
    #     "html_summarize_top_p": 0.8,
    #     "get_completion_temperature": 0.1,
    #     "moderate_sparql_temperature": 0.0,
    #     "optimize_context_and_history_max_tokens": 10000,
    #     "truncate_llm_context_max_ntokens": 0,
    #     "generate_graph_temperature": 0.0
    # }

def test_truncate_context_and_history():
    pass
