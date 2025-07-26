from agent.query_agent import CybersecQueryAgent

def main():
    print("🔒 **Cybersecurity Intelligence Agent**")
    print("Ask me to find CVEs, news, or both with natural language!")
    print("\nExamples:")
    print("- 'Show me 5 critical CVEs from the last 3 days'")
    print("- 'Find 10 cybersecurity news from this week'") 
    print("- 'Get me both CVEs and news, show 8 results from last month'")
    print("\nType 'quit' to exit.\n")
    
    agent = CybersecQueryAgent()
    
    while True:
        user_input = input("🤔 Your query: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("👋 Goodbye!")
            break
        
        if not user_input:
            continue
            
        print(f"\n🚀 Processing: '{user_input}'\n")
        response = agent.query(user_input)
        print(f"\n📋 **Results:**\n{response}\n")
        print("="*80 + "\n")

if __name__ == "__main__":
    main()