import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini

MODEL_NAME = os.getenv('MODEL_NAME', 'gemini-3.8-flash')
# Location used for model calls. Kept separate from GOOGLE_CLOUD_LOCATION because
# Agent Engine sets that to the runtime's region, while gemini-3.8-flash is only
# served from the `global` endpoint.
MODEL_LOCATION = os.getenv('MODEL_LOCATION', 'global')

root_agent = Agent(
    model=Gemini(model=MODEL_NAME, client_kwargs={'location': MODEL_LOCATION}),
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
)

# agents-cli serving (chatbot/fast_api_app.py) imports `app`; its name must match
# the agent directory name.
app = App(root_agent=root_agent, name='chatbot')
