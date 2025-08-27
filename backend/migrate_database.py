#!/usr/bin/env python3
"""
Database Migration Script for Session Tracking
Adds session_id and created_at columns to existing tables
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def migrate_database():
    """Migrate existing database to include session tracking"""
    print("🔄 Starting database migration for session tracking...")
    
    try:
        from db import get_connection, init_db
        
        # Initialize database to ensure tables exist
        init_db()
        
        # Get connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if columns already exist
        def column_exists(table, column):
            try:
                if hasattr(conn, 'server_version'):  # PostgreSQL
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = %s AND column_name = %s
                    """, (table, column))
                else:  # SQLite
                    cursor.execute("PRAGMA table_info({})".format(table))
                    columns = [row[1] for row in cursor.fetchall()]
                    return column in columns
                return cursor.fetchone() is not None
            except Exception:
                return False
        
        # Add session_id columns if they don't exist
        tables_to_migrate = [
            ('cves', 'session_id'),
            ('newsitems', 'session_id'),
            ('raw_articles', 'session_id')
        ]
        
        for table, column in tables_to_migrate:
            if not column_exists(table, column):
                print(f"➕ Adding {column} column to {table} table...")
                try:
                    if hasattr(conn, 'server_version'):  # PostgreSQL
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR(50) DEFAULT 'unknown'")
                    else:  # SQLite
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} VARCHAR(50) DEFAULT 'unknown'")
                    print(f"✅ Added {column} to {table}")
                except Exception as e:
                    print(f"⚠️ Error adding {column} to {table}: {e}")
            else:
                print(f"✅ {column} column already exists in {table}")
        
        # Add created_at columns if they don't exist
        timestamp_tables = [
            ('cves', 'created_at'),
            ('newsitems', 'created_at'),
            ('raw_articles', 'created_at')
        ]
        
        for table, column in timestamp_tables:
            if not column_exists(table, column):
                print(f"➕ Adding {column} column to {table} table...")
                try:
                    if hasattr(conn, 'server_version'):  # PostgreSQL
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    else:  # SQLite
                        # SQLite doesn't allow non-constant defaults, so add without default
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} DATETIME")
                        # Update existing records with current timestamp
                        cursor.execute(f"UPDATE {table} SET {column} = datetime('now') WHERE {column} IS NULL")
                    print(f"✅ Added {column} to {table}")
                except Exception as e:
                    print(f"⚠️ Error adding {column} to {table}: {e}")
            else:
                print(f"✅ {column} column already exists in {table}")
        
        # Create indexes
        indexes = [
            ('idx_cves_session_id', 'cves', 'session_id'),
            ('idx_cves_created_at', 'cves', 'created_at'),
            ('idx_news_session_id', 'newsitems', 'session_id'),
            ('idx_news_created_at', 'newsitems', 'created_at'),
            ('idx_raw_session_id', 'raw_articles', 'session_id'),
            ('idx_raw_created_at', 'raw_articles', 'created_at')
        ]
        
        for index_name, table, column in indexes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})")
                print(f"✅ Created index {index_name}")
            except Exception as e:
                print(f"⚠️ Error creating index {index_name}: {e}")
        
        # Update existing records with default session_id
        print("🔄 Updating existing records with default session_id...")
        try:
            cursor.execute("UPDATE cves SET session_id = 'legacy' WHERE session_id = 'unknown' OR session_id IS NULL")
            cursor.execute("UPDATE newsitems SET session_id = 'legacy' WHERE session_id = 'unknown' OR session_id IS NULL")
            cursor.execute("UPDATE raw_articles SET session_id = 'legacy' WHERE session_id = 'unknown' OR session_id IS NULL")
            print("✅ Updated existing records with 'legacy' session_id")
        except Exception as e:
            print(f"⚠️ Error updating existing records: {e}")
        
        conn.commit()
        conn.close()
        
        print("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False

def verify_migration():
    """Verify that migration was successful"""
    print("\n🔍 Verifying migration...")
    
    try:
        from db import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if columns exist
        if hasattr(conn, 'server_version'):  # PostgreSQL
            cursor.execute("""
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE table_name IN ('cves', 'newsitems', 'raw_articles')
                AND column_name IN ('session_id', 'created_at')
                ORDER BY table_name, column_name
            """)
        else:  # SQLite
            cursor.execute("PRAGMA table_info(cves)")
            cves_columns = [row[1] for row in cursor.fetchall()]
            cursor.execute("PRAGMA table_info(newsitems)")
            news_columns = [row[1] for row in cursor.fetchall()]
            cursor.execute("PRAGMA table_info(raw_articles)")
            raw_columns = [row[1] for row in cursor.fetchall()]
            
            print("📊 Column verification:")
            print(f"  CVEs: session_id={'✅' if 'session_id' in cves_columns else '❌'}, created_at={'✅' if 'created_at' in cves_columns else '❌'}")
            print(f"  News: session_id={'✅' if 'session_id' in news_columns else '❌'}, created_at={'✅' if 'created_at' in news_columns else '❌'}")
            print(f"  Raw: session_id={'✅' if 'session_id' in raw_columns else '❌'}, created_at={'✅' if 'created_at' in raw_columns else '❌'}")
        
        # Test session functions
        from db import get_items_by_session, get_recent_sessions
        
        legacy_items = get_items_by_session('legacy', limit=5)
        print(f"📋 Legacy items found: {legacy_items['total_cves']} CVEs, {legacy_items['total_news']} news")
        
        recent_sessions = get_recent_sessions(hours_back=24)
        print(f"📅 Recent sessions: {len(recent_sessions['cve_sessions'])} CVE sessions, {len(recent_sessions['news_sessions'])} news sessions")
        
        conn.close()
        print("✅ Migration verification completed!")
        return True
        
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Sentinel Database Migration Tool")
    print("=" * 50)
    
    success = migrate_database()
    
    if success:
        verify_migration()
        print("\n🎉 Migration completed successfully!")
        print("📋 Next steps:")
        print("1. Deploy the updated code to production")
        print("2. Test the manual trigger endpoint")
        print("3. Monitor the first scheduled run")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above and try again.")
