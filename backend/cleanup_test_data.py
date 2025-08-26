#!/usr/bin/env python3
"""
Script to clean up test data from Supabase database.
Deletes all items with 'test' source or test URLs.
"""

import os
import sys

# Set up PostgreSQL connection for cleanup
os.environ['DATABASE_URL'] = 'postgresql://postgres.inanivtnpahnihaeqdpw:sNZGQnfitefaQiGO@aws-1-us-east-2.pooler.supabase.com:6543/postgres'

def cleanup_test_data():
    """Delete all test data from the database"""
    print("🧹 Cleaning up test data from Supabase...")
    print("=" * 60)
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete test data from all tables
        deleted_counts = {}
        
        # 1. Delete from cves table
        print("1. Deleting test CVEs...")
        cursor.execute("DELETE FROM cves WHERE source = 'test' OR url LIKE 'https://test.com/%'")
        deleted_counts['cves'] = cursor.rowcount
        print(f"   ✅ Deleted {cursor.rowcount} test CVEs")
        
        # 2. Delete from newsitems table
        print("2. Deleting test news items...")
        cursor.execute("DELETE FROM newsitems WHERE source = 'test' OR url LIKE 'https://test.com/%'")
        deleted_counts['newsitems'] = cursor.rowcount
        print(f"   ✅ Deleted {cursor.rowcount} test news items")
        
        # 3. Delete from raw_articles table
        print("3. Deleting test raw articles...")
        cursor.execute("DELETE FROM raw_articles WHERE source = 'test' OR url LIKE 'https://test.com/%'")
        deleted_counts['raw_articles'] = cursor.rowcount
        print(f"   ✅ Deleted {cursor.rowcount} test raw articles")
        
        # Commit the changes
        conn.commit()
        conn.close()
        
        # Show summary
        total_deleted = sum(deleted_counts.values())
        print(f"\n✅ Cleanup completed successfully!")
        print(f"📊 Summary:")
        print(f"   - CVEs deleted: {deleted_counts['cves']}")
        print(f"   - News items deleted: {deleted_counts['newsitems']}")
        print(f"   - Raw articles deleted: {deleted_counts['raw_articles']}")
        print(f"   - Total items deleted: {total_deleted}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_remaining_data():
    """Show what data remains in the database"""
    print("\n📋 Remaining Database Contents:")
    print("=" * 60)
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get remaining row counts
        cursor.execute("SELECT COUNT(*) FROM cves")
        cve_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM newsitems")
        news_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM raw_articles")
        article_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"   - CVEs: {cve_count} rows")
        print(f"   - News items: {news_count} rows")
        print(f"   - Raw articles: {article_count} rows")
        print(f"   - Total: {cve_count + news_count + article_count} rows")
        
        if cve_count + news_count + article_count == 0:
            print("\n🎉 Database is now clean - no data remaining!")
        else:
            print(f"\n📝 Database still contains {cve_count + news_count + article_count} items (non-test data)")
        
    except Exception as e:
        print(f"❌ Error getting remaining data: {e}")

def main():
    """Main cleanup function"""
    print("🚀 Supabase Test Data Cleanup")
    print("=" * 60)
    
    # Show current state
    show_remaining_data()
    
    # Confirm cleanup
    print("\n⚠️  This will delete ALL test data from your database.")
    print("   - Items with source = 'test'")
    print("   - Items with URLs starting with 'https://test.com/'")
    
    # Perform cleanup
    if cleanup_test_data():
        print("\n✅ Cleanup completed successfully!")
        
        # Show final state
        show_remaining_data()
        
    else:
        print("\n❌ Cleanup failed!")

if __name__ == "__main__":
    main()
