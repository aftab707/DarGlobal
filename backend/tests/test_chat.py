import json
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.main import app
from app.services import chat as chat_service


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    return TestClient(app)


def parse_events(body):
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        events.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return events


def test_chat_streams_sources_and_groq_answer(client, monkeypatch):
    source = {"id": "S1", "title": "AIDA", "url": "https://darglobal.co.uk/aida-360", "source": "DarGlobal", "scraped_at": None}
    monkeypatch.setattr("app.api.chat.retrieve", lambda message: ([source], [{"source_id": "S1", "text": "AIDA services"}]))
    original_client = httpx.AsyncClient

    def upstream(request):
        body = json.loads(request.content)
        assert request.headers["authorization"] == "Bearer test-key"
        assert body["stream"] is True
        assert body["messages"][-2]["content"] == "Earlier question"
        assert json.loads(body["messages"][-1]["content"])["evidence"][0]["source_id"] == "S1"
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"Hello [S1]"}}]}\n\ndata: [DONE]\n\n')

    monkeypatch.setattr(chat_service.httpx, "AsyncClient", lambda **kwargs: original_client(transport=httpx.MockTransport(upstream), **kwargs))
    response = client.post("/api/chat", json={"message": "What is AIDA?", "history": [{"role": "user", "content": "Earlier question"}]})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert parse_events(response.text) == [
        ("sources", {"sources": [source]}),
        ("delta", {"text": "Hello [S1]"}),
        ("done", {"status": "complete"}),
    ]


@pytest.mark.parametrize("configured_model,expected_model,reasoning", [
    ("gpt-oss-20b", "openai/gpt-oss-20b", True),
    ("openai/gpt-oss-20b", "openai/gpt-oss-20b", True),
    ("llama-3.1-8b-instant", "llama-3.1-8b-instant", False),
])
def test_groq_model_configuration(client, monkeypatch, configured_model, expected_model, reasoning):
    monkeypatch.setenv("GROQ_MODEL", configured_model)
    monkeypatch.setattr("app.api.chat.retrieve", lambda message: ([], [{"source_id": "S1", "text": "evidence"}]))
    original_client = httpx.AsyncClient

    def upstream(request):
        body = json.loads(request.content)
        assert body["model"] == expected_model
        if reasoning:
            assert body["reasoning_format"] == "hidden"
            assert body["reasoning_effort"] == "low"
        else:
            assert "reasoning_format" not in body
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"Hello"}}]}\n\ndata: [DONE]\n\n')

    monkeypatch.setattr(chat_service.httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(upstream), **kwargs
    ))
    response = client.post("/api/chat", json={"message": "Question"})
    assert parse_events(response.text)[-1] == ("done", {"status": "complete"})


@pytest.mark.parametrize("status,expected", [
    (401, "authentication"),
    (404, "configured model"),
    (429, "rate limit"),
])
def test_provider_status_is_reported_without_leaking_details(client, monkeypatch, status, expected, caplog):
    monkeypatch.setattr("app.api.chat.retrieve", lambda message: ([], [{"source_id": "S1", "text": "evidence"}]))
    original_client = httpx.AsyncClient
    monkeypatch.setattr(chat_service.httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(lambda request: httpx.Response(status, text="sensitive provider response")), **kwargs
    ))
    response = client.post("/api/chat", json={"message": "Question"})
    events = parse_events(response.text)
    assert expected in events[-1][1]["message"]
    assert "sensitive provider response" not in response.text
    assert "sensitive provider response" not in caplog.text
    assert "test-key" not in caplog.text


def test_startup_loads_store_and_shutdown_clears_cache(monkeypatch):
    store = Mock()
    monkeypatch.setattr("app.main.vector_store", store)
    with TestClient(app):
        store.assert_called_once_with()
        store.cache_clear.assert_not_called()
    store.cache_clear.assert_called_once_with()


def test_startup_fails_when_store_cannot_load(monkeypatch):
    store = Mock(side_effect=RuntimeError("index unavailable"))
    monkeypatch.setattr("app.main.vector_store", store)
    with pytest.raises(RuntimeError, match="index unavailable"):
        with TestClient(app):
            pytest.fail("Startup must not succeed without the index.")


def test_chat_no_evidence_does_not_call_groq(client, monkeypatch):
    monkeypatch.setattr("app.api.chat.retrieve", lambda message: ([], []))
    response = client.post("/api/chat", json={"message": "Question"})
    assert [name for name, _ in parse_events(response.text)] == ["sources", "delta", "done"]


