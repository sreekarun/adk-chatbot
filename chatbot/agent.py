import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini

from chatbot.agent_registry import ask_agent, find_agents, registry_enabled

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.8-flash")
# Location used for model calls. Kept separate from GOOGLE_CLOUD_LOCATION because
# Agent Engine sets that to the runtime's region, while gemini-3.8-flash is only
# served from the `global` endpoint.
MODEL_LOCATION = os.getenv("MODEL_LOCATION", "global")

INSTRUCTION = "Answer user questions to the best of your knowledge"

# Specialist agents discovered at request time through Agent Registry
# (AGENT_REGISTRY_ENABLED=true). See chatbot/agent_registry.py.
TOOLS = []
if registry_enabled():
    TOOLS = [find_agents, ask_agent]
    INSTRUCTION += """.

Specialist agents: other agents are available through the agent registry, and the
set changes over time. When a request depends on current or recent events (for
example the latest AI news or recent research papers) or needs a specialty you
lack, call find_agents, choose the agent whose description and skills best fit,
and call ask_agent with a complete, self-contained request. Do this even if an
earlier call in this conversation failed. Present the agent's answer to the user,
keeping its sources and links, and say which agent it came from.

Never answer questions about current events from your own knowledge: it is out of
date. If no agent fits, or the call fails, say so plainly instead of guessing.

Answer everything else yourself, including general or historical questions that
don't depend on recent events."""

root_agent = Agent(
    model=Gemini(model=MODEL_NAME, client_kwargs={"location": MODEL_LOCATION}),
    name="root_agent",
    description="A helpful assistant for user questions.",
    instruction=INSTRUCTION,
    tools=TOOLS,
)

# agents-cli serving (chatbot/fast_api_app.py) imports `app`; its name must match
# the agent directory name.
app = App(root_agent=root_agent, name="chatbot")
