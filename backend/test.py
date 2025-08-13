if __name__ == "__main__":
    init_db()
    
    print("Testing tool directly:")
    result = analyze_data_needs.invoke({
        "content_type": "cve", 
        "severity": "critical", 
        "days_back": 3, 
        "max_results": 10
    })
    print(f"Tool result: {result}")
    agent = IntelligentCyberAgent()
    
    # Test queries showcasing agentic decision-making
    test_queries = [
        "Show me critical CVEs from the last 3 days",
        # "Get 20 recent cybersecurity news items with high intrigue",
        # "Find all high and critical vulnerabilities from this week",
        # "What are the latest zero-day exploits?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print('='*60)
        response = agent.query(query)
        print(response)
        print("\n" + "="*60 + "\n")