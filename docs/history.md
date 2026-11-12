# Project history

## 2026-11-10 — scaffold

ADK 2.x agent (`chatbot/`) on GEAP, run locally with `adk run` in `sreeai-noorg`.
Several model/location iterations ended on `gemini-3.8-flash` via `global`.

## 2026-11-12 — tooling and first deployment

1. **Claude Code setup** — added `CLAUDE.md` and the project skill
   `.claude/skills/google-adk/`; model name moved to `MODEL_NAME`; real project ID
   removed from the README.
2. **Manual deploy** — `adk deploy agent_engine` to `sreeai-noorg` / us-east4,
   runtime `7387508675864166400`. Found that `gemini-3.8-flash` 404s on regional
   endpoints → added `MODEL_LOCATION` and the `Gemini(client_kwargs=...)` pin.
3. **agents-cli** — imported the project
   (`scaffold enhance --from-adk-project`, then `-d agent_runtime`), added
   `app = App(..., name='chatbot')`, moved deps to `pyproject.toml`/`uv.lock`
   (Python 3.13), and redeployed with `agents-cli deploy`, which updated the same
   runtime in place (matched by display name).
4. **Terraform + GitHub Actions** — created `adk-chatbot-staging` and
   `adk-chatbot-prod`, added the GitHub Actions scaffolding, gated production on
   manual approval, and applied the CI/CD Terraform (94 resources). See
   [cicd-setup.md](cicd-setup.md).

## Retired

| Resource | Status |
|---|---|
| `projects/sreeai-noorg/locations/us-east4/reasoningEngines/7387508675864166400` (`adk-chatbot`) | To be deleted once the pipeline's staging and production runtimes are verified |
| `deploy.env`, `requirements.txt` | Removed (replaced by root `.env` and `pyproject.toml`) |
