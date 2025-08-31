from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
import json
import time
import os
import sys

# Import your agent
from agent import IntelligentCyberAgent, set_websocket_manager
from models import QueryParams
from db import get_data_freshness_info, init_db
from rate_limiter import rate_limiter

# Add this near the top of main.py, after the imports
import os
import sys

# Database migration is handled automatically by init_db()
# No separate migration needed for production

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

# Initialize database and agent with better error handling
try:
    init_db()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")

# Initialize agent and set WebSocket manager with error handling
try:
    agent = IntelligentCyberAgent()
    set_websocket_manager(manager)
    print("✅ Agent initialized successfully")
except Exception as e:
    print(f"❌ Agent initialization failed: {e}")
    # Don't crash the app, create a minimal agent
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
    try:
        # Basic health check that doesn't depend on database or agent
        return {
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "render": os.getenv('RENDER') is not None,
            "database_url_set": bool(os.getenv('DATABASE_URL')),
            "openai_key_set": bool(os.getenv('OPENAI_API_KEY'))
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Cybersecurity Intelligence API", "status": "online"}

@app.get("/rate-limit-info")
async def get_rate_limit_info(request: Request):
    """Get current rate limit information for the client"""
    client_ip = request.client.host
    if request.headers.get("x-forwarded-for"):
        client_ip = request.headers.get("x-forwarded-for").split(",")[0].strip()
    elif request.headers.get("x-real-ip"):
        client_ip = request.headers.get("x-real-ip")
    
    return rate_limiter.get_rate_limit_info(client_ip, "/search")

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
async def search_intelligence(request: SearchRequest, client_request: Request):
    """Main endpoint that activates the agent with real-time progress updates"""
    start_time = datetime.now()
    
    # Get client IP address
    client_ip = client_request.client.host
    if client_request.headers.get("x-forwarded-for"):
        client_ip = client_request.headers.get("x-forwarded-for").split(",")[0].strip()
    elif client_request.headers.get("x-real-ip"):
        client_ip = client_request.headers.get("x-real-ip")
    
    # Check rate limit
    is_allowed, retry_after = rate_limiter.check_rate_limit(client_ip, "/search")
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after_seconds": retry_after,
                "message": f"Too many requests. Please try again in {retry_after} seconds."
            }
        )
    
    # Record the request
    rate_limiter.record_request(client_ip, "/search")
    
    try:
        # Send initial status
        try:
            await manager.broadcast(json.dumps({
                "type": "progress",
                "status": "Analyzing data requirements...",
                "progress": 10
            }))
        except Exception:
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
        except Exception:
            pass  # Ignore WebSocket errors
        raise HTTPException(status_code=500, detail=f"Agent failed: {str(e)}")

@app.post("/manual-trigger")
async def manual_trigger_intelligence():
    """Manual trigger endpoint for intelligence gathering"""
    try:
        # Import the cron scheduler
        from cron_scheduler import SentinelCronScheduler
        
        # Create scheduler instance
        scheduler = SentinelCronScheduler()
        
        # Run intelligence gathering
        result = scheduler.run_scheduled_intelligence_gathering()
        
        return {
            "success": True,
            "message": "Manual intelligence gathering triggered successfully",
            "result": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to trigger manual intelligence gathering"
        }

@app.post("/run-migration")
async def run_migration_endpoint():
    """Run database migration via API endpoint"""
    try:
        from migrate_database import migrate_database
        success = migrate_database()
        
        if success:
            return {
                "success": True,
                "message": "Database migration completed successfully"
            }
        else:
            return {
                "success": False,
                "message": "Database migration failed"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Database migration error"
        }

@app.get("/scheduler-status")
async def get_scheduler_status():
    """Get status of scheduled intelligence gathering"""
    try:
        # Read log file to get last execution info
        log_file = "scheduled_intelligence.log"
        last_execution = None
        
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                lines = f.readlines()
                if lines:
                    # Get last line (most recent execution)
                    last_line = lines[-1].strip()
                    try:
                        last_execution = json.loads(last_line)
                    except:
                        pass
        
        return {
            "success": True,
            "scheduler_status": "active",
            "last_execution": last_execution,
            "next_scheduled": "Every 3 days via Render Cron Job"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

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

@app.post("/test-cron")
async def test_cron():
    """Test endpoint to manually trigger cron job (testing mode)"""
    try:
        from cron_scheduler import SentinelCronScheduler
        
        # Create scheduler in testing mode
        scheduler = SentinelCronScheduler("testing")
        
        # Run the scheduler
        result = scheduler.run_scheduled_intelligence_gathering()
        
        return {
            "success": result.get("success", False),
            "session_id": result.get("session_id", "unknown"),
            "schedule_type": "testing",
            "results": result.get("results", {}),
            "message": "Cron job test executed successfully" if result.get("success") else "Cron job test failed",
            "error": result.get("error", None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to trigger cron job test"
        }

@app.post("/trigger-production-cron")
async def trigger_production_cron():
    """Manual trigger endpoint for production cron job"""
    try:
        from cron_scheduler import SentinelCronScheduler
        
        # Create scheduler in production mode
        scheduler = SentinelCronScheduler("production")
        
        # Run the scheduler
        result = scheduler.run_scheduled_intelligence_gathering()
        
        return {
            "success": result.get("success", False),
            "session_id": result.get("session_id", "unknown"),
            "schedule_type": "production",
            "results": result.get("results", {}),
            "message": "Production cron job executed successfully" if result.get("success") else "Production cron job failed",
            "error": result.get("error", None)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to trigger production cron job"
        }

@app.get("/cron-status")
async def cron_status():
    """Check cron job status and recent executions"""
    try:
        # Read log files to get recent execution info
        log_files = [
            "scheduled_intelligence_testing.log",
            "scheduled_intelligence_production.log",
            "cron_scheduler.log"
        ]
        
        status_info = {
            "testing_log": None,
            "production_log": None,
            "scheduler_log": None,
            "last_testing_execution": None,
            "last_production_execution": None
        }
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r") as f:
                        lines = f.readlines()
                        if lines:
                            # Get last line (most recent execution)
                            last_line = lines[-1].strip()
                            try:
                                log_entry = json.loads(last_line)
                                if "testing" in log_file:
                                    status_info["testing_log"] = log_entry
                                    status_info["last_testing_execution"] = log_entry.get("timestamp")
                                elif "production" in log_file:
                                    status_info["production_log"] = log_entry
                                    status_info["last_production_execution"] = log_entry.get("timestamp")
                                else:
                                    status_info["scheduler_log"] = log_entry
                            except:
                                pass
                except Exception as e:
                    print(f"Error reading log file {log_file}: {e}")
        
        return {
            "success": True,
            "cron_status": "active",
            "schedule_type": os.getenv('CRON_SCHEDULE_TYPE', 'production'),
            "last_testing_execution": status_info["last_testing_execution"],
            "last_production_execution": status_info["last_production_execution"],
            "next_scheduled": "Every 30 minutes (testing) or 3 days (production) via Render Cron Job",
            "log_files_exist": [f for f in log_files if os.path.exists(f)]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
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