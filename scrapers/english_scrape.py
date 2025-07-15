import feedparser
from datetime import datetime
from models import Article
import requests
from bs4 import BeautifulSoup
import time
from db import is_article_scraped

class EnglishScraper:
    def scrape_cisa(self):
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        print(f"Catalog Version: {data.get('catalogVersion')}")
        print(f"Released: {data.get('dateReleased')}")
        vulns = data.get("vulnerabilities", [])
        print(f"Found {len(vulns)} known exploited vulnerabilities")
        articles = []
        for v in vulns[:3]:
            cve_url = f"https://nvd.nist.gov/vuln/detail/{v.get("cveID")}"
            article = Article(
                id=cve_url,
                source="CISA KEV",
                title= v.get("vulnerabilityName"),
                title_translated="",
                url=cve_url,
                content=v.get("shortDescription")+v.get("requiredAction"),
                content_translated="",
                language="en",
                scraped_at=datetime.now().isoformat()
            )
            articles.append(article)
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
if __name__ == "__main__":
    scraper = EnglishScraper()
    exploits = scraper.scrape_cisa()
    for art in exploits:
        print(f"ID: {art.id}")
        print(f"Source: {art.source}")
        print(f"Title: {art.title}")
        print(f"Link: {art.url}")
        print(f"Language: {art.language}")
        print(f"Scraped at: {art.scraped_at}")
        print(f"Content preview:\n{art.content[:300]}")  # first 300 chars
        print("-" * 40)
    


        