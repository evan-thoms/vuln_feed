#!/usr/bin/env python3
"""
Cron Job Scheduler for Sentinel Intelligence Gathering
Runs every 3 days to collect CVEs and news automatically
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cron_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SentinelCronScheduler:
    def __init__(self):
        """Initialize the cron scheduler"""
        self.agent = IntelligentCyberAgent()
        self.session_id = f"cron_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def run_scheduled_intelligence_gathering(self) -> Dict[str, Any]:
        """
        Main cron job function - runs every 3 days
        Collects 30 results (CVEs + news) from last 3 days
        """
        logger.info(f"🔄 Starting scheduled intelligence gathering - Session: {self.session_id}")
        
        try:
            # Initialize database
            init_db()
            
            # Set parameters for 3-day collection
            params = {
                'content_type': 'both',  # Both CVEs and news
                'severity': ['Critical', 'High', 'Medium', 'Low'],  # All severities
                'days_back': 3,  # Last 3 days
                'max_results': 30,  # 30 total results
                'output_format': 'json'
            }
            
            logger.info(f"📊 Cron job parameters: {params}")
            
            # Execute intelligence gathering
            start_time = datetime.now()
            result = self.agent.query(params)
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
                "task": "scheduled_intelligence_gathering",
                "success": result.get("success", False),
                "parameters": params,
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
            
            # Send email notification
            self._send_email_notification(log_entry)
            
            logger.info(f"✅ Scheduled intelligence gathering completed: {cves_found} CVEs, {news_found} news items")
            
            return {
                "success": True,
                "session_id": self.session_id,
                "results": log_entry
            }
            
        except Exception as e:
            error_msg = f"❌ Scheduled intelligence gathering failed: {e}"
            logger.error(error_msg)
            
            # Log error
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "task": "scheduled_intelligence_gathering",
                "success": False,
                "error": str(e)
            }
            
            self._save_log_entry(error_log)
            self._send_error_notification(error_log)
            
            return {"success": False, "error": str(e)}
    
    def _save_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """Save log entry to file"""
        try:
            log_file = "scheduled_intelligence.log"
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
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
                success=True
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
                error=error_log['error']
            )
            
            logger.info(f"📧 Error notification sent to {email_address}")
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")

def main():
    """Main entry point for cron job"""
    scheduler = SentinelCronScheduler()
    result = scheduler.run_scheduled_intelligence_gathering()
    
    # Exit with appropriate code
    if result.get("success"):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
