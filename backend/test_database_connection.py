#!/usr/bin/env python3
"""
Test script to verify database connection and identify issues
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test database connection and show details"""
    print("🧪 Testing Database Connection")
    print("=" * 50)
    
    # Check environment variables
    print("🔍 Environment Variables:")
    print(f"  DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    print(f"  RENDER: {os.getenv('RENDER', 'Not set')}")
    print(f"  PWD: {os.getcwd()}")
    
    try:
        from db import get_connection, get_db_path, DATABASE_URL
        print(f"\n🔍 Database Configuration:")
        print(f"  DATABASE_URL (from db.py): {DATABASE_URL}")
        print(f"  Database Path: {get_db_path()}")
        
        # Test connection
        print(f"\n🔌 Testing Connection...")
        conn = get_connection()
        
        # Check connection type
        if hasattr(conn, 'server_version'):
            print(f"✅ Connected to PostgreSQL (Supabase)")
            print(f"  Server Version: {conn.server_version}")
        else:
            print(f"⚠️ Connected to SQLite (Local)")
            print(f"  Database Path: {get_db_path()}")
        
        # Test queries
        print(f"\n📊 Testing Queries...")
        cursor = conn.cursor()
        
        # Check if tables exist
        if hasattr(conn, 'server_version'):
            # PostgreSQL
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('raw_articles', 'cves', 'newsitems')
            """)
        else:
            # SQLite
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        
        tables = cursor.fetchall()
        print(f"  ✅ Tables found: {[t[0] for t in tables]}")
        
        # Test CVE count
        try:
            cursor.execute("SELECT COUNT(*) FROM cves")
            cve_count = cursor.fetchone()[0]
            print(f"  📈 CVEs in database: {cve_count}")
        except Exception as e:
            print(f"  ❌ Error counting CVEs: {e}")
        
        # Test news count
        try:
            cursor.execute("SELECT COUNT(*) FROM newsitems")
            news_count = cursor.fetchone()[0]
            print(f"  📰 News items in database: {news_count}")
        except Exception as e:
            print(f"  ❌ Error counting news: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        import traceback
        traceback.print_exc()

def test_email_configuration():
    """Test email configuration"""
    print("\n🧪 Testing Email Configuration")
    print("=" * 50)
    
    print("🔍 Email Environment Variables:")
    print(f"  SENTINEL_NOTIFICATION_EMAIL: {os.getenv('SENTINEL_NOTIFICATION_EMAIL', 'Not set')}")
    print(f"  SMTP_SERVER: {os.getenv('SMTP_SERVER', 'Not set')}")
    print(f"  SMTP_PORT: {os.getenv('SMTP_PORT', 'Not set')}")
    print(f"  SMTP_USERNAME: {os.getenv('SMTP_USERNAME', 'Not set')}")
    print(f"  SMTP_PASSWORD: {'Set' if os.getenv('SMTP_PASSWORD') else 'Not set'}")
    print(f"  SEND_TEST_NOTIFICATIONS: {os.getenv('SEND_TEST_NOTIFICATIONS', 'Not set')}")

if __name__ == "__main__":
    test_database_connection()
    test_email_configuration()
    
    print("\n" + "=" * 50)
    print("✅ Database and Email Configuration Test Complete")
    print("=" * 50)
