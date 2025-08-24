from celery import Celery
from agent import IntelligentCyberAgent
from db import cleanup_old_articles
from models import QueryParams
from datetime import datetime, timedelta
import json
import sqlite3
import os
from celery.schedules import crontab

# Initialize Celery
celery_app = Celery('cyberintel')
celery_app.config_from_object('celery_config')

@celery_app.task
def weekly_intelligence_task():
    """Weekly intelligence gathering with 15 results of all severities and both content types"""
    print("🔄 Starting weekly intelligence gathering...")
    
    try:
        agent = IntelligentCyberAgent()
        
        # Weekly parameters: 15 results, all severities, both content types, 7 days back
        params = {
            'content_type': 'both',
            'severity': ['Critical', 'High', 'Medium', 'Low'],  # All severities
            'days_back': 7,
            'max_results': 15
        }
        
        print(f"📊 Weekly task parameters: {params}")
        
        # Execute the intelligence gathering
        result = agent.query(params)
        
        # Log the weekly execution
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": "weekly_intelligence_gathering",
            "success": result.get("success", False),
            "cves_found": len(result.get("cves", [])),
            "news_found": len(result.get("news", [])),
            "total_results": result.get("total_results", 0),
            "session_id": result.get("session_id", "unknown")
        }
        
        # Save to log file
        log_file = "weekly_intelligence.log"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        print(f"✅ Weekly intelligence gathering completed: {log_entry['cves_found']} CVEs, {log_entry['news_found']} news items")
        
        return {
            "success": True,
            "task": "weekly_intelligence_gathering",
            "results": log_entry
        }
        
    except Exception as e:
        error_msg = f"❌ Weekly intelligence gathering failed: {e}"
        print(error_msg)
        
        # Log error
        error_log = {
            "timestamp": datetime.now().isoformat(),
            "task": "weekly_intelligence_gathering",
            "success": False,
            "error": str(e)
        }
        
        with open("weekly_intelligence.log", "a") as f:
            f.write(json.dumps(error_log) + "\n")
        
        return {"success": False, "error": str(e)}

@celery_app.task
def cleanup_old_data_task():
    """Clean up old data based on retention policy"""
    print("🧹 Starting weekly data cleanup...")
    
    try:
        # Keep data for 30 days by default
        cutoff_date = datetime.now() - timedelta(days=30)
        
        deleted_count = cleanup_old_articles(cutoff_date)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": "data_cleanup",
            "success": True,
            "deleted_articles": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
        # Save to log file
        with open("weekly_intelligence.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        print(f"✅ Data cleanup completed: {deleted_count} articles deleted")
        
        return {
            "success": True,
            "deleted_articles": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        error_msg = f"❌ Data cleanup failed: {e}"
        print(error_msg)
        
        error_log = {
            "timestamp": datetime.now().isoformat(),
            "task": "data_cleanup",
            "success": False,
            "error": str(e)
        }
        
        with open("weekly_intelligence.log", "a") as f:
            f.write(json.dumps(error_log) + "\n")
        
        return {"success": False, "error": str(e)}

@celery_app.task
def manual_scrape_task(sources=None, max_results=20):
    """Manual scraping task triggered by API"""
    print(f"🎯 Manual scraping triggered for sources: {sources}")
    
    agent = IntelligentCyberAgent()
    
    if sources:
        query = f"Perform targeted scraping of {', '.join(sources)} sources. Get {max_results} recent items."
    else:
        query = f"Perform full scraping of all sources. Get {max_results} items from each source."
    
    return agent.query({"content_type": "both", "max_results": max_results, "days_back": 7})

@celery_app.task
def scheduled_intelligence_gathering():
    """Scheduled task to gather intelligence and update cache."""
    print("🔄 Starting scheduled intelligence gathering...")
    
    try:
        # Import here to avoid circular imports
        from tools.tools import trigger_background_scrape
        from db import get_cache_freshness, is_data_fresh
        
        # Check if cache is fresh
        cache_info = get_cache_freshness()
        
        if is_data_fresh(cache_info['last_scrape'], max_age_hours=12):
            print("✅ Cache is fresh, skipping scheduled scrape")
            return {"status": "skipped", "reason": "cache_fresh"}
        
        # Trigger background scrape
        result = trigger_background_scrape(content_type="both", max_results=50)
        print(f"✅ Scheduled scrape completed: {result}")
        
        return {"status": "completed", "result": result}
        
    except Exception as e:
        print(f"❌ Scheduled intelligence gathering failed: {e}")
        return {"status": "failed", "error": str(e)}

@celery_app.task
def scheduled_cache_cleanup():
    """Scheduled task to clean up old data."""
    print("🧹 Starting scheduled cache cleanup...")
    
    try:
        from tools.tools import manage_cache_cleanup
        
        result = manage_cache_cleanup(weeks_old=3)
        print(f"✅ Scheduled cleanup completed: {result}")
        
        return {"status": "completed", "result": result}
        
    except Exception as e:
        print(f"❌ Scheduled cache cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}

# Schedule tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Scrape every 12 hours
    sender.add_periodic_task(
        crontab(hour='*/12'),  # Every 12 hours
        scheduled_intelligence_gathering.s(),
        name='intelligence-gathering'
    )
    
    # Cleanup every day at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),  # Daily at 2 AM
        scheduled_cache_cleanup.s(),
        name='cache-cleanup'
    )

        # Helper function for cleanup
def cleanup_old_articles(cutoff_date):
    """Remove old articles beyond retention policy"""
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete old raw articles
        cursor.execute("DELETE FROM raw_articles WHERE scraped_at < ?", (cutoff_date.isoformat(),))
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        return deleted
        
    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")
        return 0