from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from typing import List, Dict, Optional
from models import QueryParams, Article, Vulnerability, NewsItem
from datetime import datetime, timedelta
import json
from dataclasses import asdict

# Import your existing functions
from scrapers.chinese_scrape import ChineseScraper
from scrapers.english_scrape import EnglishScraper
from scrapers.russian_scrape import RussianScraper
from classify import classify_article
from db import (
    init_db, insert_raw_article, is_article_scraped, mark_as_processed,
    get_unprocessed_articles, insert_cve, insert_newsitem, get_cves_by_filters, 
    get_news_by_filters, get_last_scrape_time, get_data_statistics
)

# Global state to store data between tools (avoids token bloat)
_current_session = {
    "scraped_articles": [],
    "classified_cves": [],
    "classified_news": [],
    "session_id": None
}

def new_session():
    """Start a new processing session"""
    global _current_session
    _current_session = {
        "scraped_articles": [],
        "classified_cves": [],
        "classified_news": [],
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S")
    }

class IntelligentCyberAgent:
    def __init__(self):
        self.llm = ChatOllama(model="llama3.2")
        self.tools = [
            analyze_data_needs,
            retrieve_existing_data,
            scrape_fresh_intel,
            classify_intelligence,
            evaluate_intel_sufficiency,
            intensive_rescrape,
            present_results
        ]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an elite cybersecurity intelligence agent with advanced decision-making capabilities.

YOUR INTELLIGENT WORKFLOW:
1. analyze_data_needs - Assess current intelligence quality/freshness
2. Based on analysis:
   - If sufficient: retrieve_existing_data
   - If insufficient: scrape_fresh_intel
3. classify_intelligence - Process any new raw intelligence
4. evaluate_intel_sufficiency - Check if results meet requirements
5. If insufficient after classification: intensive_rescrape
6. present_results - Format final intelligence report

CRITICAL AGENTIC THINKING:
- Always evaluate if your results meet the user's needs
- If initial scraping yields poor results, DECIDE to intensify efforts
- Show your reasoning for each strategic decision
- Adapt your approach based on data quality, not just quantity

You are autonomous and make smart decisions about when to re-scrape."""),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    def parse_query(self, query: str) -> QueryParams:
        """Parse user query into structured parameters"""
        params = QueryParams()
        query_lower = query.lower()
        
        # Content type detection
        if any(word in query_lower for word in ["cve", "vulnerability"]):
            params.content_type = "cve" if "news" not in query_lower else "both"
        elif "news" in query_lower:
            params.content_type = "news"
        else:
            params.content_type = "both"
        
        # Severity extraction
        severities = []
        for severity in ["critical", "high", "medium", "low"]:
            if severity in query_lower:
                severities.append(severity)
        params.severity = severities if severities else None
        
        # Extract numbers for time/results
        import re
        numbers = re.findall(r'\b(\d+)\b', query)
        for num in numbers:
            num_int = int(num)
            if any(word in query_lower for word in ["day", "days"]):
                params.days_back = num_int
            elif any(word in query_lower for word in ["week", "weeks"]):
                params.days_back = num_int * 7
            elif any(word in query_lower for word in ["result", "results"]):
                params.max_results = min(num_int, 50)
        
        return params
    
    def query(self, user_input: str) -> str:
        """Main query interface"""
        try:
            # Start new session
            new_session()
            
            params = self.parse_query(user_input)
            
            enhanced_input = f"""
INTELLIGENCE REQUEST: "{user_input}"

Parameters:
- Content Type: {params.content_type}
- Severity: {params.severity or "Any"}
- Days Back: {params.days_back}
- Max Results: {params.max_results}

Execute intelligence gathering workflow with these parameters.
            """
            
            result = self.agent_executor.invoke({"input": enhanced_input})
            return result["output"]
            
        except Exception as e:
            return f"❌ Intelligence gathering failed: {str(e)}"

