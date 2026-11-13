"""Remote agents the chatbot can hand off to over A2A.

The AI news agent (sreekarun/ai-news-agent) runs on its own Agent Runtime and
publishes an A2A agent card. Set NEWS_AGENT_CARD_URL to that card's URL to enable
the hand-off; leave it unset and the chatbot runs on its own.
"""

import os

import google.auth
import google.auth.transport.requests
import httpx
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class _GoogleAuth(httpx.Auth):
    """Adds a Google access token from ADC (the runtime's Agent Identity when deployed)."""

    def __init__(self) -> None:
        self._credentials, _ = google.auth.default(scopes=_SCOPES)

    def auth_flow(self, request):
        if not self._credentials.valid:
            self._credentials.refresh(google.auth.transport.requests.Request())
        request.headers["Authorization"] = f"Bearer {self._credentials.token}"
        yield request


def news_agent() -> RemoteA2aAgent | None:
    """The remote AI news agent, or None when NEWS_AGENT_CARD_URL is not set."""
    card_url = os.getenv("NEWS_AGENT_CARD_URL")
    if not card_url:
        return None
    return RemoteA2aAgent(
        name="ai_news_agent",
        description=(
            "Briefs users on recent AI industry news (models, research, funding, "
            "policy, chips) with source links and dates. Hand off any request "
            "about current or recent AI news."
        ),
        agent_card=card_url,
        # A briefing runs several grounded searches, and both runtimes scale to
        # zero, so allow for cold starts.
        httpx_client=httpx.AsyncClient(
            auth=_GoogleAuth(), timeout=httpx.Timeout(300.0)
        ),
    )
