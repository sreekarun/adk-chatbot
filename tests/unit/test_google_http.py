from unittest import mock

import httpx

from chatbot import google_http


def test_to_mtls_host() -> None:
    assert (
        google_http._to_mtls_host("us-east4-aiplatform.googleapis.com")
        == "us-east4-aiplatform.mtls.googleapis.com"
    )
    assert (
        google_http._to_mtls_host("agentregistry.googleapis.com")
        == "agentregistry.mtls.googleapis.com"
    )
    assert (
        google_http._to_mtls_host("us-east4-aiplatform.mtls.googleapis.com")
        == "us-east4-aiplatform.mtls.googleapis.com"
    )
    assert google_http._to_mtls_host("localhost") == "localhost"


def _auth(use_mtls_host: bool) -> google_http._GoogleAuth:
    creds = mock.Mock(valid=True, token="tok")
    with mock.patch("google.auth.default", return_value=(creds, "p")):
        return google_http._GoogleAuth(use_mtls_host=use_mtls_host)


def test_auth_moves_request_to_mtls_host_when_cert_present() -> None:
    request = httpx.Request(
        "GET", "https://us-east4-aiplatform.googleapis.com/reasoningEngines/v1/x"
    )
    sent = next(_auth(use_mtls_host=True).auth_flow(request))
    assert sent.url.host == "us-east4-aiplatform.mtls.googleapis.com"
    assert sent.headers["Host"] == "us-east4-aiplatform.mtls.googleapis.com"
    assert sent.headers["Authorization"] == "Bearer tok"


def test_auth_keeps_host_without_cert() -> None:
    request = httpx.Request("GET", "https://us-east4-aiplatform.googleapis.com/x")
    sent = next(_auth(use_mtls_host=False).auth_flow(request))
    assert sent.url.host == "us-east4-aiplatform.googleapis.com"
    assert sent.headers["Authorization"] == "Bearer tok"
