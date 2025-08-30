#!/usr/bin/env python3
"""
Database Cleanup Module
Removes old data to keep database current
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def cleanup_old_data(months_old: int = 3, dry_run: bool = False) -> Dict[str, any]:
    """
    Clean up data older than specified months
    
    Args:
        months_old: Number of months to keep (default: 3)
        dry_run: If True, only count items, don't delete
    
    Returns:
        Dict with cleanup statistics
    """
    print(f"🧹 Starting database cleanup (items older than {months_old} months)")
    print(f"🔍 Dry run mode: {dry_run}")
    
    try:
        from db import get_connection
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=months_old * 30)
        print(f"📅 Cutoff date: {cutoff_date}")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if we're using PostgreSQL
        is_postgresql = hasattr(conn, 'server_version')
        
        cleanup_stats = {
            "cutoff_date": cutoff_date.isoformat(),
            "dry_run": dry_run,
            "tables_cleaned": {},
            "total_deleted": 0,
            "success": True,
            "error": None
        }
        
        # Tables to clean with their date columns
        tables_to_clean = [
            ("cves", "published_date"),
            ("newsitems", "published_date"), 
            ("raw_articles", "scraped_at")
        ]
        
        for table_name, date_column in tables_to_clean:
            print(f"\n📊 Cleaning table: {table_name}")
            
            try:
                # Count items to be deleted
                if is_postgresql:
                    count_query = f"SELECT COUNT(*) FROM {table_name} WHERE {date_column} < %s"
                    cursor.execute(count_query, (cutoff_date,))
                else:
                    count_query = f"SELECT COUNT(*) FROM {table_name} WHERE {date_column} < ?"
                    cursor.execute(count_query, (cutoff_date,))
                
                count_to_delete = cursor.fetchone()[0]
                print(f"  📈 Found {count_to_delete} items to delete")
                
                if not dry_run and count_to_delete > 0:
                    # Delete old items
                    if is_postgresql:
                        delete_query = f"DELETE FROM {table_name} WHERE {date_column} < %s"
                        cursor.execute(delete_query, (cutoff_date,))
                    else:
                        delete_query = f"DELETE FROM {table_name} WHERE {date_column} < ?"
                        cursor.execute(delete_query, (cutoff_date,))
                    
                    deleted_count = cursor.rowcount
                    print(f"  ✅ Deleted {deleted_count} items")
                else:
                    deleted_count = 0
                    print(f"  ⏭️ Skipped deletion (dry run or no items)")
                
                cleanup_stats["tables_cleaned"][table_name] = {
                    "count_to_delete": count_to_delete,
                    "deleted_count": deleted_count
                }
                cleanup_stats["total_deleted"] += deleted_count
                
            except Exception as e:
                print(f"  ❌ Error cleaning {table_name}: {e}")
                cleanup_stats["tables_cleaned"][table_name] = {
                    "count_to_delete": 0,
                    "deleted_count": 0,
                    "error": str(e)
                }
        
        # Commit changes if not dry run
        if not dry_run:
            conn.commit()
            print(f"\n✅ Database cleanup completed successfully")
        else:
            print(f"\n🔍 Dry run completed - no changes made")
        
        conn.close()
        
        print(f"📊 Cleanup Summary:")
        print(f"  - Total items deleted: {cleanup_stats['total_deleted']}")
        for table, stats in cleanup_stats["tables_cleaned"].items():
            print(f"  - {table}: {stats['deleted_count']} deleted")
        
        return cleanup_stats
        
    except Exception as e:
        print(f"❌ Database cleanup failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_deleted": 0,
            "tables_cleaned": {}
        }

def add_test_data_for_cleanup():
    """
    Add test data that will be cleaned up (for testing purposes)
    """
    print("🧪 Adding test data for cleanup testing...")
    
    try:
        from db import get_connection
        from models import Article, Vulnerability, NewsItem
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if we're using PostgreSQL
        is_postgresql = hasattr(conn, 'server_version')
        
        # Add old test data (4 months ago)
        old_date = datetime.now() - timedelta(days=120)
        
        # Test data for CVEs
        test_cves = [
            ("CVE-TEST-2024-001", "Test CVE 1", "Test summary 1", "High", 7.5, old_date, "en", "TestSource", "http://test1.com", 0.8, "test_product"),
            ("CVE-TEST-2024-002", "Test CVE 2", "Test summary 2", "Medium", 5.0, old_date, "en", "TestSource", "http://test2.com", 0.6, "test_product"),
        ]
        
        # Test data for news
        test_news = [
            ("Test News 1", "Test news summary 1", old_date, "en", "TestSource", "http://testnews1.com", 0.7),
            ("Test News 2", "Test news summary 2", old_date, "en", "TestSource", "http://testnews2.com", 0.5),
        ]
        
        # Test data for raw articles
        test_raw = [
            ("TestSource", "Test Article 1", "Test content 1", "en", old_date, old_date),
            ("TestSource", "Test Article 2", "Test content 2", "en", old_date, old_date),
        ]
        
        added_count = 0
        
        # Insert test CVEs
        for cve_data in test_cves:
            try:
                if is_postgresql:
                    cursor.execute("""
                        INSERT INTO cves (cve_id, title, summary, severity, cvss_score, 
                                        published_date, original_language, source, url, intrigue, affected_products)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, cve_data)
                else:
                    cursor.execute("""
                        INSERT INTO cves (cve_id, title, summary, severity, cvss_score, 
                                        published_date, original_language, source, url, intrigue, affected_products)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, cve_data)
                added_count += 1
            except Exception as e:
                print(f"⚠️ Error adding test CVE: {e}")
        
        # Insert test news
        for news_data in test_news:
            try:
                if is_postgresql:
                    cursor.execute("""
                        INSERT INTO newsitems (title, summary, published_date, original_language, source, url, intrigue)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, news_data)
                else:
                    cursor.execute("""
                        INSERT INTO newsitems (title, summary, published_date, original_language, source, url, intrigue)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, news_data)
                added_count += 1
            except Exception as e:
                print(f"⚠️ Error adding test news: {e}")
        
        # Insert test raw articles
        for raw_data in test_raw:
            try:
                if is_postgresql:
                    cursor.execute("""
                        INSERT INTO raw_articles (source, title, content, language, scraped_at, published_date)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, raw_data)
                else:
                    cursor.execute("""
                        INSERT INTO raw_articles (source, title, content, language, scraped_at, published_date)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, raw_data)
                added_count += 1
            except Exception as e:
                print(f"⚠️ Error adding test raw article: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Added {added_count} test items for cleanup testing")
        return added_count
        
    except Exception as e:
        print(f"❌ Failed to add test data: {e}")
        return 0

if __name__ == "__main__":
    # Test the cleanup function
    print("🧪 Testing database cleanup...")
    
    # First add some test data
    test_items_added = add_test_data_for_cleanup()
    
    if test_items_added > 0:
        print(f"\n🔍 Running dry run cleanup...")
        dry_run_stats = cleanup_old_data(months_old=3, dry_run=True)
        
        print(f"\n🧹 Running actual cleanup...")
        cleanup_stats = cleanup_old_data(months_old=3, dry_run=False)
        
        print(f"\n📊 Test Results:")
        print(f"  - Test items added: {test_items_added}")
        print(f"  - Dry run found: {dry_run_stats['total_deleted']} items")
        print(f"  - Actually deleted: {cleanup_stats['total_deleted']} items")
    else:
        print("⚠️ No test data added, skipping cleanup test")
