from chatbot import agent_registry

API = "https://us-east4-aiplatform.googleapis.com/reasoningEngines/v1/projects/1/locations/us-east4/reasoningEngines/42/api/a2a/ai_news_agent"
NATIVE = "https://us-east4-aiplatform.googleapis.com/v1beta1/projects/1/locations/us-east4/reasoningEngines/42/a2a"


def _entry(engine_id: str = "42", interfaces=None) -> dict:
    return {
        "description": "Briefs users on AI news.",
        "skills": [{"name": "model", "description": "Briefs users on AI news.\nMore"}],
        "attributes": {
            "agentregistry.googleapis.com/system/RuntimeReference": {
                "uri": f"//aiplatform.googleapis.com/projects/1/locations/us-east4/reasoningEngines/{engine_id}"
            }
        },
        "card": {
            "content": {
                "url": NATIVE,
                "supportedInterfaces": interfaces
                if interfaces is not None
                else [{"url": API}],
            }
        },
    }


def test_a2a_url_prefers_api_passthrough_over_native() -> None:
    assert agent_registry._a2a_url(_entry()) == API


def test_a2a_url_none_without_api_interface() -> None:
    assert agent_registry._a2a_url(_entry(interfaces=[])) is None
    assert agent_registry._a2a_url({"description": "no card"}) is None


def test_summarize_uses_app_name_as_id() -> None:
    s = agent_registry._summarize(_entry(), API)
    assert s["agent_id"] == "ai_news_agent"
    assert s["skills"] == ["Briefs users on AI news."]


def test_is_self(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_AGENT_ENGINE_ID", "42")
    assert agent_registry._is_self(_entry("42"))
    assert not agent_registry._is_self(_entry("7"))


def test_registry_enabled(monkeypatch) -> None:
    monkeypatch.delenv("AGENT_REGISTRY_ENABLED", raising=False)
    assert not agent_registry.registry_enabled()
    monkeypatch.setenv("AGENT_REGISTRY_ENABLED", "true")
    assert agent_registry.registry_enabled()


def test_text_from_task_artifacts() -> None:
    result = {
        "kind": "task",
        "artifacts": [{"parts": [{"text": ""}]}, {"parts": [{"text": "Answer"}]}],
    }
    assert agent_registry._text_from_result(result) == "Answer"


def test_text_from_message() -> None:
    assert (
        agent_registry._text_from_result({"kind": "message", "parts": [{"text": "Hi"}]})
        == "Hi"
    )
