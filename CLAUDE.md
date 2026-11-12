# CLAUDE.md

Chatbot built on **Google ADK 2.x** (`google-adk`) running against **Gemini
Enterprise Agent Platform (GEAP)** via Application Default Credentials.
Build, run, eval and deploy go through **[agents-cli](https://google.github.io/agents-cli/)**
(`google-agents-cli` 1.14, manifest: `agents-cli-manifest.yaml`).

Skills: the global `google-agents-cli-*` skills (workflow, scaffold, adk-code,
eval, deploy, observability, publish) cover the agents-cli lifecycle; the project
skill `.claude/skills/google-adk/` has repo-specific ADK notes and gotchas.

## Layout

- `agents-cli-manifest.yaml` — agents-cli project config (`agent_directory: chatbot`,
  `deployment_target: agent_runtime`, `region: us-east4`)
- `pyproject.toml` + `uv.lock` — dependencies (managed by uv; Python `>=3.11,<3.14`)
- `chatbot/` — the agent package
  - `agent.py` — exports `root_agent` **and** `app = App(root_agent=..., name='chatbot')`;
    the App name must equal the directory name
  - `fast_api_app.py`, `app_utils/` — generated serving code (FastAPI + A2A +
    Agent Runtime adapter). Don't hand-edit; `agents-cli scaffold upgrade` manages it
  - `.env` — local config read by the ADK loader (gitignored)
- `.env` (root) — project env, gitignored; **every `agents-cli deploy` propagates it**
  as runtime env vars
- `Dockerfile`, `.gcloudignore` — Agent Runtime builds the image from these
- `deployment/terraform/` — optional infra (`agents-cli infra single-project`)
- `tests/` — `unit/`, `integration/`, `eval/` (datasets + `eval_config.yaml`)

## Commands

| Task | Command |
|---|---|
| Install deps | `agents-cli install` (uv sync into `.venv`) |
| Smoke test | `agents-cli run "hello"` |
| Dev playground | `agents-cli playground` |
| Lint | `agents-cli lint` |
| Unit/integration tests | `uv run pytest tests/unit tests/integration` |
| Eval | `agents-cli eval run` |
| Deploy (dry run) | `agents-cli deploy --project sreeai-noorg --region us-east4 --dry-run` |
| Deploy | `agents-cli deploy --project sreeai-noorg --region us-east4` |
| Deploy status / list | `agents-cli deploy --status` / `--list` |
| Test deployed agent | `agents-cli run --url https://us-east4-aiplatform.googleapis.com/v1/projects/29833218647/locations/us-east4/reasoningEngines/7387508675864166400 --mode adk "hello"` (full https URL required) |

Run Python via `uv run ...`, not a bare `python`. Never deploy without the user's
explicit go-ahead.

## Deployment (Agent Runtime)

Runtime: `projects/sreeai-noorg/locations/us-east4/reasoningEngines/7387508675864166400`,
display name `adk-chatbot`. `agents-cli deploy` matches the existing runtime by
**display name** (= project `name` in the manifest, or `--service-name`) and updates
it in place — changing the name creates a new, separately billed runtime.

- Extra runtime env vars: `--env-vars KEY=VALUE,...` (on top of root `.env`);
  secrets via `--secrets ENV=SECRET[:VERSION]` (Secret Manager).
- No revision rollback on Agent Runtime: fix and redeploy.
- Logs: `gcloud logging read 'resource.type="aiplatform.googleapis.com/ReasoningEngine"' --project sreeai-noorg --limit 50`

## Environment / auth

- Auth: `gcloud auth application-default login` (ADC). No API keys.
- `GOOGLE_GENAI_USE_ENTERPRISE` selects the enterprise (Vertex/GEAP) backend. Don't
  also set `GOOGLE_GENAI_USE_VERTEXAI` — conflicting values raise an error.
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` (`global` locally; the runtime's
  region on Agent Runtime).
- `MODEL_NAME` (default `gemini-3.8-flash`) — the root agent's model.
- `MODEL_LOCATION` (default `global`) — location for model calls, independent of
  `GOOGLE_CLOUD_LOCATION`. Needed because `gemini-3.8-flash` is only served from
  `global` (404 in us-east4 / us-central1), while an Agent Runtime is regional.

## Conventions

- **Never change the model** unless asked; it comes from `MODEL_NAME`, not code.
- Never commit `.env`, credentials, or service-account JSON. Keep real project IDs
  out of committed docs — use placeholders in `README.md` / `.env.example`.
- When adding a config variable, add it to `.env.example` too.
- Tools are plain Python functions with type hints and a docstring; return a `dict`.
- Behaviour checks go in evals (`tests/eval/`), not pytest assertions on LLM text.
- Add/extend an eval case when changing agent behaviour.

## Verifying changes

1. `uv run python -c "import chatbot.agent as a; print(a.app.name)"` — imports cleanly.
2. `agents-cli run "<a prompt that exercises the change>"` — needs valid ADC.
3. `agents-cli eval run` for behaviour changes.
