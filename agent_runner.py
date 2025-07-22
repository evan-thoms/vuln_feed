from langchain.agents import initialize_agent, AgentType
from langchain_ollama import ChatOllama
from tools import scrape_articles, translate, classify, store_articles, load_unprocessed_articles

llm = ChatOllama(model="llama3")

tools = [scrape_articles, translate, classify, store_articles, load_unprocessed_articles]

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

if __name__ == "__main__":
    result = agent.run("Scrape 10 CVE articles from each language, translate and classify them, and store them in the database.")
    print(result)
