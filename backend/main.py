from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import json

# Import your agent
from agent import IntelligentCyberAgent, set_websocket_manager
from models import QueryParams
from db import get_data_freshness_info

app = FastAPI(title="Cybersecurity Intelligence API", version="1.0.0")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Initialize agent and set WebSocket manager
agent = IntelligentCyberAgent()
set_websocket_manager(manager)

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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for testing
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/search")
async def search_intelligence(request: SearchRequest):
    """Main endpoint that activates the agent with real-time progress updates"""
    start_time = datetime.now()
    
    try:
        # Send initial status
        await manager.broadcast(json.dumps({
            "type": "progress",
            "status": "Analyzing data requirements...",
            "progress": 10
        }))

        params = {
            'content_type': request.content_type,
            'severity': request.severity,
            'days_back': request.days_back,
            'max_results': request.max_results
        }
        
        # Send scraping status
        await manager.broadcast(json.dumps({
            "type": "progress", 
            "status": "Scraping intelligence sources...",
            "progress": 25
        }))
        
        # Run agent
        agent_response = agent.query(params)

        # Send classification status
        await manager.broadcast(json.dumps({
            "type": "progress",
            "status": "Classifying threats...", 
            "progress": 75
        }))

        # Add freshness information
        freshness_info = get_data_freshness_info()
        
        # Format freshness data for frontend
        formatted_freshness = {
            "last_update": None,
            "total_articles": 0
        }
        
        # Get the most recent update time
        latest_times = []
        for source_info in freshness_info.get("scraping", {}).values():
            if source_info.get("last_scrape"):
                latest_times.append(source_info["last_scrape"])
        for type_info in freshness_info.get("classification", {}).values():
            if type_info.get("last_classified"):
                latest_times.append(type_info["last_classified"])
        
        if latest_times:
            formatted_freshness["last_update"] = max(latest_times).isoformat()
        
        # Get total articles
        total_articles = sum(
            source_info.get("total_articles", 0) 
            for source_info in freshness_info.get("scraping", {}).values()
        )
        formatted_freshness["total_articles"] = total_articles
        
        agent_response["freshness"] = formatted_freshness
        agent_response["processing_time"] = (datetime.now() - start_time).total_seconds()
        agent_response["query_params"] = request.dict()
        
        # Send completion status
        await manager.broadcast(json.dumps({
            "type": "progress",
            "status": "Complete!",
            "progress": 100
        }))
        
        return agent_response

    except Exception as e:
        # Send error status
        await manager.broadcast(json.dumps({
            "type": "error",
            "status": f"Error: {str(e)}",
            "progress": 0
        }))
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Cybersecurity Intelligence API", "status": "online"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/test-celery")
async def test_celery():
    """Test endpoint to manually trigger Celery tasks"""
    try:
        from celery.celery_tasks import weekly_intelligence_task
        
        # Trigger the task
        result = weekly_intelligence_task.delay()
        
        return {
            "success": True,
            "task_id": result.id,
            "message": "Celery task triggered successfully",
            "status": "Check logs for task execution"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to trigger Celery task"
        }

@app.get("/celery-status")
async def celery_status():
    """Check Celery worker and beat status"""
    try:
        from celery.celery_tasks import celery_app
        
        # Check if workers are available
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        return {
            "success": True,
            "active_workers": active_workers,
            "worker_count": len(active_workers) if active_workers else 0,
            "message": "Celery status check completed"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to check Celery status"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)