from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from tools.tools import (
    scrape_and_process_articles,
    classify_articles, 
    filter_and_rank_items,
    format_and_present_results
)
from models import QueryParams
import re

class CybersecQueryAgent:
    def __init__(self):
        self.llm = ChatOllama(model="llama3")
        
        self.tools = [
            scrape_and_process_articles,
            classify_articles,
            filter_and_rank_items, 
            format_and_present_results,
        ]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a cybersecurity intelligence agent. Your job is to:

1. Parse user queries to extract parameters
2. Execute a 4-step pipeline: scrape → classify → filter/rank → present

When users ask questions, extract:
- content_type: "cve", "news", or "both"
- severity: "low", "medium", "high", "critical" (for CVEs)
- days_back: number of days (default 7)
- max_results: number of results (default 10)
- output_format: "display" or "email"

ALWAYS execute these 4 tools IN ORDER:
1. scrape_and_process_articles - Get and translate fresh articles
2. classify_articles_pipeline - Classify as CVEs or news  
3. filter_and_rank_items - Apply filters and ranking
4. format_and_present_results - Format final output

Be conversational and explain what you're doing."""),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=6
        )
    
    def parse_query(self, query: str) -> QueryParams:
        """Extract parameters from natural language query"""
        params = QueryParams()
        
        query_lower = query.lower()
        
        # Content type
        if "cve" in query_lower and "news" not in query_lower:
            params.content_type = "cve"
        elif "news" in query_lower and "cve" not in query_lower:
            params.content_type = "news"
        else:
            params.content_type = "both"
        
        # Severity
        for severity in ["critical", "high", "medium", "low"]:
            if severity in query_lower:
                params.severity = severity
                break
        
        # Extract numbers
        numbers = re.findall(r'\b(\d+)\b', query)
        for num in numbers:
            num_int = int(num)
            if any(word in query_lower for word in ["day", "week", "month"]):
                if "week" in query_lower:
                    params.days_back = num_int * 7
                elif "month" in query_lower:
                    params.days_back = num_int * 30
                else:
                    params.days_back = num_int
            else:
                params.max_results = num_int
        
        # Email
        if "email" in query_lower:
            params.output_format = "email"
            # Extract email address if present
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', query)
            if email_match:
                params.email_address = email_match.group()
        
        return params
    
    def query(self, user_input: str) -> str:
        """Process a natural language query"""
        try:
            # Parse parameters
            params = self.parse_query(user_input)
            
            # Create enhanced prompt with parsed parameters
            enhanced_input = f"""
User Query: "{user_input}"

Parsed Parameters:
- Content Type: {params.content_type}
- Severity: {params.severity or "Any"}
- Days Back: {params.days_back}
- Max Results: {params.max_results}
- Output Format: {params.output_format}
- Email: {params.email_address or "None"}

Execute the 4-step pipeline with these parameters.
"""
            
            result = self.agent_executor.invoke({"input": enhanced_input})
            return result["output"]
            
        except Exception as e:
            return f"❌ Error processing query: {str(e)}"