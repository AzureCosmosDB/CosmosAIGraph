import asyncio
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient
from starlette.responses import PlainTextResponse

import impl.web_app.web_app as web_app
from src.services.ai_conversation import AiConversation


class InMemoryNoSQL:
    def __init__(self):
        self.store = {}

    async def initialize(self):
        return None

    async def close(self):
        return None

    def set_db(self, _):
        return None

    def set_container(self, _):
        return None

    async def save_conversation(self, conv: AiConversation):
        self.store[conv.get_conversation_id()] = conv
        return True

    async def load_conversation(self, conv_id: str | None):
        if conv_id and conv_id in self.store:
            return self.store[conv_id]
        return None


class FakeRagDataResult:
    def __init__(self, docs):
        self._docs = docs

    def get_strategy(self):
        return "db"

    def has_db_rag_docs(self) -> bool:
        return True

    def get_rag_docs(self):
        return self._docs

    def get_context(self):
        return ""

    def has_graph_rag_docs(self) -> bool:
        return False

    def get_sparql(self):
        return ""


class FakeRagDataService:
    def __init__(self):
        pass

    async def get_rag_data(self, user_text: str, n: int, override: str | None):
        # Always return DB docs to avoid calling LLM
        return FakeRagDataResult([
            {"id": "d1", "fileName": "f1.txt", "text": f"doc for {user_text}"}
        ])


class LlmOnlyRagDataResult(FakeRagDataResult):
    def has_db_rag_docs(self) -> bool:
        return False

    def has_graph_rag_docs(self) -> bool:
        return False

    def as_system_prompt_text(self):
        return "LLM context"


class LlmOnlyRagDataService:
    async def get_rag_data(self, user_text: str, n: int, override: str | None):
        return LlmOnlyRagDataResult([])


class FakeAiService:
    async def initialize(self):
        return None

    def generic_prompt_template(self) -> str:
        return "stub"

    async def invoke_kernel(self, conv, prompt_text, user_text, context, max_tokens, temperature, top_p):
        from src.services.ai_completion import AiCompletion
        # Return a lightweight completion shell
        c = AiCompletion(conv.get_conversation_id(), None)
        c.set_content(f"llm says: {user_text}")
        return c


@asynccontextmanager
async def dummy_lifespan(app):
    # Skip heavy startup
    yield


def test_completions_append_across_turns():
    # Patch app to avoid real startup and services
    web_app.app.router.lifespan_context = dummy_lifespan
    mem = InMemoryNoSQL()
    web_app.nosql_svc = mem
    web_app.rag_data_svc = FakeRagDataService()
    # Bypass Jinja templates during tests
    class DummyViews:
        def TemplateResponse(self, *args, **kwargs):
            return PlainTextResponse("ok")
    web_app.views = DummyViews()

    with TestClient(web_app.app) as client:
        conv_id = "it-works"

    # Skip initial GET; template rendering is bypassed anyway

        # Post 4 turns forcing DB strategy to avoid LLM path
        for i in range(1, 5):
            resp = client.post(
                "/conv_ai_console",
                data={
                    "conversation_id": conv_id,
                    "user_text": f"hello {i}",
                    "rag_strategy": "db",
                },
            )
            assert resp.status_code == 200

        # Verify conversation state stored in memory grew 4 completions
        conv = asyncio.get_event_loop().run_until_complete(mem.load_conversation(conv_id))
        assert conv is not None, "conversation not found in memory store"
        data = conv.get_data()
        completions = data.get("completions", [])
        assert len(completions) == 4
        assert [c.get("user_text") for c in completions] == [
            "hello 1",
            "hello 2",
            "hello 3",
            "hello 4",
        ]


def test_completions_append_across_turns_llm_path():
    web_app.app.router.lifespan_context = dummy_lifespan
    mem = InMemoryNoSQL()
    web_app.nosql_svc = mem
    web_app.rag_data_svc = LlmOnlyRagDataService()
    web_app.ai_svc = FakeAiService()

    class DummyViews:
        def TemplateResponse(self, *args, **kwargs):
            return PlainTextResponse("ok")
    web_app.views = DummyViews()

    with TestClient(web_app.app) as client:
        conv_id = "it-works-llm"
        for i in range(1, 5):
            resp = client.post(
                "/conv_ai_console",
                data={
                    "conversation_id": conv_id,
                    "user_text": f"ping {i}",
                    "rag_strategy": "auto",
                },
            )
            assert resp.status_code == 200

        conv = asyncio.get_event_loop().run_until_complete(mem.load_conversation(conv_id))
        assert conv is not None
        data = conv.get_data()
        completions = data.get("completions", [])
        assert len(completions) == 4
        assert [c.get("user_text") for c in completions] == [
            "ping 1",
            "ping 2",
            "ping 3",
            "ping 4",
        ]
