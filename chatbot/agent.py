import os

from google.adk.agents import Agent

MODEL = os.getenv('MODEL_NAME', 'gemini-3.8-flash')

root_agent = Agent(
    model=MODEL,
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
)