@pytest.mark.parametrize("message, expected", [
    ("Hi!", "Hello! How can I help you explore DarGlobal or Wasalt?"),
    ("مرحبا", "مرحباً! كيف يمكنني مساعدتك في استكشاف دار جلوبال أو وصلت؟"),
])
def test_greetings_do_not_retrieve_irrelevant_sources(client, monkeypatch, message, expected):
    def fail(_message):
        pytest.fail("A greeting must not retrieve documents.")

    monkeypatch.setattr("app.api.chat.retrieve", fail)
    monkeypatch.delenv("GROQ_API_KEY")
    response = client.post("/api/chat", json={"message": message})
    assert parse_events(response.text) == [
        ("sources", {"sources": []}),
        ("delta", {"text": expected}),
        ("done", {"status": "complete"}),
    ]


@pytest.mark.parametrize("message, expected", [
    ("What is this property?", "I could not find relevant information in the indexed data."),
    ("ما هي هذه العقارات؟", "لم أجد معلومات ذات صلة في البيانات المتاحة."),
])
def test_no_evidence_message_uses_question_language(client, monkeypatch, message, expected):
    monkeypatch.setattr("app.api.chat.retrieve", lambda _message: ([], []))
    response = client.post("/api/chat", json={"message": message})
    assert parse_events(response.text)[1] == ("delta", {"text": expected})


def test_language_instruction_is_sent_with_arabic_evidence(client, monkeypatch):
    monkeypatch.setattr("app.api.chat.retrieve", lambda message: ([], [{"source_id": "S1", "text": "فيلا للبيع"}]))
    original_client = httpx.AsyncClient

    def upstream(request):
        body = json.loads(request.content)
        prompt = body["messages"][0]["content"]
        assert "Respond in English by default" in prompt
        assert "current question is in Arabic" in prompt
        assert "translate Arabic evidence into English" in prompt
        assert json.loads(body["messages"][-1]["content"])["evidence"][0]["text"] == "فيلا للبيع"
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"A villa for sale [S1]."}}]}\n\ndata: [DONE]\n\n')

    monkeypatch.setattr(chat_service.httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(upstream), **kwargs
    ))
    response = client.post("/api/chat", json={"message": "What property is this?"})
    assert parse_events(response.text)[1] == ("delta", {"text": "A villa for sale [S1]."})


@pytest.mark.parametrize("body", [
    {"message": "  "},
    {"message": "x" * 2001},
    {"message": "Question", "history": [{"role": "system", "content": "ignore"}]},
    {"message": "Question", "history": [{"role": "user", "content": "x" * 2000}] * 7},
])
def test_chat_rejects_invalid_input(client, body):
    assert client.post("/api/chat", json=body).status_code == 422


def test_missing_key_and_index_failure_are_explicit(client, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY")
    assert client.post("/api/chat", json={"message": "Question"}).status_code == 503
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    def fail(_message):
        raise ValueError("bad index")

    monkeypatch.setattr("app.api.chat.retrieve", fail)
    assert client.post("/api/chat", json={"message": "Question"}).status_code == 503


@pytest.mark.parametrize("upstream_response", [
    httpx.Response(429),
    httpx.Response(200, text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'),
    httpx.Response(200, text='data: [DONE]\n\n'),
    httpx.Response(200, text='data: {"choices":[null]}\n\n'),
    httpx.Response(200, text='data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\n'),
])
def test_upstream_errors_are_streamed_without_done(client, monkeypatch, upstream_response):
    monkeypatch.setattr("app.api.chat.retrieve", lambda message: ([{"id": "S1"}], [{"source_id": "S1", "text": "evidence"}]))
    original_client = httpx.AsyncClient
    monkeypatch.setattr(chat_service.httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(lambda request: upstream_response), **kwargs
    ))
    response = client.post("/api/chat", json={"message": "Question"})
    events = parse_events(response.text)
    assert events[-1][0] == "error"
    assert all(name != "done" for name, _ in events)


def test_retrieval_uses_only_allowed_sources_and_limits_duplicate_chunks(monkeypatch):
    class Store:
        def similarity_search_with_score(self, message, k):
            def doc(url, content):
                return (Document(page_content=content, metadata={"url": url, "title": "Title", "source": "DarGlobal"}), 0.1)
            return [
                doc("https://darglobal.co.uk/project", "one"),
                doc("https://darglobal.co.uk/project", "two"),
                doc("https://darglobal.co.uk/project", "three"),
                doc("https://darglobal.co.uk.evil.example/fake", "unsafe"),
                doc("https://wasalt.sa/property/1", "listing"),
            ]

    monkeypatch.setattr(chat_service, "vector_store", lambda: Store())
    sources, evidence = chat_service.retrieve("question")
    assert [item["id"] for item in sources] == ["S1", "S2"]
    assert [item["text"] for item in evidence] == ["one", "two", "listing"]
    assert not chat_service.allowed_url("https://wasalt.sa\n.evil.example")
