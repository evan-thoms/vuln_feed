import feedparser
from datetime import datetime
from models import Article
import requests
from bs4 import BeautifulSoup
import time
from db import is_article_scraped
from dateutil import parser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ChineseScraper:
    def __init__(self, num_articles):
        self.max_arts = num_articles
        self.FORCE = False  # Changed from True to False to enable duplicate checking
        self.session = self._create_fast_session()
    def _create_fast_session(self):
        """Fast session with minimal retry and proper timeout"""
        session = requests.Session()
        retry_strategy = Retry(total=2, backoff_factor=0.5)  # Quick retries
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; scraper)'})
        return session

    def scrape_freebuf(self, days_back: int = 7):
        print("[FreeBuf] Starting RSS scrape...")
        feed_url = "https://www.freebuf.com/feed"
        print(f"🔍 DEBUG: RSS feed URL: {feed_url}")
        
        try:
            print(f"🔍 DEBUG: Attempting to parse RSS feed...")
            
            # First try to fetch the RSS feed directly with requests to see what we get
            try:
                print(f"🔍 DEBUG: Testing direct RSS fetch...")
                # Use different headers to avoid 405 errors
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                r = requests.get(feed_url, headers=headers, timeout=10)
                print(f"🔍 DEBUG: Direct RSS response status: {r.status_code}")
                print(f"🔍 DEBUG: Direct RSS response headers: {dict(r.headers)}")
                print(f"🔍 DEBUG: Direct RSS response content length: {len(r.text)}")
                print(f"🔍 DEBUG: Direct RSS response content preview: {r.text[:200]}...")
            except Exception as e:
                print(f"🔍 DEBUG: Direct RSS fetch failed: {e}")
            
            feed = feedparser.parse(feed_url)
            print(f"🔍 DEBUG: Feed object type: {type(feed)}")
            print(f"🔍 DEBUG: Feed has entries attribute: {hasattr(feed, 'entries')}")
            print(f"🔍 DEBUG: Feed entries length: {len(feed.entries) if hasattr(feed, 'entries') else 'No entries attribute'}")
            print(f"🔍 DEBUG: Feed status: {getattr(feed, 'status', 'No status')}")
            print(f"🔍 DEBUG: Feed bozo: {getattr(feed, 'bozo', 'No bozo')}")
            
            # Try RSS parsing up to 3 times with different approaches
            attempts = 0
            max_attempts = 3
            
            while attempts < max_attempts:
                attempts += 1
                print(f"🔍 DEBUG: RSS parsing attempt {attempts}/{max_attempts}")
                
                if attempts == 1:
                    # First attempt: standard feedparser
                    feed = feedparser.parse(feed_url)
                elif attempts == 2:
                    # Second attempt: with session
                    try:
                        r = self.session.get(feed_url, timeout=10)
                        feed = feedparser.parse(r.content)
                        print(f"🔍 DEBUG: Second attempt using session")
                    except Exception as e:
                        print(f"🔍 DEBUG: Second attempt failed: {e}")
                        continue
                elif attempts == 3:
                    # Third attempt: with different user agent
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                        r = requests.get(feed_url, headers=headers, timeout=10)
                        feed = feedparser.parse(r.content)
                        print(f"🔍 DEBUG: Third attempt with different user agent")
                    except Exception as e:
                        print(f"🔍 DEBUG: Third attempt failed: {e}")
                        continue
                
                if hasattr(feed, 'entries') and len(feed.entries) > 0:
                    print(f"✅ RSS parsing successful on attempt {attempts}: Found {len(feed.entries)} articles")
                    break
                else:
                    print(f"⚠️ RSS attempt {attempts} returned no entries")
                    if attempts < max_attempts:
                        time.sleep(2)  # Wait 2 seconds between attempts
            
            if hasattr(feed, 'entries') and len(feed.entries) > 0:
                print(f"Found {len(feed.entries)} articles in the RSS feed.")
            else:
                print("⚠️ All RSS attempts failed, trying alternative FreeBuf scraping...")
                api_results = self.scrape_freebuf_vuls()
                if not api_results:
                    print("❌ Both RSS and API methods failed for FreeBuf")
                    return []
                return api_results
                
        except Exception as e:
            print(f"❌ RSS feed error: {e}")
            print(f"🔍 DEBUG: Exception type: {type(e)}")
            import traceback
            print(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")
            print(f"Trying alternative method...")
            api_results = self.scrape_freebuf_vuls()
            if not api_results:
                print("❌ Both RSS and API methods failed for FreeBuf")
                return []
            return api_results

        articles = []

        for entry in feed.entries[:self.max_arts]:
            article_url = entry.link
           
            if not self.FORCE and is_article_scraped(article_url):
                print("Article ", article_url, " already scraped, moving on")
                continue
            print(f"\nFetching: {article_url}")
            
            try:
                # Use session for consistent headers and timeout
                print(f"[INFO] Sending request to {article_url}")
                try:
                    res = self.session.get(article_url, timeout=10)
                    res.raise_for_status()
                    print("[INFO] Response received")
                except Exception as e:
                    print(f"❌ Error fetching {article_url}: {e}")
                    continue
                
                soup = BeautifulSoup(res.text, "html.parser")
                
                title = soup.find("div", class_="title")
                if not title:
                    title = soup.find("h1")
                title = title.get_text(strip=True) if title else entry.title
                
                body_div = soup.find("div", class_="artical-body")
                if not body_div:
                    print("No artical-body found, skipping.")
                    continue
                paragraphs = [p.get_text(strip=True) for p in body_div.find_all("p")]
                code_blocks = [pre.get_text(strip=True) for pre in body_div.find_all("pre")]
                full_text = "\n\n".join(paragraphs + code_blocks)
                # date = soup.find("span", class_="date")

                print("Title:", entry.title)
                print("PubDate:", entry.published)
                print("Link:", article_url)
                print("Preview:", full_text[:100], "...")
                
                article = Article(
                    id= None,
                    source= "FreeBuf",
                    title= title,
                    title_translated="",
                    url= article_url,
                    content= full_text,
                    content_translated="",
                    language= "zh",
                    scraped_at= datetime.now(),
                    published_date=self.normalize_date(entry.published)
                )
                articles.append(article)

            except Exception as e:
                print("Error fetching article:", e)
            
            time.sleep(1)   
        return articles
    def normalize_date(self, date_str):
        return parser.parse(date_str)


               
    def fetch_article_content(self, url, site):
         
            if not url.startswith("http"):
                url = "https://" + url
            try:
                # ULTRA-FAST timeout to prevent hanging - 5 seconds max
                r = self.session.get(url, timeout=5)  # Reduced from 10 to 5 seconds
                if r.status_code == 404:
                    print(f"Skipping 404 URL: {url}")
                    return "404"
            except requests.exceptions.Timeout:
                print(f"⏰ Timeout (5s) for {url} - skipping")
                return "TIMEOUT"
            except requests.exceptions.ConnectionError:
                print(f"🔌 Connection error for {url} - skipping")
                return "CONNECTION_ERROR"
            except Exception as e:
                print(f"❌ Error fetching {url}: {e}")
                return "ERROR"  # Return error code instead of empty string
            soup = BeautifulSoup(r.text, "html.parser")
            if site == "FreeBuf":
                content_div = soup.find("div", class_="artical-body")
            else:
                content_div = soup.find("div", id="js-article")
            if content_div:
                paragraphs = content_div.stripped_strings
                return "\n".join(paragraphs)
            else:
                print("No div.entry-content found!")
            return ""
    def scrape_anquanke(self):
        API_URL = "https://api.anquanke.com/data/v1/posts"
        # TAG = "漏洞"
        TAG = "漏洞情报"
        pages = 3  # Increased from 1 to 3 pages for more CVEs
        articles_meta = []

        for page in range(1, pages + 1):
            params = {
                "page": page,
                "tag": TAG
            }
            try:
                # ESSENTIAL: Add timeout to API call
                r = self.session.get(API_URL, params=params, timeout=10)
                data = r.json()
            except Exception as e:
                print(f"API error page {page}: {e}")
                continue  # ESSENTIAL: Continue with next page instead of crashing

            # Get more articles from Anquanke since it has high CVE density
            anquanke_limit = min(self.max_arts * 2, 15)  # Double the limit, max 15
            for post in data['data'][:anquanke_limit]:
                original_url = f"https://www.anquanke.com/post/id/{post['id']}"
                articles_meta.append({
                    "title": post['title'],
                    "url": original_url,
                    "date": post['date']
                })

        print(f"Grabbed {len(articles_meta)} articles")
        articles = []
        for article in articles_meta:
            if not self.FORCE and is_article_scraped(article["url"]):
                print("Article ", article["url"], " already scraped, moving on")
                continue
            print(f"Fetching: {article['title']} ({article['url']})")
            content = self.fetch_article_content(article['url'], "Anquanke")
            # ESSENTIAL: Skip failed articles instead of crashing
            if not content or content in ["404", "TIMEOUT", "CONNECTION_ERROR", "ERROR"]:
                print(f"⏭️ Skipping failed article: {content}")
                continue
            print(f"Content preview:\n{content[:100]}...\n") 
            article = Article(
                        id= None,
                        source= "Anquanke",
                        title= article["title"],
                        title_translated="",
                        url= article["url"],
                        content= content,
                        content_translated="",
                        language= "zh",
                        scraped_at= datetime.now(),
                        published_date=self.normalize_date(article["date"])
                    )
            articles.append(article)
        return articles

    def scrape_freebuf_vuls(self):
        API_URL = "https://www.freebuf.com/fapi/frontend/category/list"
        max_pages = 1
        articles = []

        for page in range(1, max_pages + 1):
            print(f"Scraping FreeBuf page {page}")

            params = {
                "name": "vuls",
                "tag": "category",
                "limit": 20,
                "page": page,
                "select": 0,
                "order": 0
            }

            try:
                # Use session with proper headers and timeout
                r = self.session.get(API_URL, params=params, timeout=10)
                r.raise_for_status()
                data = r.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 405:
                    print(f"⚠️ FreeBuf API returned 405 (Method Not Allowed) - API may be blocked")
                    print(f"   Falling back to RSS method only")
                    return []  # Return empty list instead of breaking
                else:
                    print(f"Error on page {page}: {e}")
                    break
            except Exception as e:
                print(f"Error on page {page}: {e}")
                break

            try:
                article_items = data["data"]["data_list"]
            except (KeyError, TypeError) as e:
                print(f"❌ Unexpected API response structure: {e}")
                print(f"   Response data: {data}")
                break
           
            print(f"[FreeBuf] Page {page}: Found {len(article_items)} items")

            for item in article_items[:self.max_arts]:
                post_title = item.get("post_title", "No Title")
                url = "https://www.freebuf.com"+item.get("url", "")
                if not self.FORCE and is_article_scraped(url):
                    print(f"Skipping already-scraped: {url}")
                    continue
                content = self.fetch_article_content(url, "FreeBuf")
                published = item.get("post_date", "")

                print("\nGathering:", post_title)
                print("URL:", url)
                print("Published:", published)

                article = Article(
                    id=None,
                    source="FreeBuf",
                    title=post_title,
                    title_translated="",
                    url=url,
                    content=content,
                    content_translated="",
                    language="zh",
                    scraped_at=datetime.now(),
                    published_date=self.normalize_date(published)
                )
                articles.append(article)

        print(f"[FreeBuf] Total collected: {len(articles)}")
        return articles

    def scrape_all(self):
        freeBuf = self.scrape_freebuf()
        anquanke = self.scrape_anquanke()
        print(f"[ChineseScraper] Anquanke: {len(anquanke)} articles, FreeBuf: {len(freeBuf)} articles")
        
        if len(freeBuf) == 0:
            print("⚠️ FreeBuf returned no articles - this may indicate API blocking or rate limiting")
        
        all_articles = freeBuf + anquanke
        print(f"[ChineseScraper] Total collected: {len(all_articles)} articles")
        return all_articles


if __name__ == "__main__":
    scraper = ChineseScraper(10)
    articles = scraper.scrape_freebuf()
    for art in articles:
        print(f"ID: {art.id}")
        # print(f"Source: {art.source}")
        print(f"Title: {art.title}")
        print(f"Link: {art.url}")
        # print(f"Language: {art.language}")
        # print(f"Scraped at: {art.scraped_at}")
        print(f"Content preview:\n{art.content[:300]}") 
        print("SDFJKSLDF")
        print(f"date: {art.published_date}"  ) # first 300 chars
        print("-" * 40)