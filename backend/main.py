from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import json

# Import your agent
from agent import IntelligentCyberAgent
from models import QueryParams
from tools.tools import _current_session

app = FastAPI(title="Cybersecurity Intelligence API", version="1.0.0")

# Initialize agent
agent = IntelligentCyberAgent()

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    content_type: str = "both"
    severity: Optional[List[str]] = None
    max_results: int = 10
    days_back: int = 7
    output_format: str = "json"
    email_address: Optional[str] = None

@app.post("/search")
async def search_intelligence(request: SearchRequest):
    """Main endpoint that activates the agent"""
    start_time = datetime.now()
    
    try:
        # Convert severity list to single string for agent
        # severity_str = request.severity[0] if request.severity else None
        
        # # Create query string for agent
        # query = f"Find {request.content_type} cybersecurity intelligence from last {request.days_back} days"
        # if severity_str:
        #     query += f" with {severity_str} severity"
        # query += f", show {request.max_results} results"
        params = {
            'content_type': request.content_type,
            'severity': request.severity[0] if request.severity else None,
            'days_back': request.days_back,
            'max_results': request.max_results
        }
        
        # Run agent
        agent_response = agent.query(params)

        agent_response["processing_time"] = (datetime.now() - start_time).total_seconds()
        agent_response["query_params"] = request.dict()
        
        return agent_response
        
        # Get structured data from session
        cves = _current_session.get("classified_cves", [])
        news = _current_session.get("classified_news", [])
        
        # Convert to dict format for JSON response
        cves_data = []
        for cve in cves:
            cves_data.append({
                "cve_id": cve.cve_id,
                "title": cve.title,
                "title_translated": cve.title_translated,
                "summary": cve.summary,
                "severity": cve.severity,
                "cvss_score": cve.cvss_score,
                "intrigue": cve.intrigue,
                "published_date": cve.published_date.isoformat() if hasattr(cve.published_date, 'isoformat') else str(cve.published_date),
                "original_language": cve.original_language,
                "source": cve.source,
                "url": cve.url,
                "affected_products": getattr(cve, 'affected_products', [])
            })
        
        news_data = []
        for news in news:
            news_data.append({
                "title": news.title,
                "title_translated": news.title_translated,
                "summary": news.summary,
                "intrigue": news.intrigue,
                "published_date": news.published_date.isoformat() if hasattr(news.published_date, 'isoformat') else str(news.published_date),
                "original_language": news.original_language,
                "source": news.source,
                "url": news.url
            })
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "cves": cves_data,
            "news": news_data,
            "total_results": len(cves_data) + len(news_data),
            "processing_time": processing_time,
            "agent_response": agent_response,
            "query_params": request.dict()
        }
    
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Cybersecurity Intelligence API", "status": "online"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)