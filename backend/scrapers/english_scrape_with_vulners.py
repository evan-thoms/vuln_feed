import feedparser
from datetime import datetime
from models import Article
import requests
from bs4 import BeautifulSoup
import time
from db import is_article_scraped
from dateutil import parser
import vulners
import sys
import os
from utils.date_utils import parse_date_safe, normalize_date_for_article

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EnglishScraperWithVulners:
    def __init__(self, num_articles) -> None:
        self.FORCE = False
        self.max_arts = num_articles
        # Initialize Vulners API
        try:
            self.vulners_api = vulners.Vulners(api_key="9DZAW2NZ8L5502PAVQURU0VRCL7WLXNO61JEX3A4MCF1T0SNRS4THDSVMITCHUHM")
        except AttributeError:
            # Fallback for different vulners package versions
            self.vulners_api = vulners.VulnersApi(api_key="9DZAW2NZ8L5502PAVQURU0VRCL7WLXNO61JEX3A4MCF1T0SNRS4THDSVMITCHUHM")

    def normalize_date(self, date_str):
        return parser.parse(date_str)
    
    def scrape_vulners_cves(self):
        """Scrape CVEs from Vulners API - integrated into the same workflow"""
        print("🔍 Scraping Vulners for CVEs...")
        articles = []
        
        try:
            # Get recent high-severity CVEs
            query = "type:cve"
            
            # Try different API methods based on vulners package version
            try:
                # Use requests timeout instead of signal (works on all platforms)
                search_result = self.vulners_api.search(
                    query,
                    limit=self.max_arts * 2
                )
                    
            except (AttributeError, Exception) as e:
                print(f"⚠️ Vulners API search method failed: {e}")
                return []
            
            # Debug: Print Vulners API response
            print(f"🔍 Vulners API Debug:")
            print(f"  Query: {query}")
            print(f"  Results type: {type(search_result)}")
            print(f"  Results count: {len(search_result) if search_result else 0}")
            if search_result and len(search_result) > 0:
                print(f"  First result keys: {list(search_result[0].keys())}")
                print(f"  First result published: {search_result[0].get('published', 'N/A')}")
            print(f"  ---")
            
            if search_result:
                # Sort by published date (most recent first)
                sorted_results = sorted(search_result, 
                                      key=lambda x: x.get('published', ''), 
                                      reverse=True)
                
                print(f"🔍 Sorted {len(sorted_results)} CVEs by date (newest first)")
                
                for doc in sorted_results:
                    cve_id = doc.get('id', 'Unknown')
                    if not cve_id.startswith('CVE-'):
                        continue
                    
                    # Parse publication date and check if it's recent (last 7 days)
                    published_str = doc.get('published', '')
                    if published_str:
                        published_date = parse_date_safe(published_str)
                        if published_date:
                            days_old = (datetime.now() - published_date).days
                            
                            if days_old > 7:
                                print(f"  Skipping old CVE {cve_id}: {days_old} days old")
                                continue
                        else:
                            print(f"  Skipping CVE {cve_id}: Invalid date format")
                            continue
                    
                    # Check if already scraped (same as other sources)
                    cve_url = doc.get('href', f"https://vulners.com/cve/{cve_id}")
                    if not self.FORCE and is_article_scraped(cve_url):
                        print(f"Skipping already-scraped: {cve_url}")
                        continue
                    
                    title = doc.get('title', f"Vulnerability: {cve_id}")
                    description = doc.get('description', '') or doc.get('short_description', '')
                    
                    if not description:
                        description = f"Vulnerability details for {cve_id}"
                    
                    # Parse publication date
                    published_str = doc.get('published', '')
                    published_date = normalize_date_for_article(published_str)
                    
                    # Get CVSS score for severity info
                    cvss_score = doc.get('cvss', {}).get('score', 0)
                    severity_info = f" CVSS Score: {cvss_score}" if cvss_score > 0 else ""
                    
                    # Debug: Print Vulners article details
                    print(f"🔍 Vulners Article Debug:")
                    print(f"  CVE ID: {cve_id}")
                    print(f"  Title: {title}")
                    print(f"  Published: {published_date}")
                    print(f"  CVSS Score: {cvss_score}")
                    print(f"  Severity: {self._cvss_to_severity(cvss_score)}")
                    print(f"  URL: {cve_url}")
                    print(f"  Content length: {len(description)} chars")
                    print(f"  ---")
                    
                    article = Article(
                        id=None,
                        source="Vulners",
                        title=title,
                        title_translated=title,
                        url=cve_url,
                        content=f"CVE ID: {cve_id}. {description}{severity_info}",
                        content_translated=f"CVE ID: {cve_id}. {description}{severity_info}",
                        language="en",
                        scraped_at=datetime.now(),
                        published_date=published_date
                    )
                    
                    articles.append(article)
            
            print(f"✅ Vulners: Found {len(articles)} CVEs")
            
        except Exception as e:
            print(f"❌ Error fetching from Vulners: {e}")
            # Return empty list to prevent pipeline from hanging
            return []
        
        return articles
    
    def _cvss_to_severity(self, cvss_score):
        """Convert CVSS score to severity level"""
        if cvss_score >= 9.0:
            return "Critical"
        elif cvss_score >= 7.0:
            return "High"
        elif cvss_score >= 4.0:
            return "Medium"
        else:
            return "Low"
      
    def scrape_cisa(self):
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        vulns = data.get("vulnerabilities", [])
        print(f"Found {len(vulns)} known exploited vulnerabilities")
        articles = []
        for v in vulns[:self.max_arts]:
            cve_url = f"https://nvd.nist.gov/vuln/detail/{v.get('cveID')}"
            if not self.FORCE and is_article_scraped(cve_url):
                print(f"Skipping already-scraped: {cve_url}")
                continue
            article = Article(
                id=None,
                source="CISA KEV",
                title= v.get("vulnerabilityName"),
                title_translated=v.get("vulnerabilityName"),
                url=cve_url,
                content=f"CVE ID: {v.get('cveID')}. {v.get('shortDescription')}{v.get('requiredAction')}",
                content_translated=f"CVE ID: {v.get('cveID')}. {v.get('shortDescription')}{v.get('requiredAction')}",
                language="en",
                scraped_at=datetime.now(),
                published_date=self.normalize_date(v.get("dateAdded"))
            )
            articles.append(article)
        return articles
    
    def scrape_rapid_7(self):
        API_URL = "https://www.rapid7.com/api/vulnerability-list/"
        r = requests.get(API_URL)
        data = r.json()
        max_pages = 1

        articles = []

        for page in range(1, max_pages+1):
            print("scraping page: ", page)
            
            params = {
                "page": page,
                "sort": "id,DESC"
            }
            r = requests.get(API_URL, params=params)
            r.raise_for_status()
            data = r.json()

            batch = data.get("data", [])
            print(f"[Rapid7] Page {page}: Found {len(batch)} items")

            if not batch:
                print("batch empty")
                break 
            for item in batch[:self.max_arts]:
                print("\ngathering ", item["title"])
                print("content: ",item["description"][:100] )
                print("data: ", self.normalize_date(item.get("created_at")))
                urls = [alt["name"] for alt in item["data"].get("alternate_ids", []) if alt["namespace"] == "URL"]
                url = urls[0] if urls else f"https://www.rapid7.com/db/vulnerabilities/{item['identifier']}/"
                if not self.FORCE and is_article_scraped(url):
                    print(f"Skipping already-scraped: {url}")
                    continue

                article = Article(
                    id=None,
                    source="Rapid7",
                    title=item["title"],
                    title_translated=item["title"],
                    url=url,
                    content=f"{item['title']}. {item['description']} Severity: {str(item['data'].get('severity', []))}",
                    content_translated=f"{item['title']}. {item['description']} Severity: {str(item['data'].get('severity', []))}",
                    language="en",
                    scraped_at=datetime.now(),
                    published_date=self.normalize_date(item.get("created_at"))
                )
                articles.append(article)
            
        print(f"[Rapid7] Total collected: {len(articles)}")
        return articles

    def scrape_all(self):
        """Scrape from all English sources including Vulners"""
        print("🚀 Starting English scraping with Vulners integration...")
        
        all_articles = []
        
        # Scrape from existing sources
        print("📰 Scraping CISA KEV...")
        cisa_articles = self.scrape_cisa()
        all_articles.extend(cisa_articles)
        
        print("📰 Scraping Rapid7...")
        rapid7_articles = self.scrape_rapid_7()
        all_articles.extend(rapid7_articles)
        
        # # Scrape from Vulners (high CVE density)
        # vulners_articles = self.scrape_vulners_cves()
        # all_articles.extend(vulners_articles)
        
        print(f"\n📊 Total articles collected: {len(all_articles)}")
        print(f"   - CISA KEV: {len(cisa_articles)}")
        print(f"   - Rapid7: {len(rapid7_articles)}")
        # print(f"   - Vulners: {len(vulners_articles)}")
        
        return all_articles

# Keep the original class for backward compatibility
class EnglishScraper(EnglishScraperWithVulners):
    """Backward compatibility - now includes Vulners integration"""
    pass
