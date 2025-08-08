from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import json

# Import your existing tools and models
from models import QueryParams  # Your existing QueryParams model
from tools import (
    scrape_and_process_articles,
    classify_articles, 
    filter_and_rank_items,
    format_and_present_results
)

app = FastAPI(title="Cybersecurity Intelligence API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models for the API
class VulnerabilityResponse(BaseModel):
    cve_id: str
    title: str
    title_translated: str
    summary: str
    severity: str
    cvss_score: float
    intrigue: float
    published_date: datetime
    original_language: str
    source: str
    url: str
    affected_products: Optional[List[str]] = []

class NewsResponse(BaseModel):
    title: str
    title_translated: str
    summary: str
    intrigue: float
    published_date: datetime
    original_language: str
    source: str
    url: str

class SearchResponse(BaseModel):
    cves: List[VulnerabilityResponse]
    news: List[NewsResponse]
    total_results: int
    processing_time: float
    query_params: Dict[str, Any]

class SearchRequest(BaseModel):
    content_type: str = "both"  # "cve", "news", "both"
    severity: Optional[List[str]] = None  # ["low", "medium", "high", "critical"]
    max_results: int = 10
    days_back: int = 7
    output_format: str = "json"
    email_address: Optional[str] = None

# Store active searches (in production, use Redis or similar)
active_searches = {}

@app.get("/")
async def root():
    return {"message": "Cybersecurity Intelligence API", "status": "online"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/search/{search_id}/status")
async def get_search_status(search_id: str):
    """Get the status of an ongoing search"""
    if search_id not in active_searches:
        raise HTTPException(status_code=404, detail="Search not found")
    
    return active_searches[search_id]

@app.get("/stats")
async def get_stats():
    """Get API usage statistics"""
    total_searches = len(active_searches)
    completed = sum(1 for s in active_searches.values() if s["status"] == "completed")
    processing = sum(1 for s in active_searches.values() if s["status"] == "processing")
    errors = sum(1 for s in active_searches.values() if s["status"] == "error")
    
    return {
        "total_searches": total_searches,
        "completed": completed,
        "processing": processing,
        "errors": errors,
        "uptime": "online"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import List, Optional, Dict, Any
# import asyncio
# from datetime import datetime
# import json

# # Import your existing tools and models
# from models import QueryParams  # Your existing QueryParams model
# from tools.tools import (
#     scrape_and_process_articles,
#     classify_articles, 
#     filter_and_rank_items,
#     format_and_present_results
# )

# app = FastAPI(title="Cybersecurity Intelligence API", version="1.0.0")

# # CORS middleware for React frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],  # React dev server
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Response models for the API
# class VulnerabilityResponse(BaseModel):
#     cve_id: str
#     title: str
#     title_translated: str
#     summary: str
#     severity: str
#     cvss_score: float
#     intrigue: float
#     published_date: datetime
#     original_language: str
#     source: str
#     url: str
#     affected_products: Optional[List[str]] = []

# class NewsResponse(BaseModel):
#     title: str
#     title_translated: str
#     summary: str
#     intrigue: float
#     published_date: datetime
#     original_language: str
#     source: str
#     url: str

# class SearchResponse(BaseModel):
#     cves: List[VulnerabilityResponse]
#     news: List[NewsResponse]
#     total_results: int
#     processing_time: float
#     query_params: Dict[str, Any]

# class SearchRequest(BaseModel):
#     content_type: str = "both"  # "cve", "news", "both"
#     severity: Optional[List[str]] = None  # ["low", "medium", "high", "critical"]
#     max_results: int = 10
#     days_back: int = 7
#     output_format: str = "json"
#     email_address: Optional[str] = None

# # Store active searches (in production, use Redis or similar)
# active_searches = {}

# @app.get("/")
# async def root():
#     return {"message": "Cybersecurity Intelligence API", "status": "online"}

# @app.get("/health")
# async def health_check():
#     return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# @app.post("/search", response_model=Dict[str, Any])
# async def search_intelligence(request: SearchRequest):
#     """Main endpoint to search for cybersecurity intelligence"""
    
#     start_time = datetime.now()
#     search_id = f"search_{int(start_time.timestamp())}"
    
#     try:
#         # Store search status
#         active_searches[search_id] = {
#             "status": "processing",
#             "start_time": start_time,
#             "stage": "initializing"
#         }
        
#         # Convert request to QueryParams
#         query_params = QueryParams(
#             content_type=request.content_type,
#             severity=request.severity,
#             max_results=request.max_results,
#             days_back=request.days_back,
#             output_format=request.output_format,
#             email_address=request.email_address
#         )
        
#         # Stage 1: Scraping
#         active_searches[search_id]["stage"] = "scraping"
#         articles = scrape_and_process_articles.invoke({"params": query_params})
        
#         # Stage 2: Classification
#         active_searches[search_id]["stage"] = "classifying"
#         cves, news_items = classify_articles.invoke({
#             "articles": articles, 
#             "params": query_params
#         })
        
#         # Stage 3: Filtering and Ranking
#         active_searches[search_id]["stage"] = "filtering"
#         filtered_results = filter_and_rank_items.invoke({
#             "cves": cves,
#             "news_items": news_items,
#             "params": query_params
#         })
        
#         # Convert to response format
#         cve_responses = []
#         for cve in filtered_results["cves"]:
#             cve_responses.append(VulnerabilityResponse(
#                 cve_id=cve.cve_id,
#                 title=cve.title,
#                 title_translated=cve.title_translated,
#                 summary=cve.summary,
#                 severity=cve.severity,
#                 cvss_score=cve.cvss_score,
#                 intrigue=cve.intrigue,
#                 published_date=cve.published_date,
#                 original_language=cve.original_language,
#                 source=cve.source,
#                 url=cve.url,
#                 affected_products=cve.affected_products or []
#             ))
        
#         news_responses = []
#         for news in filtered_results["news"]:
#             news_responses.append(NewsResponse(
#                 title=news.title,
#                 title_translated=news.title_translated,
#                 summary=news.summary,
#                 intrigue=news.intrigue,
#                 published_date=news.published_date,
#                 original_language=news.original_language,
#                 source=news.source,
#                 url=news.url
#             ))
        
#         processing_time = (datetime.now() - start_time).total_seconds()
        
#         # Update search status
#         active_searches[search_id] = {
#             "status": "completed",
#             "start_time": start_time,
#             "stage": "completed",
#             "results_count": len(cve_responses) + len(news_responses)
#         }
        
#         return {
#             "search_id": search_id,
#             "cves": [cve.dict() for cve in cve_responses],
#             "news": [news.dict() for news in news_responses],
#             "total_results": len(cve_responses) + len(news_responses),
#             "processing_time": processing_time,
#             "query_params": request.dict()
#         }
        
#     except Exception as e:
#         active_searches[search_id] = {
#             "status": "error",
#             "start_time": start_time,
#             "stage": "error",
#             "error": str(e)
#         }
#         raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# @app.get("/search/{search_id}/status")
# async def get_search_status(search_id: str):
#     """Get the status of an ongoing search"""
#     if search_id not in active_searches:
#         raise HTTPException(status_code=404, detail="Search not found")
    
#     return active_searches[search_id]

# @app.get("/stats")
# async def get_stats():
#     """Get API usage statistics"""
#     total_searches = len(active_searches)
#     completed = sum(1 for s in active_searches.values() if s["status"] == "completed")
#     processing = sum(1 for s in active_searches.values() if s["status"] == "processing")
#     errors = sum(1 for s in active_searches.values() if s["status"] == "error")
    
#     return {
#         "total_searches": total_searches,
#         "completed": completed,
#         "processing": processing,
#         "errors": errors,
#         "uptime": "online"
#     }

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)