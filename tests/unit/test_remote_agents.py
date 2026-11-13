from unittest import mock

from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from chatbot import remote_agents


def test_news_agent_disabled_without_card_url(monkeypatch) -> None:
    monkeypatch.delenv("NEWS_AGENT_CARD_URL", raising=False)
    assert remote_agents.news_agent() is None


def test_news_agent_disabled_with_empty_card_url(monkeypatch) -> None:
    monkeypatch.setenv("NEWS_AGENT_CARD_URL", "")
    assert remote_agents.news_agent() is None


def test_news_agent_enabled_with_card_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "NEWS_AGENT_CARD_URL", "https://example.com/.well-known/agent-card.json"
    )
    with mock.patch("google.auth.default", return_value=(mock.Mock(), "p")):
        agent = remote_agents.news_agent()
    assert isinstance(agent, RemoteA2aAgent)
    assert agent.name == "ai_news_agent"


def test_to_mtls_host() -> None:
    assert (
        remote_agents._to_mtls_host("us-east4-aiplatform.googleapis.com")
        == "us-east4-aiplatform.mtls.googleapis.com"
    )
    assert (
        remote_agents._to_mtls_host("us-east4-aiplatform.mtls.googleapis.com")
        == "us-east4-aiplatform.mtls.googleapis.com"
    )
    assert remote_agents._to_mtls_host("localhost") == "localhost"


def _auth(use_mtls_host: bool) -> remote_agents._GoogleAuth:
    creds = mock.Mock(valid=True, token="tok")
    with mock.patch("google.auth.default", return_value=(creds, "p")):
        return remote_agents._GoogleAuth(use_mtls_host=use_mtls_host)


def test_auth_moves_request_to_mtls_host_when_cert_present() -> None:
    import httpx

    request = httpx.Request(
        "GET", "https://us-east4-aiplatform.googleapis.com/reasoningEngines/v1/x"
    )
    sent = next(_auth(use_mtls_host=True).auth_flow(request))
    assert sent.url.host == "us-east4-aiplatform.mtls.googleapis.com"
    assert sent.headers["Host"] == "us-east4-aiplatform.mtls.googleapis.com"
    assert sent.headers["Authorization"] == "Bearer tok"


def test_auth_keeps_host_without_cert() -> None:
    import httpx

    request = httpx.Request("GET", "https://us-east4-aiplatform.googleapis.com/x")
    sent = next(_auth(use_mtls_host=False).auth_flow(request))
    assert sent.url.host == "us-east4-aiplatform.googleapis.com"
    assert sent.headers["Authorization"] == "Bearer tok"
