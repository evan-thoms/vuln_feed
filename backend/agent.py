from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from typing import List, Dict, Optional
from models import QueryParams, Article, Vulnerability, NewsItem
from datetime import datetime, timedelta
import json
from dataclasses import asdict
from tools.tools import (
        analyze_data_needs,
            retrieve_existing_data,
            scrape_fresh_intel,
            classify_intelligence,
            evaluate_intel_sufficiency,
            intensive_rescrape,
            present_results
)
# Import your existing functions
from scrapers.chinese_scrape import ChineseScraper
from scrapers.english_scrape import EnglishScraper
from scrapers.russian_scrape import RussianScraper
from classify import classify_article
from langchain_groq import ChatGroq

from db import (
    init_db, insert_raw_article, is_article_scraped, mark_as_processed,
    get_unprocessed_articles, insert_cve, insert_newsitem, get_cves_by_filters, 
    get_news_by_filters, get_last_scrape_time, get_data_statistics
)
import os

api_key_name = "GROQ_API"

# Get the value of the environment variable
api_key = os.environ.get(api_key_name)


class IntelligentCyberAgent:
    def __init__(self):
        # self.llm = ChatGroq(
        #     model="llama-3.3-70b-versatile",
        #     groq_api_key=api_key,
        #     temperature=0,
        # )
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=0,
            max_retries=3
        )
        self.current_session = {
            "scraped_articles": [],
            "classified_cves": [],
            "classified_news": [],
            "session_id": None
        }
        self.tools = [
            analyze_data_needs,
            retrieve_existing_data,
            scrape_fresh_intel,
            classify_intelligence,
            evaluate_intel_sufficiency,
            intensive_rescrape,
            present_results
        ]
        for tool in self.tools:
            tool._agent_instance = self
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a cybersecurity intelligence agent. Follow this workflow:

1. analyze_data_needs - Check existing data
2. Based on JSON "recommendation":
   - "sufficient" → retrieve_existing_data → present_results → STOP
   - "urgent_scrape" → scrape_fresh_intel → classify_intelligence → present_results → STOP

Return only the final JSON from present_results. No additional commentary."""),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=8,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            early_stopping_method="generate"
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
    def new_session(self):
        self.current_session = {
            "scraped_articles": [],
            "classified_cves": [],
            "classified_news": [],
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    def query(self, params: dict) -> dict:
        """Main query interface"""
        try:
            # Start new session
            self.new_session()
            enhanced_input = f"""
            Execute cybersecurity intelligence workflow with these exact parameters:
                - content_type: {params['content_type']}
                - severity: {params.get('severity')}
                - days_back: {params['days_back']}
                - max_results: {params['max_results']}
                            """
                        
            # params = self.parse_query(user_input)
            
            # enhanced_input = f"""
            #     INTELLIGENCE REQUEST: "{user_input}"

            #     Parameters:
            #     - Content Type: {params.content_type}
            #     - Severity: {params.severity or "Any"}
            #     - Days Back: {params.days_back}
            #     - Max Results: {params.max_results}

            #     Execute intelligence gathering workflow with these parameters.
            # """
            print("input print", enhanced_input)
            result = self.agent_executor.invoke({"input": enhanced_input})



            # return result["output"]
            return self._build_response_from_session()
        
            # try:
            #     json_result = json.loads(result["output"])
            #     # Validate it has expected structure
            #     if "cves" in json_result and "news" in json_result:
            #         return json_result
            # except (json.JSONDecodeError, KeyError):
            #     pass
            #     # Fallback: extract from session if agent didn't return proper JSON
            # return self._build_response_from_session()
            
        except Exception as e:
            return {"success": False, "error": str(e), "cves": [], "news": []}
    def _build_response_from_session(self) -> dict:
        """Build response from session data - more reliable than parsing agent output"""
        cves_data = []
        for cve in self.current_session.get("classified_cves", []):
            cves_data.append({
                "cve_id": cve.cve_id,
                "title": cve.title,
                "title_translated": cve.title_translated,
                "summary": cve.summary,
                "severity": cve.severity,
                "cvss_score": float(cve.cvss_score),
                "intrigue": float(cve.intrigue),
                "published_date": cve.published_date.isoformat() if hasattr(cve.published_date, 'isoformat') else str(cve.published_date),
                "original_language": cve.original_language,
                "source": cve.source,
                "url": cve.url,
                "affected_products": getattr(cve, 'affected_products', [])
            })
        
        news_data = []
        for news in self.current_session.get("classified_news", []):
            news_data.append({
                "title": news.title,
                "title_translated": news.title_translated,
                "summary": news.summary,
                "intrigue": float(news.intrigue),
                "published_date": news.published_date.isoformat() if hasattr(news.published_date, 'isoformat') else str(news.published_date),
                "original_language": news.original_language,
                "source": news.source,
                "url": news.url
            })
        
        return {
            "success": True,
            "cves": cves_data,
            "news": news_data,
            "total_results": len(cves_data) + len(news_data),
            "session_id": self.current_session.get('session_id', 'Unknown'),
            "generated_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    agent = IntelligentCyberAgent()
    
    # Test queries showcasing agentic decision-making
    test_queries = [
        {'content_type': 'both', 'days_back': 7, 'max_results': 10, 'severity': 'high'}
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