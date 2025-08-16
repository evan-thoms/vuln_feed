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

        params = {
            'content_type': request.content_type,
            'severity': request.severity,
            'days_back': request.days_back,
            'max_results': request.max_results
        }
        
        # Run agent
        agent_response = agent.query(params)

        agent_response["processing_time"] = (datetime.now() - start_time).total_seconds()
        agent_response["query_params"] = request.dict()
        
        return agent_response

    
        
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