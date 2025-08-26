#!/usr/bin/env python3
"""
Test script to insert sample data into Supabase database for viewing.
This data will be left in the database for inspection.
"""

import os
import sys
from datetime import datetime, timedelta
from models import Vulnerability, NewsItem, Article

# Set up PostgreSQL connection for testing
os.environ['DATABASE_URL'] = 'postgresql://postgres.inanivtnpahnihaeqdpw:sNZGQnfitefaQiGO@aws-1-us-east-2.pooler.supabase.com:6543/postgres'

def insert_test_data():
    """Insert test data into the database for Supabase viewing"""
    print("🧪 Inserting Test Data for Supabase Viewing...")
    print("=" * 60)
    
    try:
        # Import database functions
        from db import (
            get_connection, insert_cve, insert_newsitem, insert_raw_article,
            get_cves_by_filters, get_news_by_filters
        )
        
        # Test 1: Insert test CVEs
        print("1. Inserting test CVEs...")
        test_cves = [
            Vulnerability(
                cve_id="TEST-2025-001",
                title="Test Critical Vulnerability",
                title_translated="Test Critical Vulnerability",
                summary="This is a test critical vulnerability for database viewing. It demonstrates how critical vulnerabilities appear in the system.",
                severity="Critical",
                cvss_score=9.8,
                published_date=datetime.now() - timedelta(days=1),
                original_language="en",
                source="test",
                url="https://test.com/cve-2025-001",
                intrigue=8.5,
                affected_products=["Test Product 1.0", "Test Product 2.0"]
            ),
            Vulnerability(
                cve_id="TEST-2025-002",
                title="Test High Severity Vulnerability",
                title_translated="Test High Severity Vulnerability",
                summary="This is a test high severity vulnerability for database viewing. It shows how high severity issues are handled.",
                severity="High",
                cvss_score=7.5,
                published_date=datetime.now() - timedelta(days=2),
                original_language="en",
                source="test",
                url="https://test.com/cve-2025-002",
                intrigue=7.0,
                affected_products=["Test Product 3.0"]
            ),
            Vulnerability(
                cve_id="TEST-2025-003",
                title="Test Medium Severity Vulnerability",
                title_translated="Test Medium Severity Vulnerability",
                summary="This is a test medium severity vulnerability for database viewing. It demonstrates medium priority issues.",
                severity="Medium",
                cvss_score=5.5,
                published_date=datetime.now() - timedelta(days=3),
                original_language="en",
                source="test",
                url="https://test.com/cve-2025-003",
                intrigue=5.5,
                affected_products=["Test Product 4.0"]
            )
        ]
        
        for cve in test_cves:
            insert_cve(cve)
            print(f"   ✅ Inserted CVE: {cve.cve_id} ({cve.severity})")
        
        # Test 2: Insert test news items
        print("\n2. Inserting test news items...")
        test_news = [
            NewsItem(
                title="Test Security Breach News",
                title_translated="Test Security Breach News",
                summary="This is a test security breach news item for database viewing. It demonstrates how security news appears in the system.",
                published_date=datetime.now() - timedelta(hours=6),
                original_language="en",
                source="test",
                url="https://test.com/news-2025-001",
                intrigue=8.0
            ),
            NewsItem(
                title="Test Malware Analysis Report",
                title_translated="Test Malware Analysis Report",
                summary="This is a test malware analysis report for database viewing. It shows how malware-related news is handled.",
                published_date=datetime.now() - timedelta(hours=12),
                original_language="en",
                source="test",
                url="https://test.com/news-2025-002",
                intrigue=7.5
            ),
            NewsItem(
                title="Test Zero-Day Exploit Discovery",
                title_translated="Test Zero-Day Exploit Discovery",
                summary="This is a test zero-day exploit discovery news for database viewing. It demonstrates high-priority security news.",
                published_date=datetime.now() - timedelta(hours=24),
                original_language="en",
                source="test",
                url="https://test.com/news-2025-003",
                intrigue=9.0
            )
        ]
        
        for news in test_news:
            insert_newsitem(news)
            print(f"   ✅ Inserted News: {news.title[:50]}...")
        
        # Test 3: Insert test raw articles
        print("\n3. Inserting test raw articles...")
        test_articles = [
            Article(
                id=None,
                source="test",
                url="https://test.com/article-2025-001",
                title="Test Raw Article 1",
                title_translated="Test Raw Article 1",
                content="This is a test raw article content for database viewing. It shows how raw articles are stored before classification.",
                content_translated="This is a test raw article content for database viewing. It shows how raw articles are stored before classification.",
                language="en",
                scraped_at=datetime.now() - timedelta(hours=1),
                published_date=datetime.now() - timedelta(hours=2)
            ),
            Article(
                id=None,
                source="test",
                url="https://test.com/article-2025-002",
                title="Test Raw Article 2",
                title_translated="Test Raw Article 2",
                content="This is another test raw article content for database viewing. It demonstrates the raw article storage process.",
                content_translated="This is another test raw article content for database viewing. It demonstrates the raw article storage process.",
                language="en",
                scraped_at=datetime.now() - timedelta(hours=3),
                published_date=datetime.now() - timedelta(hours=4)
            )
        ]
        
        for article in test_articles:
            insert_raw_article(article)
            print(f"   ✅ Inserted Raw Article: {article.title}")
        
        # Test 4: Verify data retrieval
        print("\n4. Verifying data retrieval...")
        
        # Test CVE retrieval with filters
        cves = get_cves_by_filters(severity_filter=["Critical", "High"], limit=10)
        print(f"   Found {len(cves)} CVEs with Critical/High severity")
        
        # Test news retrieval
        news = get_news_by_filters(limit=10)
        print(f"   Found {len(news)} news items")
        
        # Test connection type
        conn = get_connection()
        # if hasattr(conn, 'server_version'):
        #     print(f"   ✅ Using PostgreSQL connection (version: {conn.server_version})")
        # else:
        #     print(f"   ✅ Using SQLite connection")
        conn.close()
        
        print("\n✅ All test data inserted successfully!")
        print("\n📊 Summary:")
        print(f"   - CVEs inserted: {len(test_cves)}")
        print(f"   - News items inserted: {len(test_news)}")
        print(f"   - Raw articles inserted: {len(test_articles)}")
        print(f"   - Total items: {len(test_cves) + len(test_news) + len(test_articles)}")
        
        print("\n🔍 You can now view this data in your Supabase dashboard:")
        print("   - Tables: cves, newsitems, raw_articles")
        print("   - Look for items with 'test' source")
        print("   - Test URLs start with 'https://test.com/'")
        
    except Exception as e:
        print(f"❌ Error inserting test data: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def show_database_info():
    """Show information about the database connection and tables"""
    print("\n📋 Database Information:")
    print("=" * 60)
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get table information
        if hasattr(conn, 'server_version'):  # PostgreSQL
            cursor.execute("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name IN ('cves', 'newsitems', 'raw_articles')
                ORDER BY table_name, ordinal_position
            """)
        else:  # SQLite
            cursor.execute("PRAGMA table_info(cves)")
            cve_columns = cursor.fetchall()
            cursor.execute("PRAGMA table_info(newsitems)")
            news_columns = cursor.fetchall()
            cursor.execute("PRAGMA table_info(raw_articles)")
            article_columns = cursor.fetchall()
            
            print("   SQLite Tables:")
            print("   - cves:", [col[1] for col in cve_columns])
            print("   - newsitems:", [col[1] for col in news_columns])
            print("   - raw_articles:", [col[1] for col in article_columns])
        
        # Get row counts
        cursor.execute("SELECT COUNT(*) FROM cves")
        cve_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM newsitems")
        news_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM raw_articles")
        article_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"\n   Current Database Contents:")
        print(f"   - CVEs: {cve_count} rows")
        print(f"   - News items: {news_count} rows")
        print(f"   - Raw articles: {article_count} rows")
        
    except Exception as e:
        print(f"❌ Error getting database info: {e}")

def main():
    """Main test function"""
    print("🚀 Supabase Database Insertion Test")
    print("=" * 60)
    
    # Show current database info
    show_database_info()
    
    # Insert test data
    if insert_test_data():
        print("\n✅ Test data insertion completed successfully!")
        
        # Show updated database info
        show_database_info()
        
        print("\n🎉 You can now check your Supabase dashboard to see the test data!")
        print("   - Look for items with 'test' in the source field")
        print("   - Test URLs: https://test.com/...")
        print("   - Severities: Critical, High, Medium")
        
    else:
        print("\n❌ Test data insertion failed!")

if __name__ == "__main__":
    main()
