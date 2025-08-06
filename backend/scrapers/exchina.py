import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dataclasses import dataclass
from typing import List
from transformers import pipeline
import torch

@dataclass
class Vulnerability:
    cve_id: str
    title: str
    description: str
    source: str
    published_date: datetime
    url: str

@dataclass
class SecurityNewsItem:
    title: str
    description: str
    source: str
    published_date: datetime
    url: str

class ChineseScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'VulnIntel-Research-Bot/1.0'
        })

        # LLM zero-shot filter (local HF model)
        self.classifier = pipeline(
    "zero-shot-classification", 
    model="facebook/bart-large-mnli",
    device=0  # use GPU (MPS) if available; use -1 for CPU
)

    def scrape_freebuf(self, limit=10) -> List[dict]:
        """Scrape FreeBuf homepage vulns/news links"""
        url = 'https://www.freebuf.com/vuls'
        r = self.session.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')

        articles = []
        for a in soup.select('.news-info a'):
            href = a.get('href')
            if href:
                full_url = href if href.startswith('http') else f"https://www.freebuf.com{href}"
                articles.append(full_url)

        return articles[:10]

    def scrape_anquanke(self, limit=10) -> List[str]:
        """Scrape Anquanke 漏洞 tag page to get article URLs"""
        url = 'https://www.anquanke.com/tag/%E6%BC%8F%E6%B4%9E'
        r = self.session.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')

        articles = []
        for a in soup.select('.article-item a'):
            href = a.get('href')
            if href:
                full_url = href if href.startswith('http') else f"https://www.anquanke.com{href}"
                articles.append(full_url)

        return articles[:limit]


    def fetch_article(self, url: str) -> dict:
        """Fetch article details"""
        r = self.session.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')

        title = soup.find('h1').text.strip() if soup.find('h1') else ''
        content = ' '.join([t.strip() for t in soup.select_one('.article-content').stripped_strings]) if soup.select_one('.article-content') else ''

        pub_date = datetime.now()
        date_text = soup.select_one('.article-info span')
        if date_text:
            try:
                pub_date = datetime.strptime(date_text.text.strip()[:10], '%Y-%m-%d')
            except:
                pass

        return {
            'title': title,
            'content': content,
            'published_date': pub_date,
            'url': url
        }

    def classify_article(self, text: str) -> str:
        """Use LLM zero-shot to classify as vuln or news"""
        result = self.classifier(
            text,
            candidate_labels=["confirmed vulnerability", "general security news"]
        )
        return result['labels'][0]
    def fetch_article(self, url: str) -> dict:
        print("fetching article ", url)
        r = self.session.get(url)
        soup = BeautifulSoup(r.content, 'html.parser')

        title = soup.find('h1').text.strip() if soup.find('h1') else ''

        # Try FreeBuf selector first
        content_elem = soup.select_one('.article-content')

        # If not found, try Anquanke selector (article body may be under different class)
        if not content_elem:
            content_elem = soup.select_one('.post-content')  # Anquanke uses .post-content

        content = ' '.join([t.strip() for t in content_elem.stripped_strings]) if content_elem else ''

        pub_date = datetime.now()
        date_text = soup.select_one('.article-info span') or soup.select_one('.post-meta time')
        if date_text:
            try:
                pub_date_str = date_text.text.strip()[:10]
                pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
            except:
                pass
        print("found this: ", title, " content ", content)
        return {
            'title': title,
            'content': content,
            'published_date': pub_date,
            'url': url
         }

    def scrape_all(self) -> (List[Vulnerability], List[SecurityNewsItem]):
        """Scrape both sites, classify, and return separate lists"""
        all_links = []

        print("[+] Collecting FreeBuf links...")
        all_links.extend(self.scrape_freebuf())

        print("[+] Collecting Anquanke links...")
        all_links.extend(self.scrape_anquanke())

        vulnerabilities = []
        news_items = []

        for link in all_links:
            print(f"[+] Fetching {link}")
            article = self.fetch_article(link)  # <-- this fetches full description/content
            
            text_for_llm = article['title'] + " " + article['content']  # use full content for classification

            label = self.classify_article(text_for_llm)
            print(f"    => Classified as: {label}")

            if label == "confirmed vulnerability":
                vuln = Vulnerability(
                    cve_id=f"CN-{hash(link) % 100000}",
                    title=article['title'],
                    description=article['content'][:200],  # truncated detailed description
                    source="FreeBuf or Anquanke",
                    published_date=article['published_date'],
                    url=article['url']
                )
                print(vuln)
                vulnerabilities.append(vuln)
            else:
                news = SecurityNewsItem(
                    title=article['title'],
                    description=article['content'][:200],  # truncated detailed description
                    source="FreeBuf or Anquanke",
                    published_date=article['published_date'],
                    url=article['url']
                )
                print(news)
                news_items.append(news)


        return vulnerabilities, news_items

if __name__ == "__main__":
    scraper = ChineseScraper()
    vulns, news = scraper.scrape_all()
    print(f"Found {len(vulns)} confirmed vulnerabilities")
    print(f"Found {len(news)} security news items")
