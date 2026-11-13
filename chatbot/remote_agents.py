"""Remote agents the chatbot can hand off to over A2A.

The AI news agent (sreekarun/ai-news-agent) runs on its own Agent Runtime and
publishes an A2A agent card. Set NEWS_AGENT_CARD_URL to that card's URL to enable
the hand-off; leave it unset and the chatbot runs on its own.

Auth: on Agent Runtime the chatbot runs as its Agent Identity, whose access
tokens are bound to the runtime's X.509 certificate. Google only accepts such
tokens over mTLS on the `*.mtls.googleapis.com` endpoints (a plain bearer call
gets 401). So when google-auth finds a client certificate, the HTTP client
presents it and every request is sent to the mTLS host, including the message
endpoint advertised in the agent card. Locally there's no certificate, so
requests go to the normal host with the user's ADC token.
"""

import os
import ssl

import google.auth
import google.auth.transport.requests
import httpx
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.auth.transport import mtls

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def _to_mtls_host(host: str) -> str:
    """`us-east4-aiplatform.googleapis.com` -> `us-east4-aiplatform.mtls.googleapis.com`."""
    if host.endswith(".googleapis.com") and not host.endswith(".mtls.googleapis.com"):
        return host[: -len("googleapis.com")] + "mtls.googleapis.com"
    return host


class _GoogleAuth(httpx.Auth):
    """Adds a Google access token from ADC, and moves requests to the mTLS host when asked."""

    def __init__(self, use_mtls_host: bool) -> None:
        self._credentials, _ = google.auth.default(scopes=_SCOPES)
        self._use_mtls_host = use_mtls_host

    def auth_flow(self, request):
        if not self._credentials.valid:
            self._credentials.refresh(google.auth.transport.requests.Request())
        if self._use_mtls_host:
            host = _to_mtls_host(request.url.host)
            if host != request.url.host:
                request.url = request.url.copy_with(host=host)
                request.headers["Host"] = host
        request.headers["Authorization"] = f"Bearer {self._credentials.token}"
        yield request


def _client_cert_ssl_context() -> ssl.SSLContext | None:
    """SSL context with the runtime's client certificate, or None if there isn't one."""
    return mtls.get_default_ssl_context()


def news_agent() -> RemoteA2aAgent | None:
    """The remote AI news agent, or None when NEWS_AGENT_CARD_URL is not set."""
    card_url = os.getenv("NEWS_AGENT_CARD_URL")
    if not card_url:
        return None
    ssl_ctx = _client_cert_ssl_context()
    return RemoteA2aAgent(
        name="ai_news_agent",
        description=(
            "Briefs users on recent AI industry news (models, research, funding, "
            "policy, chips) with source links and dates. Hand off any request "
            "about current or recent AI news."
        ),
        agent_card=card_url,
        httpx_client=httpx.AsyncClient(
            auth=_GoogleAuth(use_mtls_host=ssl_ctx is not None),
            verify=ssl_ctx if ssl_ctx is not None else True,
            # A briefing runs several grounded searches, and both runtimes scale
            # to zero, so allow for cold starts.
            timeout=httpx.Timeout(300.0),
        ),
    )
