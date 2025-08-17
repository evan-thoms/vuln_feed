#!/usr/bin/env python3
"""
Test script to verify the freshness and classification checking functions work correctly.
"""

from db import (
    init_db, 
    get_data_freshness_info, 
    is_article_classified, 
    get_classified_article,
    get_all_classified_data_with_freshness
)

def test_freshness_functions():
    """Test the freshness and classification functions"""
    print("🧪 Testing freshness and classification functions...")
    
    # Initialize database
    print("📊 Initializing database...")
    init_db()
    
    # Test freshness info
    print("\n📈 Getting data freshness information...")
    freshness = get_data_freshness_info()
    print(f"Freshness info: {freshness}")
    
    # Test classification checking
    print("\n🔍 Testing article classification checking...")
    test_url = "https://example.com/test-article"
    is_classified = is_article_classified(test_url)
    print(f"Is '{test_url}' classified? {is_classified}")
    
    # Test getting classified article
    print("\n📋 Testing getting classified article...")
    classified_data = get_classified_article(test_url)
    print(f"Classified data for '{test_url}': {classified_data}")
    
    # Test getting all classified data
    print("\n📊 Testing getting all classified data...")
    all_data = get_all_classified_data_with_freshness(limit=5)
    print(f"Total CVEs: {len(all_data['cves'])}")
    print(f"Total News: {len(all_data['news'])}")
    print(f"Freshness info: {all_data['freshness']}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    test_freshness_functions()
