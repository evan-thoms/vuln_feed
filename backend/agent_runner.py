from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from langchain.tools import Tool

# Import your tools
from tools.scrape_tools import scrape_site
from tools.cve_tools import fetch_cves
from tools.translate_tools import translate_text
from tools.db_tools import initialize_db, list_recent_articles

# Define tool list
tools = [
    Tool.from_function(scrape_site),
    Tool.from_function(fetch_cves),
    Tool.from_function(translate_text),
    Tool.from_function(initialize_db),
    Tool.from_function(list_recent_articles),
]

# Set up the language model (GPT-4o or 3.5-turbo depending on your key)
llm = ChatOpenAI(temperature=0, model="gpt-4")

# Initialize agent
agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    verbose=True,
)

# Optional: expose agent_executor as a function
def run_agent(input_text: str):
    return agent_executor.run(input_text)
