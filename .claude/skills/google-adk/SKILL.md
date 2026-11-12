---
name: google-adk
description: Patterns for building agents with Google ADK 2.x (google-adk) in this repo — defining agents, function tools, built-in tools, MCP toolsets, sub-agents and workflow agents, callbacks, session state, structured output, evals, and deploying to Agent Engine / Cloud Run. Use whenever editing chatbot/agent.py, adding tools or agents, writing evals, or running/deploying with the adk CLI.
---

# Google ADK 2.x — working notes

Verified against **google-adk 2.14.0 / google-genai 2.34.0** (the versions in `.venv`).
If the installed version changes, re-check signatures before relying on this file:

```bash
source .venv/bin/activate
pip show google-adk | grep Version
python -c "from google.adk.agents import LlmAgent; print(list(LlmAgent.model_fields))"
adk --help
```

When unsure about an API, read the installed source under
`.venv/lib/python3.14/site-packages/google/adk/` rather than guessing.

## 1. Agent package contract

ADK loads an agent from a folder:

- `<app>/__init__.py` contains `from . import agent`
- `<app>/agent.py` defines module-level `root_agent`
- `<app>/.env` is auto-loaded by the CLI

`Agent` is an alias of `LlmAgent` (`from google.adk.agents import Agent`).

```python
import os
from google.adk.agents import Agent

MODEL = os.getenv("MODEL_NAME", "gemini-3.8-flash")

root_agent = Agent(
    name="root_agent",            # valid identifier, unique in the tree
    model=MODEL,
    description="...",            # used by parent agents to decide delegation
    instruction="...",            # system prompt; supports {state_key} templating
    tools=[...],
)
```

Useful `LlmAgent` fields: `instruction`, `global_instruction`, `static_instruction`,
`tools`, `sub_agents`, `generate_content_config`, `output_schema`, `input_schema`,
`output_key`, `include_contents` (`'default'`/`'none'`), `planner`, `code_executor`,
`disallow_transfer_to_parent`, `disallow_transfer_to_peers`, plus the callbacks below.

## 2. Function tools

Any Python function (sync or async) is a tool. ADK builds the schema from the
**name, type hints, and docstring** — write them carefully, the model reads them.

```python
from google.adk.tools import ToolContext

def get_order_status(order_id: str, tool_context: ToolContext) -> dict:
    """Look up the shipping status of an order.

    Args:
        order_id: The order identifier, e.g. "A-1234".
    """
    tool_context.state["last_order_id"] = order_id   # optional state access
    return {"status": "success", "order_id": order_id, "state": "shipped"}
```

- Return a `dict` (include a status/error field so the model can recover).
- A parameter named `tool_context: ToolContext` is injected, not exposed to the model.
- Avoid default values the model can't express; keep params JSON-simple.
- Long-running work: wrap with `LongRunningFunctionTool(func=...)`.
- Human confirmation: see `google.adk.tools.tool_confirmation` / `request_input`.

## 3. Built-in and integration tools (`google.adk.tools`)

- `google_search`, `enterprise_web_search`, `url_context`, `google_maps_grounding`
- `VertexAiSearchTool(data_store_id=...)`, `DiscoveryEngineSearchTool`
- `load_memory`, `preload_memory`, `load_artifacts`
- `AgentTool(agent=other_agent)` — call another agent *as a tool* (returns to caller)
- `McpToolset(...)` — expose an MCP server's tools (needs `pip install mcp` — not
  installed by default; add it to `requirements.txt` if used)
- `APIHubToolset`, `exit_loop`, `transfer_to_agent`, `get_user_choice`

Some Gemini built-in tools (e.g. search grounding) can't be mixed with function
tools in the same agent; if you hit that, put the built-in in its own agent and
attach it via `AgentTool`.

## 4. Multi-agent

**Delegation (LLM-driven transfer):** give the parent `sub_agents=[...]`; each child
needs a clear `description`. The model transfers control to the best child.

**AgentTool vs sub_agents:** `AgentTool` = child answers and control returns to
the parent; `sub_agents` = control transfers to the child for the conversation.

