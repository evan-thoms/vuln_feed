import feedparser
from datetime import datetime
from models import Article
import requests
from bs4 import BeautifulSoup
import time
from db import is_article_scraped
from dateutil import parser


class EnglishScraper:
    def __init__(self, num_articles) -> None:
        self.FORCE = True
        self.max_arts = num_articles

    def normalize_date(self, date_str):
        date = parser.parse(date_str)
        return date.isoformat()
    
    def scrape_cisa(self):
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        vulns = data.get("vulnerabilities", [])
        print(f"Found {len(vulns)} known exploited vulnerabilities")
        articles = []
        for v in vulns[:self.max_arts]:
            cve_url = f"https://nvd.nist.gov/vuln/detail/{v.get("cveID")}"
            if is_article_scraped(cve_url) and not self.FORCE:
                print(f"Skipping already-scraped: {cve_url}")
                continue
            article = Article(
                id=cve_url,
                source="CISA KEV",
                title= v.get("vulnerabilityName"),
                title_translated=v.get("vulnerabilityName"),
                url=cve_url,
                content=v.get("shortDescription")+v.get("requiredAction"),
                content_translated=v.get("shortDescription")+v.get("requiredAction"),
                language="en",
                scraped_at=datetime.now().isoformat(),
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
                if is_article_scraped(url) and not self.FORCE:
                    print(f"Skipping already-scraped: {url}")
                    continue

                article = Article(
                    id=url,
                    source="Rapid7",
                    title=item["title"],
                    title_translated=item["title"],
                    url=url,
                    content=item["description"] + " Severity: "+str(item["data"].get("severity", [])),
                    content_translated=item["description"] + " Severity: "+str(item["data"].get("severity", [])),
                    language="en",
                    scraped_at=datetime.now().isoformat(),
                    published_date=self.normalize_date(item.get("created_at"))
                )
                articles.append(article)
            
        print(f"[Rapid7] Total collected: {len(articles)}")
        return articles




    def scrape_exploitdb(self):
        feed_url = "https://www.exploit-db.com/rss.xml"
        feed = feedparser.parse(feed_url)
        print(f"Found {len(feed.entries)} exploits.")
        articles_meta = []
        for entry in feed.entries[:1]:
            articles_meta.append({
                "title": entry.title,
                "url": entry.link,
                "date": entry.published if hasattr(entry, "published") else ""
            })
        print(f"Grabbed {len(articles_meta)} exploits")

        articles = []

        for article in articles_meta:
            if is_article_scraped(article["url"]):
                print("Exploit ", article["url"], " already scraped, moving on")
                continue
            print(f"Fetching: {article['title']} ({article['url']})")
            content = self.fetch_exploit_content(article['url'])
            print(f"Content preview:\n{content[:300]}...\n")

            article_obj = Article(
                id=article["url"],
                source="ExploitDB",
                title=article["title"],
                title_translated="",
                url=article["url"],
                content=content,
                content_translated="",
                language="en",
                scraped_at=datetime.now().isoformat()
            )
            articles.append(article_obj)
            time.sleep(1)

        return articles

    def fetch_exploit_content(self, url):
        if not url.startswith("http"):
            url = "https://" + url
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 404:
            print(f"Skipping 404 URL: {url}")
            return "404"

        soup = BeautifulSoup(r.text, "html.parser")

        code_block = soup.find("pre", id="code")
        code = code_block.get_text(strip=True) if code_block else ""

        desc_div = soup.find("div", class_="card-text")
        desc = desc_div.get_text(strip=True) if desc_div else ""

        full_text = desc + "\n\n" + code if code else desc

        if not full_text.strip():
            print(f"No useful content found at {url}")
            return ""

        return full_text
    def scrape_all(self):
        cisa = self.scrape_cisa()
        rapid = self.scrape_rapid_7()
        print("cisa len, ", len(cisa), " rapid len ", len(rapid))
        cisa.extend(rapid)
        return cisa
    
if __name__ == "__main__":
    scraper = EnglishScraper(2)
    exploits = scraper.scrape_rapid_7()
    for art in exploits:
        print(f"ID: {art.id}")
        print(f"Source: {art.source}")
        print(f"Title: {art.title}")
        print(f"Link: {art.url}")
        print(f"Language: {art.language}")
        print(f"Scraped at: {art.scraped_at}")
        print(f"Content preview:\n{art.content[:300]}")  # first 300 chars
        print(f"date: {art.published_date}")
        print("-" * 40)
    # exploits = scraper.scrape_rapid_7()
    


        