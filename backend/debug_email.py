#!/usr/bin/env python3
"""
Debug script to test email with recent items
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_email_with_recent_items():
    """Test email with recent items debugging"""
    print("🔍 Debugging Email with Recent Items")
    print("=" * 40)
    
    # Set environment variables
    os.environ['SENTINEL_NOTIFICATION_EMAIL'] = 'nadodude329@gmail.com'
    os.environ['SMTP_SERVER'] = 'smtp.gmail.com'
    os.environ['SMTP_PORT'] = '587'
    os.environ['SMTP_USERNAME'] = 'nadodude329@gmail.com'
    os.environ['SMTP_PASSWORD'] = 'gyac svcc rmay ctvd'
    
    try:
        from db import get_items_by_session
        
        # Test session_id
        session_id = "test_20250826_180010"
        
        print(f"🔍 Testing session_id: {session_id}")
        
        # Get recent items
        recent_items = get_items_by_session(session_id, limit=5)
        
        print(f"📊 Recent items result:")
        print(f"  CVEs: {recent_items['total_cves']}")
        print(f"  News: {recent_items['total_news']}")
        print(f"  CVE data: {recent_items['cves'][:2] if recent_items['cves'] else 'None'}")
        print(f"  News data: {recent_items['news'][:2] if recent_items['news'] else 'None'}")
        
        # Test email function
        from utils.email_notifications import send_intelligence_report
        
        print("\n📧 Testing email with recent items...")
        
        result = send_intelligence_report(
            email_address='nadodude329@gmail.com',
            session_id=session_id,
            results={
                'cves_found': 15,
                'news_found': 8,
                'processing_time': 45.2
            },
            success=True
        )
        
        if result:
            print("✅ Email sent successfully!")
        else:
            print("❌ Email failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_email_with_recent_items()
