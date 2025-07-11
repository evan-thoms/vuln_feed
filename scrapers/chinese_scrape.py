import feedparser
from datetime import datetime
from models import Article
import requests
from bs4 import BeautifulSoup
import time

class ChineseScraper:
    def scrape_freebuf(self, days_back: int = 7):
        print("[FreeBuf] Starting RSS scrape...")
        feed_url = "https://www.freebuf.com/feed"
        feed = feedparser.parse(feed_url)
        print(f"Found {len(feed.entries)} articles in the RSS feed.")

        articles = []

        for entry in feed.entries[:3]:
            article_url = entry.link
            print(f"\nFetching: {article_url}")
            
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get(article_url, headers=headers)
                res.raise_for_status()
                
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

                print("Title:", entry.title)
                print("PubDate:", entry.published)
                print("Link:", article_url)
                print("First 300 chars:", full_text[:300], "...")
                
                article = Article(
                    id= article_url,
                    source= "FreeBuf",
                    title= title,
                    translated_title="",
                    link= article_url,
                    content= full_text,
                    translated_content="",
                    language= "zh",
                    scraped_at= datetime.now()
                )
                articles.append(article)

            except Exception as e:
                print("Error fetching article:", e)
            
            time.sleep(1)   
        print("articles: ", articles[1].title, articles[0].language)
        return articles
               
    def fetch_article_content_an(self, url):
            if not url.startswith("http"):
                url = "https://" + url
            r = requests.get(url)
            if r.status_code == 404:
                print(f"Skipping 404 URL: {url}")
                return "404"
            soup = BeautifulSoup(r.text, "html.parser")
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
        articles_meta = []

        for page in range(1, pages + 1):
            params = {
                "page": page,
                "size": 3,
                "tag": TAG
            }
            r = requests.get(API_URL, params=params)
            data = r.json()
            for post in data['data']:
                original_url = f"https://www.anquanke.com/post/id/{post['id']}"
                articles_meta.append({
                    "title": post['title'],
                    "url": original_url,
                    "date": post['date']
                })

        print(f"Grabbed {len(articles_meta)} articles")
        articles = []
        for article in articles_meta:
            print(f"Fetching: {article['title']} ({article['url']})")
            content = self.fetch_article_content_an(article['url'])
            print(f"Content preview:\n{content[:300]}...\n") 
            article = Article(
                        id= article["url"],
                        source= "FreeBuf",
                        title= article["title"],
                        translated_title="",
                        link= article["url"],
                        content= content,
                        translated_content="",
                        language= "zh",
                        scraped_at= datetime.now()
                    )
            articles.append(article)
        return articles
    def scrape_all(self):
        freeBuf = self.scrape_freebuf()
        anquanke = self.scrape_anquanke()
        print("anquan len, ", len(anquanke), " freebuf len ", len(freeBuf))
        freeBuf.extend(anquanke)
        return freeBuf


if __name__ == "__main__":
    scraper = ChineseScraper()
    articles = scraper.scrape_all()
    for art in articles:
        print(f"ID: {art.id}")
        print(f"Source: {art.source}")
        print(f"Title: {art.title}")
        print(f"Link: {art.link}")
        print(f"Language: {art.language}")
        print(f"Scraped at: {art.scraped_at}")
        print(f"Content preview:\n{art.content[:300]}")  # first 300 chars
        print("-" * 40)