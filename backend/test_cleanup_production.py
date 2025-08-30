#!/usr/bin/env python3
"""
Production test script for database cleanup
Tests with your actual Supabase database
"""

import os
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_production_cleanup():
    """Test cleanup with production database"""
    print("🧪 Testing Production Database Cleanup")
    print("=" * 50)
    
    # Set your production database URL
    DATABASE_URL = "postgresql://postgres.inanivtnpahnihaeqdpw:sNZGQnfitefaQiGO@aws-1-us-east-2.pooler.supabase.com:6543/postgres"
    os.environ['DATABASE_URL'] = DATABASE_URL
    
    print("🔍 Environment setup:")
    print(f"  DATABASE_URL: {DATABASE_URL[:50]}...")
    
    try:
        from db_cleanup import add_test_data_for_cleanup, cleanup_old_data
        
        # Step 1: Add test data
        print(f"\n📝 Step 1: Adding test data...")
        test_items_added = add_test_data_for_cleanup()
        print(f"✅ Added {test_items_added} test items")
        
        if test_items_added > 0:
            # Step 2: Run dry run
            print(f"\n🔍 Step 2: Running dry run cleanup...")
            dry_run_stats = cleanup_old_data(months_old=3, dry_run=True)
            
            print(f"📊 Dry run results:")
            print(f"  - Success: {dry_run_stats['success']}")
            print(f"  - Total to delete: {dry_run_stats['total_deleted']}")
            for table, stats in dry_run_stats['tables_cleaned'].items():
                print(f"  - {table}: {stats['count_to_delete']} items")
            
            # Step 3: Run actual cleanup
            print(f"\n🧹 Step 3: Running actual cleanup...")
            cleanup_stats = cleanup_old_data(months_old=3, dry_run=False)
            
            print(f"📊 Actual cleanup results:")
            print(f"  - Success: {cleanup_stats['success']}")
            print(f"  - Total deleted: {cleanup_stats['total_deleted']}")
            for table, stats in cleanup_stats['tables_cleaned'].items():
                print(f"  - {table}: {stats['deleted_count']} items deleted")
            
            # Step 4: Verify cleanup
            print(f"\n✅ Step 4: Verification")
            print(f"  - Test items added: {test_items_added}")
            print(f"  - Items actually deleted: {cleanup_stats['total_deleted']}")
            
            if cleanup_stats['total_deleted'] >= test_items_added:
                print(f"✅ SUCCESS: Cleanup working correctly!")
                print(f"🎯 PROOF: {cleanup_stats['total_deleted']} test items were successfully deleted from production database")
            else:
                print(f"⚠️ PARTIAL: Some items may not have been cleaned up")
                
        else:
            print("⚠️ No test data was added, cannot verify cleanup")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_production_cleanup()