**Workflow agents (deterministic):** from `google.adk.agents`
- `SequentialAgent(name=..., sub_agents=[a, b, c])` — run in order
- `ParallelAgent(name=..., sub_agents=[...])` — run concurrently
- `LoopAgent(name=..., sub_agents=[...], max_iterations=N)` — repeat; a tool can
  call `exit_loop` to stop

Pass data between steps with `output_key="key"` on one agent and `{key}` in the
next agent's `instruction`.

## 5. State

- `ToolContext.state` / `CallbackContext.state` — dict-like, persisted in the session.
- Key prefixes: no prefix = session; `user:` = per user across sessions;
  `app:` = shared across users; `temp:` = this invocation only.
- `{key}` in `instruction` is substituted from state (`{key?}` = optional).
- `output_key` writes the agent's final text response into state.

## 6. Callbacks (signatures in 2.14)

`CallbackContext` is an alias of `google.adk.agents.Context`. Each callback can be a
function or list of functions, sync or async. **Return `None` to continue**;
return a value to short-circuit / replace.

| Field | Args | Return to override |
|---|---|---|
| `before_agent_callback` / `after_agent_callback` | `(callback_context)` | `types.Content` |
| `before_model_callback` | `(callback_context, llm_request)` | `LlmResponse` (skip model) |
| `after_model_callback` | `(callback_context, llm_response)` | `LlmResponse` |
| `on_model_error_callback` | `(callback_context, llm_request, error)` | `LlmResponse` |
| `before_tool_callback` | `(tool, args, tool_context)` | `dict` (skip tool) |
| `after_tool_callback` | `(tool, args, tool_context, tool_response)` | `dict` |
| `on_tool_error_callback` | `(tool, args, tool_context, error)` | `dict` |

Imports: `from google.adk.models import LlmRequest, LlmResponse`,
`from google.genai import types`, `from google.adk.tools import BaseTool, ToolContext`.

Typical uses: guardrails/input filtering (`before_model`), arg validation or auth
(`before_tool`), redaction/logging (`after_*`), caching.

## 7. Structured output and generation config

```python
from pydantic import BaseModel
from google.genai import types

class Answer(BaseModel):
    summary: str
    confidence: float

agent = Agent(..., output_schema=Answer, output_key="answer",
              generate_content_config=types.GenerateContentConfig(temperature=0.2))
```

## 8. Running

```bash
adk run chatbot                 # interactive CLI
adk run chatbot "hello"         # single query
adk web .                       # dev UI (AGENTS_DIR = parent, or a single agent folder)
adk api_server .                # FastAPI server
```

Dev servers are unauthenticated — never expose them publicly.

Programmatic use: `google.adk.runners.Runner` with a session service
(`google.adk.sessions.InMemorySessionService` for local tests).

## 9. Evals

```bash
adk eval_set --help                                          # create/manage eval sets
adk eval chatbot chatbot/evals/basic.evalset.json            # run all cases
adk eval chatbot chatbot/evals/basic.evalset.json:case_1     # specific cases
adk eval chatbot <set> --config_file_path <cfg> --num_runs 3
```

- Easiest way to author cases: chat in `adk web`, then save the session to an eval set.
- Config defaults to `test_config.json` next to the eval set file, e.g.:

```json
{ "criteria": { "tool_trajectory_avg_score": 1.0, "response_match_score": 0.8 } }
```

- `adk test [folder]` runs pytest over agent test JSON files (`--rebuild` regenerates).
- In pytest: `google.adk.evaluation.agent_evaluator.AgentEvaluator.evaluate(...)` (async).

## 10. Deploy

```bash
adk deploy agent_engine --project <p> --region <r> --display_name <name> chatbot
adk deploy cloud_run    --project <p> --region <r> chatbot
adk deploy gke ... | adk deploy docker ...
```

Check `adk deploy <target> --help` first — several older flags
(`--staging_bucket`, `--env_file`, `--requirements_file`, `--adk_app`) are deprecated
in 2.14. Use `--agent_engine_id` to update an existing Agent Engine instance and
`--trace_to_cloud` / `--otel_to_cloud` for observability.

## Checklist when changing the agent

1. `root_agent` still exported; `python -c "import chatbot.agent"` succeeds.
2. New config vars added to `.env.example`.
3. Tool docstrings/type hints describe every argument.
4. `adk run chatbot "<prompt>"` exercises the change.
5. Add or update an eval case for new behaviour.
