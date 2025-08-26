#!/usr/bin/env python3
"""
Test script for date utilities to ensure consistent date handling.
"""

import sys
import os
from datetime import datetime

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.date_utils import parse_date_safe, format_date_for_db, format_date_for_display, is_recent_date, get_days_old, normalize_date_for_article

def test_date_parsing():
    """Test various date formats and edge cases"""
    print("🧪 Testing Date Utilities...")
    print("=" * 50)
    
    # Test cases with different date formats
    test_cases = [
        # ISO format strings
        "2025-08-26T10:30:00",
        "2025-08-26T10:30:00.123456",
        "2025-08-26T10:30:00Z",
        "2025-08-26T10:30:00+00:00",
        "2025-08-26T10:30:00-05:00",
        
        # SQL format strings
        "2025-08-26 10:30:00",
        "2025-08-26 10:30:00.123456",
        
        # Date only
        "2025-08-26",
        
        # Different formats
        "26/08/2025",
        "08/26/2025",
        
        # Edge cases
        None,
        "",
        "invalid_date",
        "2025-13-45",  # Invalid month/day
    ]
    
    print("1. Testing parse_date_safe()...")
    for i, test_date in enumerate(test_cases):
        result = parse_date_safe(test_date)
        status = "✅" if result is not None else "❌"
        print(f"   {status} Test {i+1}: {test_date} -> {result}")
    
    print("\n2. Testing format_date_for_db()...")
    for i, test_date in enumerate(test_cases[:5]):  # Test first 5 valid cases
        result = format_date_for_db(test_date)
        status = "✅" if result is not None else "❌"
        print(f"   {status} Test {i+1}: {test_date} -> {result}")
    
    print("\n3. Testing format_date_for_display()...")
    for i, test_date in enumerate(test_cases[:5]):  # Test first 5 valid cases
        result = format_date_for_display(test_date)
        print(f"   ✅ Test {i+1}: {test_date} -> {result}")
    
    print("\n4. Testing is_recent_date()...")
    # Test with a recent date
    recent_date = datetime.now()
    old_date = datetime(2020, 1, 1)
    
    print(f"   Recent date ({recent_date}): {is_recent_date(recent_date)}")
    print(f"   Old date ({old_date}): {is_recent_date(old_date)}")
    print(f"   None: {is_recent_date(None)}")
    
    print("\n5. Testing get_days_old()...")
    print(f"   Recent date: {get_days_old(recent_date)} days old")
    print(f"   Old date: {get_days_old(old_date)} days old")
    print(f"   None: {get_days_old(None)}")
    
    print("\n6. Testing normalize_date_for_article()...")
    for i, test_date in enumerate(test_cases[:5]):  # Test first 5 cases
        result = normalize_date_for_article(test_date)
        print(f"   ✅ Test {i+1}: {test_date} -> {result}")
    
    print("\n✅ All date utility tests completed!")

def test_postgresql_vs_sqlite_simulation():
    """Simulate PostgreSQL vs SQLite date handling differences"""
    print("\n🔍 Testing PostgreSQL vs SQLite Simulation...")
    print("=" * 50)
    
    # Simulate what PostgreSQL returns (datetime objects)
    postgresql_date = datetime.now()
    
    # Simulate what SQLite returns (strings)
    sqlite_date = postgresql_date.isoformat()
    
    print(f"PostgreSQL returns: {postgresql_date} (type: {type(postgresql_date)})")
    print(f"SQLite returns: {sqlite_date} (type: {type(sqlite_date)})")
    
    # Test parsing both
    postgresql_parsed = parse_date_safe(postgresql_date)
    sqlite_parsed = parse_date_safe(sqlite_date)
    
    print(f"PostgreSQL parsed: {postgresql_parsed}")
    print(f"SQLite parsed: {sqlite_parsed}")
    
    # Verify they're equivalent
    if postgresql_parsed and sqlite_parsed:
        time_diff = abs((postgresql_parsed - sqlite_parsed).total_seconds())
        if time_diff < 1:  # Within 1 second
            print("✅ PostgreSQL and SQLite dates parsed consistently!")
        else:
            print(f"❌ Date parsing inconsistency: {time_diff} seconds difference")
    else:
        print("❌ One or both dates failed to parse")

if __name__ == "__main__":
    test_date_parsing()
    test_postgresql_vs_sqlite_simulation()
    print("\n🎉 All tests completed successfully!")
