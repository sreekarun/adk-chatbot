"""Discover and call other agents through Agent Registry.

Agents deployed to Agent Runtime are registered automatically, including the A2A
agent card each deploy stores on the runtime. The chatbot lists the registry at
request time (cached briefly), so a newly deployed agent becomes reachable without
changing or redeploying the chatbot, and a deleted one disappears.

Only agents that serve A2A through their own app (`.../api/a2a/<app>`) are
offered: Agent Runtime's native `.../a2a` endpoint, which the registry also
advertises, rejects calls for these containers ("does not have A2A methods
defined"), so calls go to the interface URL from the stored card instead.

Config:
  AGENT_REGISTRY_ENABLED   "true" to give the chatbot the find/ask tools.
  AGENT_REGISTRY_PROJECT   project to list (default: GOOGLE_CLOUD_PROJECT).
  AGENT_REGISTRY_LOCATION  registry location (default: us-east4).
"""

import os
import time
import uuid

from chatbot.google_http import google_client

_REGISTRY_URL = "https://agentregistry.googleapis.com/v1"
_CACHE_SECONDS = 60
_ASK_TIMEOUT_SECONDS = 300.0  # several grounded searches, plus cold starts

_cache: dict = {"at": 0.0, "agents": []}


def registry_enabled() -> bool:
    return os.getenv("AGENT_REGISTRY_ENABLED", "").lower() == "true"


def _registry_parent() -> str:
    project = os.getenv("AGENT_REGISTRY_PROJECT") or os.getenv(
        "GOOGLE_CLOUD_PROJECT", ""
    )
    location = os.getenv("AGENT_REGISTRY_LOCATION", "us-east4")
    return f"projects/{project}/locations/{location}"


def _a2a_url(entry: dict) -> str | None:
    """The callable A2A JSON-RPC URL from the entry's stored agent card, if any."""
    card = (entry.get("card") or {}).get("content") or {}
    urls = [i.get("url", "") for i in card.get("supportedInterfaces") or []]
    urls.append(card.get("url", ""))
    return next((u for u in urls if "/api/a2a/" in u), None)


def _is_self(entry: dict) -> bool:
    own_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")
    if not own_id:
        return False
    ref = (entry.get("attributes") or {}).get(
        "agentregistry.googleapis.com/system/RuntimeReference", {}
    )
    return ref.get("uri", "").endswith(f"/reasoningEngines/{own_id}")


def _summarize(entry: dict, url: str) -> dict:
    card = (entry.get("card") or {}).get("content") or {}
    return {
        # The app name in the A2A path (e.g. "ai_news_agent") is unique per agent;
        # display names aren't (scaffolded agents all report "root_agent").
        "agent_id": url.rstrip("/").rsplit("/", 1)[-1],
        "description": entry.get("description") or card.get("description", ""),
        "skills": [
            (s.get("description") or s.get("name") or "").split("\n")[0][:160]
            for s in entry.get("skills") or []
        ],
        "url": url,
    }


async def _list_agents() -> list[dict]:
    if time.monotonic() - _cache["at"] < _CACHE_SECONDS:
        return _cache["agents"]
    agents, page_token = [], ""
    async with google_client() as client:
        while True:
            params = {"pageSize": 100}
            if page_token:
                params["pageToken"] = page_token
            resp = await client.get(
                f"{_REGISTRY_URL}/{_registry_parent()}/agents", params=params
            )
            resp.raise_for_status()
            body = resp.json()
            for entry in body.get("agents", []):
                url = _a2a_url(entry)
                if url and not _is_self(entry):
                    agents.append(_summarize(entry, url))
            page_token = body.get("nextPageToken", "")
            if not page_token:
                break
    _cache.update(at=time.monotonic(), agents=agents)
    return agents


async def find_agents() -> dict:
    """List the specialist agents available in the agent registry.

    Call this when a request needs current information or a specialty you don't
    have (for example current AI news), then pick the best match by its
    description and skills and call ask_agent.

    Returns:
        A dict with status and a list of agents (agent_id, description, skills).
    """
    try:
        agents = await _list_agents()
    except Exception as e:  # report to the model, don't crash the turn
        return {"status": "error", "error": f"Agent registry unavailable: {e}"}
    return {
        "status": "success",
        "agents": [
            {k: a[k] for k in ("agent_id", "description", "skills")} for a in agents
        ],
    }


def _text_from_result(result: dict) -> str:
    """Extract the reply text from an A2A message/send result (Task or Message)."""
    texts = []
    for artifact in result.get("artifacts") or []:
        texts += [p.get("text", "") for p in artifact.get("parts") or []]
    if not any(texts):
        message = (result.get("status") or {}).get("message") or result
        texts = [p.get("text", "") for p in message.get("parts") or []]
    return "\n".join(t for t in texts if t).strip()


async def ask_agent(agent_id: str, request: str) -> dict:
    """Send a request to an agent from find_agents and return its answer.

    Args:
        agent_id: The agent_id returned by find_agents, e.g. "ai_news_agent".
        request: The full, self-contained request for that agent.

    Returns:
        A dict with status and the agent's answer (or an error).
    """
    try:
        agents = {a["agent_id"]: a for a in await _list_agents()}
    except Exception as e:
        return {"status": "error", "error": f"Agent registry unavailable: {e}"}
    agent = agents.get(agent_id)
    if not agent:
        return {"status": "error", "error": f"No agent '{agent_id}' in the registry."}
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "messageId": str(uuid.uuid4()),
                "parts": [{"kind": "text", "text": request}],
            }
        },
    }
    try:
        async with google_client(timeout=_ASK_TIMEOUT_SECONDS) as client:
            resp = await client.post(agent["url"], json=payload)
            resp.raise_for_status()
            body = resp.json()
    except Exception as e:
        return {"status": "error", "error": f"Call to {agent_id} failed: {e}"}
    if "error" in body:
        return {"status": "error", "error": f"{agent_id}: {body['error']}"}
    answer = _text_from_result(body.get("result") or {})
    if not answer:
        return {"status": "error", "error": f"{agent_id} returned no text."}
    return {"status": "success", "agent_id": agent_id, "answer": answer}
