# CLAUDE.md

Chatbot built on **Google ADK 2.x** (`google-adk`, currently 2.14.0) running against
**Gemini Enterprise Agent Platform (GEAP)** via Application Default Credentials.

For ADK API patterns (tools, sub-agents, callbacks, state, evals, deploy), use the
`google-adk` project skill in `.claude/skills/google-adk/`.

## Layout

- `chatbot/` — the ADK agent package (the folder name is the app name)
  - `__init__.py` — must keep `from . import agent`
  - `agent.py` — must export a module-level `root_agent`
  - `.env` — local config, gitignored; template is `/.env.example`
- `requirements.txt` — runtime deps
- `.venv/` — Python 3.14 virtualenv

## Commands

Always activate the venv first: `source .venv/bin/activate`

| Task | Command |
|---|---|
| Interactive chat | `adk run chatbot` |
| One-shot query | `adk run chatbot "hello"` |
| Dev web UI | `adk web .` (parent dir; lists every agent folder) or `adk web chatbot` |
| API server | `adk api_server .` |
| Run evals | `adk eval chatbot chatbot/evals/<set>.evalset.json` |
| Deploy (update existing) | see "Deployment" below |

`adk web` / `api_server` endpoints are unauthenticated — local use only.

## Deployment (Agent Engine / Agent Platform Runtimes)

Deployed runtime: `projects/sreeai-noorg/locations/us-east4/reasoningEngines/7387508675864166400`
(display name `adk-chatbot`). Redeploy by updating it in place — omitting
`--agent_engine_id` creates a second, separately billed instance:

```bash
adk deploy agent_engine --project sreeai-noorg --region us-east4 \
  --agent_engine_id 7387508675864166400 --display_name adk-chatbot \
  --env_file "$PWD/deploy.env" chatbot
```

- `--env_file` must be an **absolute** path: the deploy `chdir`s into a temp build
  folder before reading it, so a relative path is silently ignored.
- `deploy.env` holds runtime env vars. Don't put `GOOGLE_CLOUD_PROJECT` /
  `GOOGLE_CLOUD_LOCATION` there — Agent Engine sets them (location = runtime region).
- `chatbot/.env` is not copied into the image (excluded by `chatbot/.gitignore`).
- Smoke test: `vertexai.Client(project=..., location="us-east4").agent_engines.get(name=...)`
  then `.stream_query(user_id="smoke-test", message="hi")`.

## Environment / auth

- Auth: `gcloud auth application-default login` (ADC). No API keys.
- `GOOGLE_GENAI_USE_ENTERPRISE=1` selects the enterprise (Vertex/GEAP) backend in
  google-genai 2.x. Don't also set `GOOGLE_GENAI_USE_VERTEXAI` — conflicting
  values raise an error.
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` (currently `global`).
- `MODEL_NAME` — the model the root agent should use.
- `MODEL_LOCATION` (default `global`) — location for model calls, independent of
  `GOOGLE_CLOUD_LOCATION`. Needed because `gemini-3.8-flash` is only served from
  `global` (404 in us-east4 / us-central1), while an Agent Engine runtime is regional.

## Conventions

- **Model name comes from config, not code.** Read `MODEL_NAME` from the
  environment (with a sensible default) rather than hardcoding it in `agent.py`;
  model swaps should be a `.env` change, not a commit.
- Never commit `.env`, credentials, or service-account JSON. Keep real project
  IDs out of committed docs — use placeholders in `README.md` / `.env.example`.
- When adding a config variable, add it to `.env.example` too.
- Tools are plain Python functions with type hints and a docstring (ADK builds the
  schema from them); return a `dict`.
- Prefer `instruction` text that is specific about the agent's role, tools, and
  output; keep long prompts in a separate module/constant.
- Add/extend an eval set when changing agent behaviour.

## Verifying changes

There is no unit test suite yet. To check a change:
1. `python -c "import chatbot.agent as a; print(a.root_agent)"` — imports cleanly.
2. `adk run chatbot "<a prompt that exercises the change>"` — needs valid ADC.
3. `adk eval ...` if an eval set exists.
