import feedparser
from datetime import datetime, timedelta
from models import Vulnerability
from deep_translator import GoogleTranslator  # or your LangChain helper

class ChineseScraper:
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='en')

    def scrape_freebuf(self, days_back: int = 7):
        print("[FreeBuf] Starting RSS scrape...")
        feed_url = "https://www.freebuf.com/feed"
        feed = feedparser.parse(feed_url)

        vulns = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for entry in feed.entries[:15]:
            try:
                
                title_original_ = entry.title
                title_translated_ = entry.title
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
                    cvss_score=5.0,
                    published_date=pub_date,
                    source='FreeBuf',
                    url=link,
                    affected_products=[]
                )
                vulns.append(vuln)

            except Exception as e:
                print(f"[FreeBuf] Parse error: {e}")
                continue

        print(f"[FreeBuf] Scraped {len(vulns)} fresh vulnerabilities.")
        return vulns

if __name__ == "__main__":
    scraper = ChineseScraper()
    vulns = scraper.scrape_freebuf()
    for v in vulns:
        print(v)


# # scrapers/chinese_scrape.py

# import requests
# from bs4 import BeautifulSoup
# from datetime import datetime, timedelta
# from models import Vulnerability
# #from llm_summarizer import summarize_text  # <- Your LangChain helper

# class ChineseScraper:
#     def __init__(self):
#         self.session = requests.Session()
#         self.session.headers.update({
#             'User-Agent': 'AgenticCyberFeed-Bot/1.0'
#         })

#     def scrape_freebuf(self, days_back: int = 7):
#         print("starting freebuff")
#         """Scrape FreeBuf vulnerability posts"""
#         base_url = "https://www.freebuf.com/vuls"
#         vulns = []

#         try:
#             response = self.session.get(base_url)
#             response.raise_for_status()
#             soup = BeautifulSoup(response.content, 'html.parser')

#             articles = soup.select('.news-info')

#             cutoff_date = datetime.now() - timedelta(days=days_back)

#             for article in articles[:10]:  # Limit for demo
#                 try:
#                     link_elem = article.find('a')
#                     link = link_elem.get('href') if link_elem else None
#                     title = link_elem.get_text(strip=True) if link_elem else "No Title"

#                     # Try to get date from meta if available
#                     pub_date = datetime.now()
#                     time_elem = article.find('time')
#                     if time_elem and time_elem.has_attr('datetime'):
#                         pub_date = datetime.fromisoformat(time_elem['datetime'])
#                     elif time_elem:
#                         pub_date = datetime.strptime(time_elem.text.strip(), '%Y-%m-%d')

#                     if pub_date < cutoff_date:
#                         continue

#                     # Get full article content
#                     article_resp = self.session.get(link)
#                     article_resp.raise_for_status()
#                     article_soup = BeautifulSoup(article_resp.content, 'html.parser')
#                     raw_content = "\n".join(p.get_text(strip=True) for p in article_soup.select('.article-content p'))

#                     # Summarize or translate with LangChain
#                     summary = "testing"
#                     #summary = summarize_text(raw_content, source_language='zh', target_language='en')

#                     vuln = Vulnerability(
#                         cve_id=f"FreeBuf-{hash(title) % 10000}",
#                         title=title,
#                         description=summary,
#                         severity='MEDIUM',
#                         cvss_score=5.0,
#                         published_date=pub_date,
#                         source='FreeBuf',
#                         url=link,
#                         affected_products=[]
#                     )
#                     vulns.append(vuln)

#                 except Exception as e:
#                     print(f"FreeBuf article parse error: {e}")
#                     continue

#         except requests.RequestException as e:
#             print(f"FreeBuf request error: {e}")
#         print("vulns ehre bro", vulns)
#         return vulns



