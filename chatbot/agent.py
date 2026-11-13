import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini

from chatbot.remote_agents import news_agent

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.8-flash")
# Location used for model calls. Kept separate from GOOGLE_CLOUD_LOCATION because
# Agent Engine sets that to the runtime's region, while gemini-3.8-flash is only
# served from the `global` endpoint.
MODEL_LOCATION = os.getenv("MODEL_LOCATION", "global")

INSTRUCTION = "Answer user questions to the best of your knowledge"

# Optional hand-off to the AI news agent over A2A (NEWS_AGENT_CARD_URL).
_news_agent = news_agent()
if _news_agent:
    INSTRUCTION += """.

AI news: for any question about current, recent, latest or top AI news,
announcements, releases or developments, always transfer to ai_news_agent, even if
an earlier transfer in this conversation failed (it may have recovered). Never
answer current AI news from your own knowledge: it is out of date. If the transfer
fails, tell the user the news service is unavailable right now and suggest trying
again shortly, without listing stories from memory.

Answer everything else yourself, including general or historical questions about
AI concepts that don't depend on recent events."""

root_agent = Agent(
    model=Gemini(model=MODEL_NAME, client_kwargs={"location": MODEL_LOCATION}),
    name="root_agent",
    description="A helpful assistant for user questions.",
    instruction=INSTRUCTION,
    sub_agents=[_news_agent] if _news_agent else [],
)

# agents-cli serving (chatbot/fast_api_app.py) imports `app`; its name must match
# the agent directory name.
app = App(root_agent=root_agent, name="chatbot")
