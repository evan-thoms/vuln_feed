#!/usr/bin/env python3
"""
Cron Job Scheduler for Sentinel Intelligence Gathering
Designed for Render cron service deployment
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import IntelligentCyberAgent
from db import init_db, get_data_statistics
from models import QueryParams

# Configure logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Render captures stdout/stderr
    ]
)
logger = logging.getLogger(__name__)

class SentinelCronScheduler:
    def __init__(self, schedule_type: str = "production"):
        """
        Initialize the cron scheduler
        schedule_type: "testing" (30 min) or "production" (6 hours)
        """
        self.agent = IntelligentCyberAgent()
        self.session_id = f"render_cron_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.schedule_type = schedule_type
        
        # Configuration based on schedule type
        if schedule_type == "testing":
            self.config = {
                'content_type': 'both',
                'severity': ['Critical', 'High'],  # Focus on high priority for testing
                'days_back': 1,  # Last 24 hours
                'max_results': 15,  # Smaller batch for frequent runs
                'output_format': 'json'
            }
            self.schedule_name = "30-minute testing"
        else:  # production
            self.config = {
                'content_type': 'both',
                'severity': ['Critical', 'High', 'Medium', 'Low'],  # All severities
                'days_back': 3,  # Last 3 days
                'max_results': 30,  # Larger batch for less frequent runs
                'output_format': 'json'
            }
            self.schedule_name = "6-hour production"
        
    def run_scheduled_intelligence_gathering(self) -> Dict[str, Any]:
        """
        Main cron job function - runs based on schedule type
        """
        logger.info(f"🔄 Starting {self.schedule_name} intelligence gathering - Session: {self.session_id}")
        logger.info(f"📁 Working directory: {os.getcwd()}")
        logger.info(f"🐍 Python executable: {sys.executable}")
        logger.info(f"🌐 Render environment: {os.getenv('RENDER', 'false')}")
        
        try:
            # Initialize database
            # Ensure DATABASE_URL is set for production
            if not os.getenv('DATABASE_URL'):
                logger.warning("⚠️ DATABASE_URL not set - will use SQLite fallback")
            else:
                logger.info("✅ DATABASE_URL configured for PostgreSQL")
            
            init_db()
            
            logger.info(f"📊 Cron job parameters: {self.config}")
            
            # Execute intelligence gathering
            start_time = datetime.now()
            
                    # Set the session ID in the agent to match the cron session EXACTLY
            # Don't call new_session() as it creates its own timestamp
            self.agent.current_session = {
                "scraped_articles": [],
                "classified_cves": [],
                "classified_news": [],
                "session_id": self.session_id  # Use the cron session ID
            }
            
            result = self.agent.query(self.config)
            end_time = datetime.now()
            
            # Calculate statistics
            cves_found = len(result.get('cves', []))
            news_found = len(result.get('news', []))
            total_results = cves_found + news_found
            execution_time = (end_time - start_time).total_seconds()
            
            # Log results
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "schedule_type": self.schedule_type,
                "task": "scheduled_intelligence_gathering",
                "success": result.get("success", False),
                "parameters": self.config,
                "results": {
                    "cves_found": cves_found,
                    "news_found": news_found,
                    "total_results": total_results,
                    "execution_time_seconds": execution_time
                },
                "error": result.get("error", None)
            }
            
            # Save to log file
            self._save_log_entry(log_entry)
            
            # Send email notification (only for production or if explicitly enabled)
            if self.schedule_type == "production" or os.getenv('SEND_TEST_NOTIFICATIONS', 'false').lower() == 'true':
                self._send_email_notification(log_entry)
            
            logger.info(f"✅ {self.schedule_name} intelligence gathering completed: {cves_found} CVEs, {news_found} news items")
            logger.info(f"⏱️ Execution time: {execution_time:.2f} seconds")
            
            # Run database cleanup after successful intelligence gathering
            cleanup_result = self._run_database_cleanup()
            
            return {
                "success": True,
                "session_id": self.session_id,
                "schedule_type": self.schedule_type,
                "results": log_entry,
                "cleanup": cleanup_result
            }
            
        except Exception as e:
            error_msg = f"❌ {self.schedule_name} intelligence gathering failed: {e}"
            logger.error(error_msg)
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Log error
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "schedule_type": self.schedule_type,
                "task": "scheduled_intelligence_gathering",
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            
            self._save_log_entry(error_log)
            
            # Send error notification
            if self.schedule_type == "production" or os.getenv('SEND_TEST_NOTIFICATIONS', 'false').lower() == 'true':
                self._send_error_notification(error_log)
            
            return {"success": False, "error": str(e)}
    
    def _save_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """Save log entry to file"""
        try:
            log_file = f"scheduled_intelligence_{self.schedule_type}.log"
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            logger.info(f"📝 Log saved to {log_file}")
        except Exception as e:
            logger.error(f"Failed to save log entry: {e}")
    
    def _send_email_notification(self, log_entry: Dict[str, Any]) -> None:
        """Send email notification for successful runs"""
        try:
            # Get email from environment variable
            email_address = os.getenv('SENTINEL_NOTIFICATION_EMAIL')
            if not email_address:
                logger.warning("No notification email configured")
                return
            
            # Import email functionality
            from utils.email_notifications import send_intelligence_report
            
            # Send email with results
            send_intelligence_report(
                email_address=email_address,
                session_id=log_entry['session_id'],
                results=log_entry['results'],
                success=True,
                schedule_type=self.schedule_type
            )
            
            logger.info(f"📧 Email notification sent to {email_address}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    def _send_error_notification(self, error_log: Dict[str, Any]) -> None:
        """Send email notification for errors"""
        try:
            email_address = os.getenv('SENTINEL_NOTIFICATION_EMAIL')
            if not email_address:
                return
            
            from utils.email_notifications import send_error_notification
            
            send_error_notification(
                email_address=email_address,
                session_id=error_log['session_id'],
                error=error_log['error'],
                schedule_type=self.schedule_type
            )
            
            logger.info(f"📧 Error notification sent to {email_address}")
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    def _run_database_cleanup(self) -> Dict[str, Any]:
        """Run database cleanup to remove old data"""
        try:
            logger.info("🧹 Starting database cleanup...")
            
            # Import cleanup function
            from db_cleanup import cleanup_old_data
            
            # Run cleanup (3 months old data)
            cleanup_stats = cleanup_old_data(months_old=3, dry_run=False)
            
            if cleanup_stats["success"]:
                logger.info(f"✅ Database cleanup completed: {cleanup_stats['total_deleted']} items deleted")
                
                # Log detailed cleanup stats
                for table, stats in cleanup_stats["tables_cleaned"].items():
                    logger.info(f"  📊 {table}: {stats['deleted_count']} items deleted")
                
                return cleanup_stats
            else:
                logger.error(f"❌ Database cleanup failed: {cleanup_stats['error']}")
                return cleanup_stats
                
        except Exception as e:
            logger.error(f"❌ Database cleanup error: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_deleted": 0
            }

def main():
    """Main entry point for cron job"""
    # For Render, use environment variable to determine schedule type
    # This allows different cron jobs for different schedules
    schedule_type = os.getenv('CRON_SCHEDULE_TYPE', 'production')
    
    logger.info(f"🚀 Starting Render cron job with schedule type: {schedule_type}")
    logger.info(f"📅 Current time: {datetime.now()}")
    
    if schedule_type not in ['testing', 'production']:
        logger.error(f"Invalid schedule type: {schedule_type}. Must be 'testing' or 'production'")
        sys.exit(1)
    
    scheduler = SentinelCronScheduler(schedule_type)
    result = scheduler.run_scheduled_intelligence_gathering()
    
    # Exit with appropriate code
    if result.get("success"):
        logger.info("✅ Cron job completed successfully")
        sys.exit(0)
    else:
        logger.error(f"❌ Cron job failed: {result.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
