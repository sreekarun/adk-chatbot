"""HTTP client for calling Google APIs (Agent Registry, other agents) from the chatbot.

On Agent Runtime the chatbot runs as its Agent Identity, whose access tokens are
bound to the runtime's X.509 certificate. Google only accepts such tokens over
mTLS on the `*.mtls.googleapis.com` endpoints (a plain bearer call gets 401).
So when google-auth finds a client certificate, the client presents it and every
request is sent to the mTLS host. Locally there's no certificate, so requests go
to the normal host with the user's ADC token.
"""

import functools
import ssl

import google.auth
import google.auth.transport.requests
import httpx
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


@functools.cache
def _client_cert_ssl_context() -> ssl.SSLContext | None:
    """SSL context with the runtime's client certificate, or None if there isn't one."""
    return mtls.get_default_ssl_context()


def google_client(timeout: float = 60.0) -> httpx.AsyncClient:
    """An async httpx client authenticated as this runtime (or the local user)."""
    ssl_ctx = _client_cert_ssl_context()
    return httpx.AsyncClient(
        auth=_GoogleAuth(use_mtls_host=ssl_ctx is not None),
        verify=ssl_ctx if ssl_ctx is not None else True,
        timeout=httpx.Timeout(timeout),
    )
