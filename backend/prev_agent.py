from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tools.tools import (
    scrape_and_process_articles,
    classify_articles, 
    filter_and_rank_items,
    format_and_present_results,
    check_data_sufficiency,
    get_existing_data,
    targeted_scrape
)
from models import QueryParams
from db import record_scraping_session, get_data_statistics
import re
from datetime import datetime

class IntelligentCyberAgent:
    def __init__(self):
        self.llm = ChatOllama(model="llama3")
        
        self.tools = [
            check_data_sufficiency,
            get_existing_data,
            scrape_and_process_articles,
            targeted_scrape,
            classify_articles,
            filter_and_rank_items, 
            format_and_present_results,
        ]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent cybersecurity agent that makes smart decisions about data collection.

DECISION MAKING PROCESS:
1. ALWAYS start by checking data sufficiency with check_data_sufficiency
2. Based on the analysis, choose ONE of these strategies:
   - If sufficient_data=True: Use get_existing_data
   - If recommendation="targeted_scrape": Use targeted_scrape with specific sources
   - If recommendation="full_scrape": Use scrape_and_process_articles
3. If you scraped new data, classify it with classify_articles
4. Always filter and rank with filter_and_rank_items
5. Format results with format_and_present_results

INTELLIGENCE RULES:
- Don't scrape unnecessarily - check existing data first
- Explain your reasoning for each decision
- Be efficient - use targeted scraping when possible
- Learn from data patterns

USER QUERY PARSING:
Extract these parameters from user queries:
- content_type: "cve", "news", "both" 
- severity: ["low", "medium", "high", "critical"] (for CVEs)
- days_back: number of days to look back
- max_results: number of results wanted
- output_format: "json" or "email"

Always explain what you're doing and why."""),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=8,  # Increased for more complex workflows
            handle_parsing_errors=True
        )
    
    def parse_query(self, query: str) -> QueryParams:
        """Enhanced query parsing with better intent detection"""
        params = QueryParams()
        query_lower = query.lower()
        
        # Content type detection
        if any(word in query_lower for word in ["cve", "vulnerability", "exploit"]):
            if "news" not in query_lower:
                params.content_type = "cve"
            else:
                params.content_type = "both"
        elif any(word in query_lower for word in ["news", "article", "report"]):
            params.content_type = "news"
        else:
            params.content_type = "both"
        
        # Severity extraction (multiple severities)
        severities = []
        for severity in ["critical", "high", "medium", "low"]:
            if severity in query_lower:
                severities.append(severity)
        params.severity = severities if severities else None
        
        # Time period extraction
        numbers = re.findall(r'\b(\d+)\b', query)
        for i, num in enumerate(numbers):
            num_int = int(num)
            
            # Check context around the number
            if any(word in query_lower for word in ["day", "days"]):
                params.days_back = num_int
            elif any(word in query_lower for word in ["week", "weeks"]):
                params.days_back = num_int * 7
            elif any(word in query_lower for word in ["month", "months"]):
                params.days_back = num_int * 30
            elif any(word in query_lower for word in ["result", "results", "item", "items"]):
                params.max_results = min(num_int, 50)  # Cap at 50
        
        # Default values if not specified
        if params.days_back == 7 and any(word in query_lower for word in ["recent", "latest", "today"]):
            params.days_back = 1
        elif any(word in query_lower for word in ["week"]):
            params.days_back = 7
            
        return params
    
    async def process_query_intelligent(self, user_input: str) -> dict:
        """Process query with full intelligence and return structured data"""
        try:
            params = self.parse_query(user_input)
            
            # Create context for the agent
            stats = get_data_statistics()
            enhanced_input = f"""
CYBERSECURITY INTELLIGENCE QUERY
User Request: "{user_input}"

Parsed Parameters:
- Content Type: {params.content_type}
- Severity Filter: {params.severity or "Any"}
- Time Period: {params.days_back} days
- Max Results: {params.max_results}
- Output Format: {params.output_format}

Current Database Status:
- Total CVEs: {stats['cves']['total']}
- Total News: {stats['news']['total']} 
- Recent Articles (24h): {stats['recent_articles']}

EXECUTE INTELLIGENT WORKFLOW:
1. Check data sufficiency first
2. Make smart decision about scraping
3. Process and return results
4. Explain your reasoning at each step
"""
            
            # Run the agent
            result = self.agent_executor.invoke({"input": enhanced_input})
            
            return {
                "success": True,
                "result": result["output"],
                "query_params": params.dict(),
                "processing_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query_params": params.dict() if 'params' in locals() else None
            }
    
    def query(self, user_input: str) -> str:
        """Simplified interface for backwards compatibility"""
        result = self.process_query_intelligent(user_input)
        
        if result["success"]:
            return result["result"]
        else:
            return f"❌ Error: {result['error']}"

# Usage example for testing
if __name__ == "__main__":
    agent = IntelligentCyberAgent()
    
    # Test queries
    test_queries = [
        "Show me critical CVEs from the last 3 days",
        "Get 15 recent cybersecurity news items", 
        "Find high and critical vulnerabilities from this week",
        "What are the latest security threats?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"QUERY: {query}")
        print('='*60)
        response = agent.query(query)
        print(response)