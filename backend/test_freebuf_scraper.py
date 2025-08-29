#!/usr/bin/env python3
"""
Test FreeBuf scraper locally
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_freebuf_scraper():
    """Test the FreeBuf scraper"""
    print("🧪 Testing FreeBuf Scraper")
    print("=" * 50)
    
    try:
        from scrapers.chinese_scrape import ChineseScraper
        
        # Create scraper instance
        scraper = ChineseScraper(num_articles=5)
        
        print("🔍 Testing FreeBuf RSS scraping...")
        articles = scraper.scrape_freebuf(days_back=1)
        
        print(f"✅ FreeBuf scraping completed!")
        print(f"📊 Articles collected: {len(articles)}")
        
        if articles:
            print(f"📋 Sample articles:")
            for i, article in enumerate(articles[:3]):
                print(f"  {i+1}. {article.source}: {article.title[:50]}...")
        else:
            print("⚠️ No articles collected")
            
    except Exception as e:
        print(f"❌ FreeBuf scraping failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_freebuf_scraper()
