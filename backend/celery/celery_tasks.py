from celery import Celery
from agent import IntelligentCyberAgent
from db import get_data_statistics, cleanup_old_articles, get_trend_analysis
from models import QueryParams
from datetime import datetime, timedelta
import json
import sqlite3

# Initialize Celery
celery_app = Celery('cyberintel')
celery_app.config_from_object('celery_config')

@celery_app.task
def intelligent_scraping_task():
    """Autonomous scraping based on agent intelligence"""
    print("🤖 Starting intelligent autonomous scraping...")
    
    agent = IntelligentCyberAgent()
    
    # Agent decides what to scrape based on data analysis
    query = """
    Perform autonomous intelligence collection. Check current data status and:
    1. Identify gaps in recent data (last 24 hours)
    2. Scrape sources that are stale or missing data
    3. Focus on high-priority content (critical/high severity CVEs)
    4. Collect both CVEs and news for comprehensive coverage
    """
    
    try:
        result = agent.process_query_intelligent(query)
        
        # Log the autonomous action
        with open("autonomous_scraping.log", "a") as f:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "trigger": "scheduled",
                "success": result["success"],
                "summary": result.get("result", result.get("error"))[:200] + "..."
            }
            f.write(json.dumps(log_entry) + "\n")
        
        return result
        
    except Exception as e:
        print(f"❌ Autonomous scraping failed: {e}")
        return {"success": False, "error": str(e)}

@celery_app.task
def cleanup_old_data_task():
    """Clean up old data based on retention policy"""
    print("🧹 Starting data cleanup task...")
    
    try:
        # Keep data for 30 days by default
        cutoff_date = datetime.now() - timedelta(days=30)
        
        # This function needs to be added to db.py
        deleted_count = cleanup_old_articles(cutoff_date)
        
        return {
            "success": True,
            "deleted_articles": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return {"success": False, "error": str(e)}

@celery_app.task
def trend_analysis_task():
    """Analyze trends for agent learning"""
    print("📊 Starting trend analysis...")
    
    try:
        stats = get_data_statistics()
        
        # Add trend analysis (you'll need to implement this in db.py)
        trends = {
            "timestamp": datetime.now().isoformat(),
            "data_stats": stats,
            "growth_rate": calculate_growth_rate(),  # To be implemented
            "top_sources": get_top_sources(),        # To be implemented
            "severity_distribution": get_severity_distribution()  # To be implemented
        }
        
        # Save trends for agent learning
        with open("trend_analysis.json", "w") as f:
            json.dump(trends, f, indent=2)
        
        return trends
        
    except Exception as e:
        print(f"❌ Trend analysis failed: {e}")
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
    
    return agent.process_query_intelligent(query)

# Additional helper functions to add to db.py
def cleanup_old_articles(cutoff_date):
    """Remove old articles beyond retention policy"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Delete old raw articles
    cursor.execute("DELETE FROM raw_articles WHERE scraped_at < ?", (cutoff_date.isoformat(),))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    return deleted

def calculate_growth_rate():
    """Calculate data growth rate for trend analysis"""
    # Implementation depends on your specific needs
    return {"daily_growth": 0, "weekly_growth": 0}

def get_top_sources():
    """Get most productive sources"""
    # Implementation depends on your specific needs
    return {"chinese": 0, "russian": 0, "english": 0}

def get_severity_distribution():
    """Get distribution of CVE severities"""
    # Implementation depends on your specific needs
    return {"critical": 0, "high": 0, "medium": 0, "low": 0}