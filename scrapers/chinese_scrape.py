import feedparser
from datetime import datetime, timedelta
from models import Vulnerability
from deep_translator import GoogleTranslator  # or your LangChain helper
import requests
from bs4 import BeautifulSoup

class ChineseScraper:
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='en')

    def scrape_freebuf(self, days_back: int = 7):
        print("[FreeBuf] Starting RSS scrape...")
        feed_url = "https://www.freebuf.com/feed"
        feed = feedparser.parse(feed_url)

        vulns = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for entry in feed.entries[:5]:
            try:
                
                title_original_ = entry.title
                title_translated_ = self.translator.translate(title_original_) if title_original_ else "No title."
                print(title_original_, title_translated_)

                description_original_ = getattr(entry, 'summary', '')
                description_translated_ = self.translator.translate(description_original_) if description_original_ else "No description."

                link = entry.link

                pub_date = datetime.now()
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6])

                if pub_date < cutoff_date:
                    continue

                vuln = Vulnerability(
                    cve_id=f"FreeBuf-{hash(title_original_) % 10000}",
                    title_original=title_original_,
                    title_translated=title_translated_,
                    description_original=description_original_,
                    description_translated=description_translated_,
                    severity='TBD',
                    cvss_score=-1.0,
                    published_date=pub_date,
                    original_language="zh",
                    source='FreeBuf',
                    url=link,
                    affected_products=[]
                )
                vulns.append(vuln)
                print(vuln, "\n")
            except Exception as e:
                print(f"[FreeBuf] Parse error: {e}")
                continue

        print(f"[FreeBuf] Scraped {len(vulns)} fresh vulnerabilities.")
        return vulns
    def fetch_article_content_an(self, url):
            if not url.startswith("http"):
                url = "https://" + url
            r = requests.get(url)
            if r.status_code == 404:
                print(f"Skipping 404 URL: {url}")
                return "404"
            soup = BeautifulSoup(r.text, "html.parser")
            # content_div = soup.find("div", class_="entry-content")
            content_div = soup.find("div", id="js-article")
            if content_div:
                paragraphs = content_div.stripped_strings
                return "\n".join(paragraphs)
            else:
                print("No div.entry-content found!")
            return ""
    def scrape_anquanke(self):
        API_URL = "https://api.anquanke.com/data/v1/posts"
        TAG = "漏洞"
        pages = 1
        articles = []

        for page in range(1, pages + 1):
            params = {
                "page": page,
                "size": 1,
                "tag": TAG
            }
            r = requests.get(API_URL, params=params)
            data = r.json()
            for post in data['data']:
                # Build original Chinese article URL using post id
                original_url = f"https://www.anquanke.com/post/id/{post['id']}"
                articles.append({
                    "title": post['title'],
                    "url": original_url,
                    "date": post['date']
                })

        print(f"Grabbed {len(articles)} articles")

        for art in articles:
            print(f"Fetching: {art['title']} ({art['url']})")
            content = self.fetch_article_content_an(art['url'])
            print(f"Content preview:\n{content[:300]}...\n") 

if __name__ == "__main__":
    scraper = ChineseScraper()
    vulns = scraper.scrape_anquanke()
    # for v in vulns:
    #     print(v)