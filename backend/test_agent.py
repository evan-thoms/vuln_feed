def main():
    from agent import IntelligentCyberAgent
    agent = IntelligentCyberAgent()
    result = agent.query("Show me critical CVEs from the last 3 days")

if __name__ == "__main__":
    main()