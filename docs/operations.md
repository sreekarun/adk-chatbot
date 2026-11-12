# Operations

## Test a deployed agent

```bash
# staging
agents-cli run --mode adk "hello" --url \
  https://us-east4-aiplatform.googleapis.com/v1/projects/adk-chatbot-staging/locations/us-east4/reasoningEngines/1601509054599921664
# production
agents-cli run --mode adk "hello" --url \
  https://us-east4-aiplatform.googleapis.com/v1/projects/adk-chatbot-prod/locations/us-east4/reasoningEngines/721618277402411008
```

`--url` must be the full `https://<region>-aiplatform.googleapis.com/v1/...` URL; a
bare resource name fails with "Agent Runtime URL with a missing location".

SDK alternative:

```python
import vertexai
c = vertexai.Client(project="adk-chatbot-prod", location="us-east4")
ae = c.agent_engines.get(name="projects/adk-chatbot-prod/locations/us-east4/reasoningEngines/721618277402411008")
for ev in ae.stream_query(user_id="smoke-test", message="hello"):
    print(ev)
```

Console playground: Vertex AI → Agents → Agent Engines (us-east4) → `adk-chatbot`.

## Logs and telemetry

```bash
gcloud logging read 'resource.type="aiplatform.googleapis.com/ReasoningEngine"' \
  --project adk-chatbot-prod --limit 50
```

- Traces: Cloud Trace in each project (`GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`).
- GenAI telemetry is routed by a log sink into BigQuery `adk_chatbot_telemetry`
  (message content is **not** captured: `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`).
- Load-test reports: `gs://adk-chatbot-staging-adk-chatbot-logs/load-test-results/`.

## Configuration

| Variable | Where set | Notes |
|---|---|---|
| `GOOGLE_GENAI_USE_ENTERPRISE` | Terraform (runtime env), `.env` locally | Enterprise/Vertex backend. Don't also set `GOOGLE_GENAI_USE_VERTEXAI` |
| `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` | Agent Runtime / Terraform | Runtime location = region; model location is separate |
| `MODEL_NAME` | default in `agent.py` | `gemini-3.8-flash` |
| `MODEL_LOCATION` | default in `agent.py` | `global` — required for this model on a regional runtime |
| `LOGS_BUCKET_NAME`, `OTEL_*` | pipeline `--update-env-vars` / Terraform | telemetry |

Secrets: store in Secret Manager in the target project and pass via
`agents-cli deploy --secrets ENV=SECRET[:VERSION]` in the workflow; grant
`roles/secretmanager.secretAccessor` to the app service account.

## Terraform

- CI/CD + staging + prod stack: `deployment/terraform/cicd/`, state
  `gs://adk-chatbot-prod-terraform-state` (prefix per stack). Change it by editing
  the `.tf` files and re-running `agents-cli infra cicd ... --apply` (plan first
  without `--apply`).
- `deployment/terraform/single-project/` (template dev stack) is **not applied**.
  Don't run `agents-cli infra single-project --apply` without a decision: it would
  create another runtime and telemetry stack in `sreeai-noorg`.
- Terraform cannot adopt a runtime that `agents-cli deploy` created outside it;
  use `terraform import` if that ever becomes necessary.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| 404 `Publisher model ... gemini-3.8-flash was not found` | Model called in a region. Keep `MODEL_LOCATION=global` and the `client_kwargs` pin in `agent.py` |
| Local pytest: `Gemini API does not support project/location` | `.env` not loaded: `uv run --env-file .env pytest ...` |
| `infra cicd`: `lacks required scopes: workflow` | `gh auth refresh -h github.com -s workflow`, finish the browser step |
| Push to `main` didn't deploy | Path filter: only `chatbot/**`, `tests/**`, `deployment/**`, `uv.lock` trigger staging |
| Prod job stuck "Waiting" | Expected — approve via *Review deployments* |
| WIF / auth failures in Actions | Re-run `agents-cli infra cicd ... --apply`; IAM can take a few minutes to propagate |
| Agent errors after deploy | Logs query above; look for import errors (`app` must be exported from `chatbot/agent.py`) |
| `agents-cli deploy` created a second runtime | Display name changed. The pipeline matches on `adk-chatbot` (manifest `name`) — don't rename |
| Python 3.14 errors | Template requires `>=3.11,<3.14`; recreate with `agents-cli install` |
