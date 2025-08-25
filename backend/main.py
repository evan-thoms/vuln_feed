from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import json
import time
import os

# Import your agent
from agent import IntelligentCyberAgent, set_websocket_manager
from models import QueryParams
from db import get_data_freshness_info, init_db

# Initialize FastAPI app
app = FastAPI()

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

# Initialize WebSocket manager
manager = ConnectionManager()

# Simplified startup for debugging
try:
    print("🚀 Starting application...")
    # Skip database init temporarily to test basic startup
    # init_db()
    print("✅ Basic startup successful")
except Exception as e:
    print(f"❌ Startup error: {e}")

# Initialize agent and set WebSocket manager
try:
    agent = IntelligentCyberAgent()
    set_websocket_manager(manager)
    print("✅ Agent initialized successfully")
except Exception as e:
    print(f"⚠️ Agent initialization warning: {e}")
    agent = None

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Cybersecurity Intelligence API", "status": "online"}

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
        try:
            await manager.broadcast(json.dumps({
                "type": "progress",
                "status": "Analyzing data requirements...",
                "progress": 10
            }))
        except:
            pass  # Ignore WebSocket errors

        params = {
            'content_type': request.content_type,
            'severity': request.severity,
            'days_back': request.days_back,
            'max_results': request.max_results
        }
        
        # Send scraping status
        try:
            await manager.broadcast(json.dumps({
                "type": "progress", 
                "status": "Scraping intelligence sources...",
                "progress": 25
            }))
        except:
            pass  # Ignore WebSocket errors
        
        # Run agent
        agent_response = agent.query(params)

        # Send classification status
        try:
            await manager.broadcast(json.dumps({
                "type": "progress",
                "status": "Classifying threats...", 
                "progress": 75
            }))
        except:
            pass  # Ignore WebSocket errors

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
        agent_response["query_params"] = request.model_dump()
        
        # Send completion status
        try:
            await manager.broadcast(json.dumps({
                "type": "progress",
                "status": "Complete!",
                "progress": 100
            }))
        except:
            pass  # Ignore WebSocket errors
        
        return agent_response

    except Exception as e:
        # Send error status
        try:
            await manager.broadcast(json.dumps({
                "type": "error",
                "status": f"Error: {str(e)}",
                "progress": 0
            }))
        except:
            pass  # Ignore WebSocket errors
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")

@app.post("/search-minimal")
async def search_intelligence_minimal(request: SearchRequest):
    """Minimal search endpoint that just returns existing data without scraping"""
    try:
        # Initialize database only when needed
        from db import init_db, get_cves_by_filters, get_news_by_filters
        init_db()
        
        # Get existing data
        cves = get_cves_by_filters(
            content_type=request.content_type,
            severity=request.severity,
            days_back=request.days_back,
            max_results=request.max_results
        )
        
        news = get_news_by_filters(
            content_type=request.content_type,
            days_back=request.days_back,
            max_results=request.max_results
        )
        
        # Format response
        response = {
            "success": True,
            "cves": [],
            "news": [],
            "total_results": len(cves) + len(news),
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "generated_at": datetime.now().isoformat(),
            "source": "existing_data"
        }
        
        # Convert CVEs to proper format
        for cve in cves:
            response["cves"].append({
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
        
        # Convert news to proper format
        for news_item in news:
            response["news"].append({
                "title": news_item.title,
                "title_translated": news_item.title_translated,
                "summary": news_item.summary,
                "intrigue": float(news_item.intrigue),
                "published_date": news_item.published_date.isoformat() if hasattr(news_item.published_date, 'isoformat') else str(news_item.published_date),
                "original_language": news_item.original_language,
                "source": news_item.source,
                "url": news_item.url
            })
        
        return response
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cves": [],
            "news": [],
            "total_results": 0
        }

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

@app.get("/cache")
async def get_cached_data():
    """Simple cache-only endpoint for production"""
    try:
        from db import get_cached_intelligence
        
        # Get any available cached data
        cached_data = get_cached_intelligence(
            content_type="both",
            severity=None,
            days_back=7,
            max_results=10
        )
        
        return {
            "success": True,
            "cves": cached_data['cves'],
            "news": cached_data['news'],
            "total_results": cached_data['total_found'],
            "source": "cache_only"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "cves": [],
            "news": [],
            "total_results": 0
        }

@app.get("/test")
async def test_endpoint():
    """Simple test endpoint that doesn't use database or scraping"""
    return {
        "success": True,
        "message": "Basic endpoint working",
        "timestamp": datetime.now().isoformat(),
        "render": os.getenv('RENDER') is not None
    }

@app.get("/test-supabase")
async def test_supabase_connection():
    """Simple test to verify Supabase connection"""
    try:
        from db import DATABASE_URL
        
        # Check if DATABASE_URL is set to Supabase
        is_supabase = DATABASE_URL.startswith('postgresql')
        
        if is_supabase:
            # Try to import psycopg2 and test connection
            try:
                import psycopg2
                # Add connection parameters for better compatibility with hosting services
                connection_url = DATABASE_URL
                if "?" not in connection_url:
                    connection_url += "?sslmode=require&application_name=render_app"
                
                conn = psycopg2.connect(connection_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                conn.close()
                
                return {
                    "success": True,
                    "database_type": "PostgreSQL (Supabase)",
                    "connection": "Working",
                    "test_query": "SELECT 1 = OK",
                    "timestamp": datetime.now().isoformat()
                }
            except ImportError as e:
                # If psycopg2 fails, try to use current database connection as fallback
                try:
                    from db import get_connection
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    conn.close()
                    
                    return {
                        "success": True,
                        "database_type": "PostgreSQL (Supabase) - using fallback connection",
                        "connection": "Working via fallback",
                        "test_query": "SELECT 1 = OK",
                        "note": f"psycopg2 import failed: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                except Exception as fallback_error:
                    return {
                        "success": False,
                        "database_type": "PostgreSQL (Supabase)",
                        "connection": "Failed - psycopg2 not available and fallback failed",
                        "error": f"psycopg2: {str(e)}, fallback: {str(fallback_error)}",
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                return {
                    "success": False,
                    "database_type": "PostgreSQL (Supabase)",
                    "connection": "Failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "success": False,
                "database_type": "SQLite (not Supabase)",
                "connection": "Not using Supabase",
                "current_url": DATABASE_URL[:50] + "..." if len(DATABASE_URL) > 50 else DATABASE_URL,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)