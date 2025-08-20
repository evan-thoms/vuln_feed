import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from models import Article
from dateutil import parser
import json

class RussianCVEScraper:
    def __init__(self, max_articles=20):
        self.max_arts = max_articles
        self.session = self._create_session()
        
    def _create_session(self):
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        return session

    def normalize_date(self, date_str):
        """Normalize various date formats"""
        try:
            return parser.parse(date_str)
        except:
            return datetime.now()

    # 1. SECURITYLAB.RU - Most comprehensive Russian security portal
    def scrape_securitylab_vulnerabilities(self):
        """
        SecurityLab.ru - Leading Russian cybersecurity portal
        Has RSS feeds and structured vulnerability sections
        """
        print("[SecurityLab.ru] Starting vulnerability scrape...")
        
        # SecurityLab RSS feed for vulnerabilities
        rss_url = "https://www.securitylab.ru/rss.php"
        
        try:
            feed = feedparser.parse(rss_url)
            print(f"[SecurityLab.ru] Found {len(feed.entries)} RSS entries")
            
            articles = []
            for entry in feed.entries[:self.max_arts]:
                # Filter for vulnerability-related content
                if any(keyword in entry.title.lower() for keyword in 
                       ['уязвимость', 'cve-', 'брешь', 'exploit', 'zero-day', 'патч']):
                    
                    content = self._fetch_securitylab_content(entry.link)
                    
                    article = Article(
                        id=None,
                        source="SecurityLab.ru",
                        title=entry.title,
                        title_translated="",
                        url=entry.link,
                        content=content,
                        content_translated="",
                        language="ru",
                        scraped_at=datetime.now(),
                        published_date=self.normalize_date(entry.published) if hasattr(entry, 'published') else datetime.now()
                    )
                    articles.append(article)
                    
                    print(f"SecurityLab: {entry.title}")
            
            # Also scrape direct vulnerability page
            vuln_articles = self._scrape_securitylab_vuln_page()
            articles.extend(vuln_articles)
            
            print(f"[SecurityLab.ru] Collected {len(articles)} vulnerability articles")
            return articles
            
        except Exception as e:
            print(f"[SecurityLab.ru] Error: {e}")
            return []

    def _scrape_securitylab_vuln_page(self):
        """Scrape SecurityLab vulnerability section directly"""
        vuln_url = "https://www.securitylab.ru/vulnerability/"
        articles = []
        
        try:
            response = self.session.get(vuln_url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for vulnerability entries
            vuln_links = soup.find_all('a', href=re.compile(r'/vulnerability/\d+'))
            
            for link in vuln_links[:self.max_arts//2]:
                vuln_url = "https://www.securitylab.ru" + link['href']
                title = link.get_text(strip=True)
                
                content = self._fetch_securitylab_content(vuln_url)
                
                if content:
                    articles.append(Article(
                        id=None,
                        source="SecurityLab.ru Vulnerabilities",
                        title=title,
                        title_translated="",
                        url=vuln_url,
                        content=content,
                        content_translated="",
                        language="ru",
                        scraped_at=datetime.now(),
                        published_date=datetime.now()
                    ))
            
            return articles
            
        except Exception as e:
            print(f"SecurityLab vulnerability page error: {e}")
            return []

    def _fetch_securitylab_content(self, url):
        """Fetch SecurityLab article content"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # SecurityLab content selectors
            content_selectors = [
                '.news-content',
                '.article-content', 
                '.vulnerability-info',
                '.content',
                'article'
            ]
            
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    return content_div.get_text(strip=True, separator='\n')
            
            return soup.get_text(strip=True, separator='\n')[:1500]
            
        except Exception as e:
            return f"Error fetching content: {e}"

    # 2. POSITIVE TECHNOLOGIES - Russian security company with vulnerability research
    def scrape_ptsecurity_blog(self):
        """
        Positive Technologies - Russian cybersecurity company
        Publishes vulnerability research and CVE analysis
        """
        print("[PT Security] Starting blog scrape...")
        
        # PT Security blog with vulnerability research
        blog_url = "https://www.ptsecurity.com/ru-ru/research/"
        
        try:
            response = self.session.get(blog_url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            # Look for research articles
            article_links = soup.find_all('a', href=re.compile(r'/research/'))
            
            for link in article_links[:self.max_arts]:
                if 'ptsecurity.com' not in link['href']:
                    article_url = "https://www.ptsecurity.com" + link['href']
                else:
                    article_url = link['href']
                
                title = link.get_text(strip=True)
                
                # Filter for vulnerability content
                if any(keyword in title.lower() for keyword in 
                       ['уязвимость', 'cve', 'exploit', 'исследование', 'анализ']):
                    
                    content = self._fetch_pt_content(article_url)
                    
                    if content:
                        articles.append(Article(
                            id=None,
                            source="PT Security",
                            title=title,
                            title_translated="",
                            url=article_url,
                            content=content,
                            content_translated="",
                            language="ru",
                            scraped_at=datetime.now(),
                            published_date=datetime.now()
                        ))
                        
                        print(f"PT Security: {title}")
            
            print(f"[PT Security] Collected {len(articles)} research articles")
            return articles
            
        except Exception as e:
            print(f"[PT Security] Error: {e}")
            return []

    def _fetch_pt_content(self, url):
        """Fetch PT Security content"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_div = soup.find('div', class_=['article-content', 'post-content', 'research-content'])
            if content_div:
                return content_div.get_text(strip=True, separator='\n')
            
            return soup.get_text(strip=True, separator='\n')[:1500]
            
        except Exception as e:
            return f"Error fetching PT content: {e}"

    # 3. ANTI-MALWARE.RU - Russian antimalware portal with vulnerability tracking
    def scrape_antimalware_vulnerabilities(self):
        """
        Anti-Malware.ru - Russian security portal
        Tracks vulnerabilities and provides CVE information
        """
        print("[Anti-Malware.ru] Starting scrape...")
        
        # Anti-Malware RSS feed
        rss_url = "https://www.anti-malware.ru/rss"
        
        try:
            feed = feedparser.parse(rss_url)
            print(f"[Anti-Malware.ru] Found {len(feed.entries)} RSS entries")
            
            articles = []
            for entry in feed.entries[:self.max_arts]:
                if any(keyword in entry.title.lower() or (hasattr(entry, 'summary') and keyword in entry.summary.lower())
                       for keyword in ['уязвимость', 'cve', 'брешь', 'exploit', 'патч']):
                    
                    content = self._fetch_antimalware_content(entry.link)
                    
                    article = Article(
                        id=None,
                        source="Anti-Malware.ru",
                        title=entry.title,
                        title_translated="",
                        url=entry.link,
                        content=content,
                        content_translated="",
                        language="ru",
                        scraped_at=datetime.now(),
                        published_date=self.normalize_date(entry.published) if hasattr(entry, 'published') else datetime.now()
                    )
                    articles.append(article)
                    
                    print(f"Anti-Malware: {entry.title}")
            
            print(f"[Anti-Malware.ru] Collected {len(articles)} vulnerability articles")
            return articles
            
        except Exception as e:
            print(f"[Anti-Malware.ru] Error: {e}")
            return []

    def _fetch_antimalware_content(self, url):
        """Fetch Anti-Malware content"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_div = soup.find('div', class_=['news-content', 'article-text', 'content'])
            if content_div:
                return content_div.get_text(strip=True, separator='\n')
            
            return soup.get_text(strip=True, separator='\n')[:1500]
            
        except Exception as e:
            return f"Error fetching content: {e}"

    # 4. XAKEP.RU - Russian hacker magazine with vulnerability coverage
    def scrape_xakep_vulnerabilities(self):
        """
        Xakep.ru - Russian hacker/security magazine
        Covers vulnerabilities, exploits, and security research
        """
        print("[Xakep.ru] Starting scrape...")
        
        # Xakep RSS feed
        rss_url = "https://xakep.ru/feed/"
        
        try:
            feed = feedparser.parse(rss_url)
            print(f"[Xakep.ru] Found {len(feed.entries)} RSS entries")
            
            articles = []
            for entry in feed.entries[:self.max_arts]:
                if any(keyword in entry.title.lower() or (hasattr(entry, 'summary') and keyword in entry.summary.lower())
                       for keyword in ['уязвимость', 'cve', 'exploit', 'хак', 'брешь', '0day', 'rce']):
                    
                    content = self._fetch_xakep_content(entry.link)
                    
                    article = Article(
                        id=None,
                        source="Xakep.ru",
                        title=entry.title,
                        title_translated="",
                        url=entry.link,
                        content=content,
                        content_translated="",
                        language="ru",
                        scraped_at=datetime.now(),
                        published_date=self.normalize_date(entry.published) if hasattr(entry, 'published') else datetime.now()
                    )
                    articles.append(article)
                    
                    print(f"Xakep: {entry.title}")
            
            print(f"[Xakep.ru] Collected {len(articles)} vulnerability articles")
            return articles
            
        except Exception as e:
            print(f"[Xakep.ru] Error: {e}")
            return []

    def _fetch_xakep_content(self, url):
        """Fetch Xakep content"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_div = soup.find('div', class_=['entry-content', 'post-content', 'article-content'])
            if content_div:
                return content_div.get_text(strip=True, separator='\n')
            
            return soup.get_text(strip=True, separator='\n')[:1500]
            
        except Exception as e:
            return f"Error fetching content: {e}"

    # 5. HABR.COM Security Hub - Russian tech community
    def scrape_habr_infosec(self):
        """
        Habr.com InfoSecurity hub - Russian tech community
        Active vulnerability discussions and CVE analysis
        """
        print("[Habr InfoSec] Starting scrape...")
        
        # Habr InfoSecurity RSS
        rss_url = "https://habr.com/ru/rss/hub/infosecurity/"
        
        try:
            feed = feedparser.parse(rss_url)
            print(f"[Habr InfoSec] Found {len(feed.entries)} RSS entries")
            
            articles = []
            for entry in feed.entries[:self.max_arts]:
                if any(keyword in entry.title.lower() or (hasattr(entry, 'summary') and keyword in entry.summary.lower())
                       for keyword in ['уязвимость', 'cve', 'exploit', 'брешь', 'rce', 'xss', 'sqli']):
                    
                    content = self._fetch_habr_content(entry.link)
                    
                    article = Article(
                        id=None,
                        source="Habr InfoSec",
                        title=entry.title,
                        title_translated="",
                        url=entry.link,
                        content=content,
                        content_translated="",
                        language="ru",
                        scraped_at=datetime.now(),
                        published_date=self.normalize_date(entry.published) if hasattr(entry, 'published') else datetime.now()
                    )
                    articles.append(article)
                    
                    print(f"Habr: {entry.title}")
            
            print(f"[Habr InfoSec] Collected {len(articles)} vulnerability articles")
            return articles
            
        except Exception as e:
            print(f"[Habr InfoSec] Error: {e}")
            return []

    def _fetch_habr_content(self, url):
        """Fetch Habr content"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Habr article content
            content_div = soup.find('div', class_=['tm-article-body', 'post__text', 'content'])
            if content_div:
                return content_div.get_text(strip=True, separator='\n')
            
            return soup.get_text(strip=True, separator='\n')[:1500]
            
        except Exception as e:
            return f"Error fetching content: {e}"

    # 6. BI.ZONE Threat Intelligence (Russian)
    def scrape_bizone_threats(self):
        """
        BI.ZONE - Russian cybersecurity company
        Threat intelligence and vulnerability research
        """
        print("[BI.ZONE] Starting threat intelligence scrape...")
        
        blog_url = "https://bi.zone/blog/"
        
        try:
            response = self.session.get(blog_url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            # Look for blog posts
            post_links = soup.find_all('a', href=re.compile(r'/blog/'))
            
            for link in post_links[:self.max_arts]:
                if 'bi.zone' not in link['href']:
                    post_url = "https://bi.zone" + link['href']
                else:
                    post_url = link['href']
                
                title = link.get_text(strip=True)
                
                if any(keyword in title.lower() for keyword in 
                       ['уязвимость', 'cve', 'exploit', 'угроза', 'атака']):
                    
                    content = self._fetch_bizone_content(post_url)
                    
                    if content:
                        articles.append(Article(
                            id=None,
                            source="BI.ZONE",
                            title=title,
                            title_translated="",
                            url=post_url,
                            content=content,
                            content_translated="",
                            language="ru",
                            scraped_at=datetime.now(),
                            published_date=datetime.now()
                        ))
                        
                        print(f"BI.ZONE: {title}")
            
            print(f"[BI.ZONE] Collected {len(articles)} threat articles")
            return articles
            
        except Exception as e:
            print(f"[BI.ZONE] Error: {e}")
            return []

    def _fetch_bizone_content(self, url):
        """Fetch BI.ZONE content"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_div = soup.find('div', class_=['post-content', 'article-content', 'blog-content'])
            if content_div:
                return content_div.get_text(strip=True, separator='\n')
            
            return soup.get_text(strip=True, separator='\n')[:1500]
            
        except Exception as e:
            return f"Error fetching content: {e}"

    # Main scraping method
    def scrape_all_russian_sources(self):
        """Scrape all Russian vulnerability sources"""
        all_articles = []
        
        print("\n=== Starting Russian CVE/Vulnerability Scraping ===\n")
        
        # Scrape all sources
        sources = [
            self.scrape_securitylab_vulnerabilities,
            self.scrape_ptsecurity_blog,
            self.scrape_antimalware_vulnerabilities,
            self.scrape_xakep_vulnerabilities,
            self.scrape_habr_infosec,
            self.scrape_bizone_threats
        ]
        
        for source_func in sources:
            try:
                articles = source_func()
                all_articles.extend(articles)
                print(f"Source completed: {len(articles)} articles")
            except Exception as e:
                print(f"Source failed: {e}")
            
            # Small delay between sources
            import time
            time.sleep(2)
        
        # Remove duplicates by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)
        
        print(f"\n=== TOTAL: {len(unique_articles)} unique Russian vulnerability articles ===")
        return unique_articles

# Usage example
if __name__ == "__main__":
    scraper = RussianCVEScraper(max_articles=10)
    
    # Test individual sources
    print("Testing SecurityLab.ru...")
    seclab_articles = scraper.scrape_securitylab_vulnerabilities()
    
    print("Testing Xakep.ru...")
    xakep_articles = scraper.scrape_xakep_vulnerabilities()
    
    # Or scrape all Russian sources
    print("Scraping all Russian sources...")
    all_articles = scraper.scrape_all_russian_sources()
    
    # Display results
    for article in all_articles[:5]:  # Show first 5
        print(f"\nSource: {article.source}")
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        print(f"Content preview: {article.content[:200]}...")
        print("-" * 60)