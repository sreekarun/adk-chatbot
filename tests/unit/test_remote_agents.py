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
