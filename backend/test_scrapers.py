#!/usr/bin/env python3
"""
Test script to test each scraper individually
"""

import os
import sys
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_chinese_scraper():
    print("=" * 50)
    print("🧪 Testing Chinese Scraper")
    print("=" * 50)
    
    from scrapers.chinese_scrape import ChineseScraper
    
    scraper = ChineseScraper(5)
    
    print("Testing FreeBuf RSS...")
    try:
        articles = scraper.scrape_freebuf()
        print(f"✅ FreeBuf: {len(articles)} articles")
        for i, art in enumerate(articles[:3]):
            print(f"  {i+1}. {art.title[:50]}...")
    except Exception as e:
        print(f"❌ FreeBuf failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting Anquanke...")
    try:
        articles = scraper.scrape_anquanke()
        print(f"✅ Anquanke: {len(articles)} articles")
        for i, art in enumerate(articles[:3]):
            print(f"  {i+1}. {art.title[:50]}...")
    except Exception as e:
        print(f"❌ Anquanke failed: {e}")
        import traceback
        traceback.print_exc()

def test_english_scraper():
    print("=" * 50)
    print("🧪 Testing English Scraper")
    print("=" * 50)
    
    from scrapers.english_scrape_with_vulners import EnglishScraperWithVulners
    
    scraper = EnglishScraperWithVulners(5)
    
    print("Testing CISA KEV...")
    try:
        articles = scraper.scrape_cisa()
        print(f"✅ CISA KEV: {len(articles)} articles")
        for i, art in enumerate(articles[:3]):
            print(f"  {i+1}. {art.title[:50]}...")
    except Exception as e:
        print(f"❌ CISA KEV failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting Rapid7...")
    try:
        articles = scraper.scrape_rapid_7()
        print(f"✅ Rapid7: {len(articles)} articles")
        for i, art in enumerate(articles[:3]):
            print(f"  {i+1}. {art.title[:50]}...")
    except Exception as e:
        print(f"❌ Rapid7 failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting Vulners...")
    try:
        articles = scraper.scrape_vulners_cves()
        print(f"✅ Vulners: {len(articles)} articles")
        for i, art in enumerate(articles[:3]):
            print(f"  {i+1}. {art.title[:50]}...")
    except Exception as e:
        print(f"❌ Vulners failed: {e}")
        import traceback
        traceback.print_exc()

def test_russian_scraper():
    print("=" * 50)
    print("🧪 Testing Russian Scraper")
    print("=" * 50)
    
    from scrapers.russian_scrape import RussianScraper
    
    scraper = RussianScraper(5)
    
    print("Testing Anti-Malware...")
    try:
        articles = scraper.scrape_all()
        print(f"✅ Anti-Malware: {len(articles)} articles")
        for i, art in enumerate(articles[:3]):
            print(f"  {i+1}. {art.title[:50]}...")
    except Exception as e:
        print(f"❌ Anti-Malware failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print(f"🧪 Testing all scrapers at {datetime.now()}")
    
    test_chinese_scraper()
    test_english_scraper()
    test_russian_scraper()
    
    print("\n" + "=" * 50)
    print("✅ All scraper tests completed!")
    print("=" * 50)
