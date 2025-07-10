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
    def fetch_article_content(self, url):
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
        # url = 'https://www.anquanke.com/tag/%E6%BC%8F%E6%B4%9E'
        # response = requests.get(url)
        # soup = BeautifulSoup(response.content, 'html.parser')
        # post_list = soup.find('div', id='post-list')
        # article_items = post_list.find_all('div', class_='article-item')
        # links = []

        # for item in article_items:
        #     a_tag = item.find('a')
        #     if a_tag and a_tag.get('href'):
        #         link = a_tag['href']
        #         if not link.startswith('http'):
        #             link = f"https://www.anquanke.com{link}"
        #         links.append(link)

        # print(links)
        API_URL = "https://api.anquanke.com/data/v1/posts"
        TAG = "漏洞"
        pages = 1
        articles = []

        for page in range(1, pages + 1):
            params = {
                "page": page,
                "size": 10,
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
            content = self.fetch_article_content(art['url'])
            print(f"Content preview:\n{content[:300]}...\n")  # show 300 chars preview


        # for page in range(1, pages + 1):
        #     params = {
        #         "page": page,
        #         "size": 10,
        #         "tag": TAG
        #     }
        #     r = requests.get(API_URL, params=params)
        #     data = r.json()
        #     for post in data['data']:
        #         url = post['url']
        #         if "anquanke.com" not in url:
        #             # Try to find the original anquanke URL or skip / handle differently
        #             print(f"Skipping non-Chinese original: {url}")
        #             continue
        #         articles.append({
        #             "title": post['title'],
        #             "url": post['url'],
        #             "date": post['date']
        #         })
        # print("Grabbed ", len(articles), " articles")
        
        # for art in articles:
        #     print(f"Fetching: {art['title']} ({art['url']})")
        #     content = self.fetch_article_content(art['url'])
        #     print(f"Content preview: {content[:100]}...\n")
    

if __name__ == "__main__":
    scraper = ChineseScraper()
    vulns = scraper.scrape_anquanke()
    # for v in vulns:
    #     print(v)


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



