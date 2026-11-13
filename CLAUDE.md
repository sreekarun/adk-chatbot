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
| Integration tests | `uv run --env-file .env pytest tests/integration` (pytest doesn't load `.env`) |
| Test deployed agent | `agents-cli run --mode adk "hello" --url https://us-east4-aiplatform.googleapis.com/v1/projects/<project>/locations/us-east4/reasoningEngines/<id>` (full https URL required) |

Run Python via `uv run ...`, not a bare `python`.

## Deployment — GitHub Actions + Terraform only

Full docs: `docs/` (start at `docs/README.md`; process in `docs/release-process.md`,
bootstrap in `docs/cicd-setup.md`).

- **Never run `agents-cli deploy` against staging or prod by hand.** Changes ship via
  PR → merge to `main` → *Deploy to Staging* → approval → *Deploy to Production*.
- Staging: `adk-chatbot-staging`, runtime `1601509054599921664`.
  Prod (+ CI/CD resources, TF state): `adk-chatbot-prod`, runtime `721618277402411008`.
  Region `us-east4`. `sreeai-noorg` is the local dev project only.
- Infra lives in `deployment/terraform/cicd/`, applied with
  `agents-cli infra cicd --staging-project adk-chatbot-staging --prod-project adk-chatbot-prod --repository-name adk-chatbot --repository-owner sreekarun --cicd-runner github_actions --region us-east4`
  (plan first; add `--apply` only with the user's go-ahead).
- Local change to the template: required reviewer on the `production` environment
  in `deployment/terraform/cicd/github.tf` — keep it after `scaffold upgrade`.
- Don't apply `deployment/terraform/single-project/` (would create another runtime
  in `sreeai-noorg`). Don't rename the project — deploys match runtimes by display
  name `adk-chatbot`.
- Staging deploys only when `chatbot/**`, `tests/**`, `deployment/**` or `uv.lock`
  change. No revision rollback: revert on `main`.
- Runtimes use Agent Identity (staging now; prod after staging is validated). Don't
  pass `--service-account` in the workflows — Agent Runtime rejects it. Any Terraform
  change to the runtime resource resets its code to the placeholder: always follow
  it with a pipeline deploy (`docs/operations.md`).
- Runtime size is set by the deploy flags in the workflows (`--max-instances 1
  --concurrency 3 --cpu 1 --memory 1Gi`: Agent Runtime minimums for the PoC), not
  Terraform (`deployment_spec` is ignored after creation). Staging keeps 1 warm
  instance (`--min-instances 1`, ~$69/month) to avoid cold starts during
  development; prod scales to zero (`--min-instances 0`).
- Keep the committed `deployment_metadata.json` at `null` values. agents-cli deploys
  to the runtime ID recorded there before matching by name, so a stale ID sends CI
  to the wrong project (403).

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
- `AGENT_REGISTRY_ENABLED` (`true` in staging) — gives `root_agent` the `find_agents` /
  `ask_agent` tools (`chatbot/agent_registry.py`): it lists Agent Registry at request
  time and calls the chosen agent over A2A, so new agents are reachable without a
  chatbot change. `AGENT_REGISTRY_PROJECT` (default `GOOGLE_CLOUD_PROJECT`) and
  `AGENT_REGISTRY_LOCATION` (default `us-east4`) pick the registry. The identity
  needs `roles/agentregistry.viewer`. Prod reads `AGENT_REGISTRY_ENABLED_PROD`.

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
