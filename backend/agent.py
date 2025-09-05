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
            present_results
)
# Import your existing functions
from scrapers.chinese_scrape import ChineseScraper
from scrapers.english_scrape_with_vulners import EnglishScraperWithVulners
from scrapers.russian_scrape import RussianScraper
from classify import classify_article

from db import (
    init_db, insert_raw_article, is_article_scraped, mark_as_processed,
    get_unprocessed_articles, insert_cve, insert_newsitem, get_cves_by_filters, 
    get_news_by_filters, get_last_scrape_time, get_data_statistics
)
import os

api_key_name = "GROQ_API"

# Get the value of the environment variable
api_key = os.environ.get(api_key_name)

# WebSocket manager will be set by main.py after import
manager = None

def set_websocket_manager(ws_manager):
    """Set the WebSocket manager from main.py"""
    global manager
    manager = ws_manager

async def send_progress_update(status: str, progress: int):
    """Send progress update via WebSocket"""
    if manager:
        try:
            await manager.broadcast(json.dumps({
                "type": "progress",
                "status": status,
                "progress": progress
            }))
        except Exception as e:
            print(f"⚠️ WebSocket update failed: {e}")

class IntelligentCyberAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Import tools here to avoid circular imports
        from tools.tools import (
            analyze_data_needs, retrieve_existing_data, scrape_fresh_intel,
            classify_intelligence, evaluate_intel_sufficiency,
            present_results
        )
        
        # Keep existing tools for now, add new ones
        self.tools = [
            analyze_data_needs,
            retrieve_existing_data,
            scrape_fresh_intel,
            classify_intelligence,
            evaluate_intel_sufficiency,
            present_results
        ]
        
        # Set agent instance for tools
        for tool in self.tools:
            tool._agent_instance = self
        
        self.current_session = {
            "scraped_articles": [],
            "classified_cves": [],
            "classified_news": [],
            "session_id": None
        }
        
        # Keep existing prompt for now
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a cybersecurity intelligence agent. Follow this EXACT workflow:

1. analyze_data_needs - Check existing data
2. Based on JSON "recommendation":
   - "sufficient" → retrieve_existing_data → present_results → STOP
   - "urgent_scrape" → scrape_fresh_intel → classify_intelligence → present_results → STOP

IMPORTANT: 
- Call each function ONLY ONCE
- Do NOT repeat steps
- Do NOT call scrape_fresh_intel multiple times
- Return only the final JSON from present_results

Return only the final JSON from present_results. No additional commentary."""),
            ("user", "{input}"),
            ("assistant", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=4,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    def new_session(self, session_id=None):
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.current_session = {
            "scraped_articles": [],
            "classified_cves": [],
            "classified_news": [],
            "session_id": session_id
        }
    
    def query(self, params: dict, session_id: str = None) -> dict:
        """Main query interface - keep existing logic"""
        try:
            # Start new session with provided session_id or generate new one
            self.new_session(session_id)

            self.current_params = {
                'content_type': params['content_type'],
                'severity': params.get('severity'),
                'days_back': params['days_back'],
                'max_results': params['max_results']
            }
            
            enhanced_input = f"""
            Execute cybersecurity intelligence workflow with these exact parameters:
                - content_type: {params['content_type']}
                - severity: {params.get('severity', [])} 
                - days_back: {params['days_back']}
                - max_results: {params['max_results']}
                            """
    
            print("input print", enhanced_input)
            
            # Execute the agent
            print(f"🚀 Executing agent with input: {enhanced_input[:100]}...")
            result = self.agent_executor.invoke({"input": enhanced_input})
            print(f"✅ Agent execution completed. Result type: {type(result)}")
            print(f"🔍 Agent result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            # Send progress updates (non-blocking)
            # Note: send_progress_update is async but we're not awaiting it to avoid blocking
            # This will generate a RuntimeWarning but won't affect functionality
            try:
                import asyncio
                # Send initial progress (fire and forget)
                asyncio.create_task(send_progress_update("Analyzing data requirements...", 10))
                # Send completion progress (fire and forget)
                asyncio.create_task(send_progress_update("Complete!", 100))
            except Exception as e:
                print(f"⚠️ Progress update failed: {e}")
                # Continue execution even if WebSocket fails

            # Check if agent execution was successful
            if not result or (isinstance(result, dict) and not result.get('output')):
                print(f"⚠️ Agent execution returned empty result: {result}")
                # Return a fallback response instead of crashing
                return {
                    "success": False,
                    "error": "Agent execution failed to produce results",
                    "cves": [],
                    "news": [],
                    "total_results": 0,
                    "session_id": self.current_session.get('session_id', 'Unknown'),
                    "generated_at": datetime.now().isoformat()
                }

            return self._build_response_from_session()
        
        except Exception as e:
            return {"success": False, "error": str(e), "cves": [], "news": []}
    
    def _build_response_from_session(self) -> dict:
        """Build response from session data - keep existing logic"""
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