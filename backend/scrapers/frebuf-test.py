#!/usr/bin/env python3
"""
Quick test script to verify FreeBuf RSS feed is working with proper headers
"""

import feedparser
import requests
from datetime import datetime

def test_freebuf_rss():
    """Test FreeBuf RSS feed parsing with and without headers"""
    
    feed_url = "https://www.freebuf.com/feed"
    
    print("=" * 60)
    print("FreeBuf RSS Feed Test")
    print("=" * 60)
    
    # Test 1: Direct feedparser (original broken method)
    print("\n1. Testing direct feedparser.parse() (original method):")
    try:
        feed_direct = feedparser.parse(feed_url)
        print(f"   Status: {getattr(feed_direct, 'status', 'No status')}")
        print(f"   Entries found: {len(feed_direct.entries)}")
        if hasattr(feed_direct, 'bozo') and feed_direct.bozo:
            print(f"   Bozo error: {feed_direct.bozo_exception}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: With proper headers (fixed method)
    print("\n2. Testing with proper browser headers (fixed method):")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'Accept-Language': 'en-US,en;q=0.9,zh;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
        
        print("   Fetching RSS with headers...")
        response = requests.get(feed_url, headers=headers, timeout=15)
        print(f"   HTTP Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"   Content Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("   Parsing with feedparser...")
            feed = feedparser.parse(response.content)
            print(f"   Feed Title: {feed.get('feed', {}).get('title', 'No title')}")
            print(f"   Feed Language: {feed.get('feed', {}).get('language', 'No language')}")
            print(f"   Entries found: {len(feed.entries)}")
            
            if feed.entries:
                print(f"   Latest entry: '{feed.entries[0].title}'")
                print(f"   Published: {feed.entries[0].get('published', 'No date')}")
                print(f"   Link: {feed.entries[0].get('link', 'No link')}")
                
                # Show first few entries
                print("\n   First 3 entries:")
                for i, entry in enumerate(feed.entries[:3]):
                    print(f"     {i+1}. {entry.title}")
                    print(f"        URL: {entry.link}")
                    print(f"        Date: {entry.get('published', 'No date')}")
                    print()
            else:
                print("   ⚠️  No entries found even with headers!")
                if hasattr(feed, 'bozo') and feed.bozo:
                    print(f"   Bozo error: {feed.bozo_exception}")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection error")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Check if we can access article content
    print("\n3. Testing article content fetching:")
    try:
        # Re-fetch to get entries
        response = requests.get(feed_url, headers=headers, timeout=15)
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            if feed.entries:
                test_url = feed.entries[0].link
                print(f"   Testing article: {test_url}")
                
                article_response = requests.get(test_url, headers=headers, timeout=10)
                print(f"   Article HTTP Status: {article_response.status_code}")
                
                if article_response.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(article_response.text, "html.parser")
                    
                    # Check for expected content divs
                    title_div = soup.find("div", class_="title") or soup.find("h1")
                    body_div = soup.find("div", class_="artical-body")
                    
                    print(f"   Title found: {'✓' if title_div else '✗'}")
                    print(f"   Body div found: {'✓' if body_div else '✗'}")
                    
                    if title_div:
                        print(f"   Title text: {title_div.get_text(strip=True)[:100]}...")
                    if body_div:
                        print(f"   Body preview: {body_div.get_text(strip=True)[:100]}...")
                else:
                    print(f"   ❌ Could not fetch article: {article_response.status_code}")
            else:
                print("   ❌ No entries to test")
        else:
            print("   ❌ Could not re-fetch RSS feed")
    except Exception as e:
        print(f"   ❌ Article test error: {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_freebuf_rss()