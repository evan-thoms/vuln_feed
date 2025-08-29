#!/usr/bin/env python3
"""
Test script to verify production environment configuration
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_production_environment():
    """Test production environment configuration"""
    print("🧪 Testing Production Environment")
    print("=" * 50)
    
    # Check all critical environment variables
    print("🔍 Environment Variables:")
    critical_vars = [
        'DATABASE_URL',
        'SENTINEL_NOTIFICATION_EMAIL',
        'SMTP_SERVER',
        'SMTP_PORT',
        'SMTP_USERNAME',
        'SMTP_PASSWORD',
        'SEND_TEST_NOTIFICATIONS',
        'OPENAI_API_KEY',
        'CRON_SCHEDULE_TYPE',
        'RENDER'
    ]
    
    for var in critical_vars:
        value = os.getenv(var, 'Not set')
        if var == 'SMTP_PASSWORD':
            value = 'Set' if value != 'Not set' else 'Not set'
        print(f"  {var}: {value}")
    
    # Test database connection
    print(f"\n🔌 Testing Database Connection...")
    try:
        from db import get_connection, DATABASE_URL
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check connection type
        if hasattr(conn, 'server_version'):
            print(f"✅ Connected to PostgreSQL (Supabase)")
            print(f"  Server Version: {conn.server_version}")
        else:
            print(f"⚠️ Connected to SQLite (Local)")
        
        # Test queries
        cursor.execute("SELECT COUNT(*) FROM cves")
        cve_count = cursor.fetchone()[0]
        print(f"  📈 CVEs in database: {cve_count}")
        
        cursor.execute("SELECT COUNT(*) FROM newsitems")
        news_count = cursor.fetchone()[0]
        print(f"  📰 News items in database: {news_count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    
    # Test email configuration
    print(f"\n📧 Testing Email Configuration...")
    try:
        from utils.email_notifications import send_intelligence_report
        
        # Test email functionality
        email_address = os.getenv('SENTINEL_NOTIFICATION_EMAIL')
        if email_address:
            print(f"✅ Email address configured: {email_address}")
            
            # Check if we can create an email (without sending)
            test_results = {
                "cves_found": 5,
                "news_found": 3,
                "successful_classifications": 8,
                "failed_classifications": 0,
                "status": "test_run"
            }
            
            print(f"✅ Email function available")
        else:
            print(f"❌ No email address configured")
            
    except Exception as e:
        print(f"❌ Email configuration failed: {e}")
    
    # Test OpenAI API
    print(f"\n🤖 Testing OpenAI API...")
    try:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Test a simple completion
        response = llm.invoke("Say 'Hello World'")
        print(f"✅ OpenAI API working: {response.content}")
        
    except Exception as e:
        print(f"❌ OpenAI API failed: {e}")
    
    print(f"\n" + "=" * 50)
    print("✅ Production Environment Test Complete")
    print("=" * 50)

if __name__ == "__main__":
    test_production_environment()
