import requests
from bs4 import BeautifulSoup
from db import is_article_scraped
from models import Article
from datetime import datetime
from dateutil import parser


class RussianScraper():
    def __init__(self):
        self.max_arts = 8
        self.FORCE = True
    
    def normalize_date(self, date_str):
        month_map = {
        "Января": "January",
        "Февраля": "February",
        "Марта": "March",
        "Апреля": "April",
        "Мая": "May",
        "Июня": "June",
        "Июля": "July",
        "Августа": "August",
        "Сентября": "September",
        "Октября": "October",
        "Ноября": "November",
        "Декабря": "December"
        }

        for ru, en in month_map.items():
            if ru in date_str:
                date_str = date_str.replace(ru, en)
                break

        try:
            return parser.parse(date_str).date()
        except Exception as e:
            print(f"Date parse failed: {date_str}, Error: {e}")
            return None
     
    def scrape_anti_malware_news(self):

        max_pages = 1
        
        BASE_URL = "https://www.anti-malware.ru"
        headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        all_articles = []

        for page in range(1,max_pages+1):
            print("PAGE ",page)
            LISTING_URL = f"{BASE_URL}/news?page={page}"
            response = requests.get(LISTING_URL, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []

            articles = soup.select("div.node-news")

            for article in articles[:self.max_arts]:
                a_tag = article.find("h2").find("a")
                title = a_tag.text.strip()
                article_url = BASE_URL + a_tag["href"]
                

                if is_article_scraped(article_url) and not self.FORCE:
                    print(f"Skipping already-scraped: {article_url}")
                    continue

                article_res = requests.get(article_url, headers=headers)
                article_res.raise_for_status()
                article_soup = BeautifulSoup(article_res.text, 'html.parser')

                date_div = article_soup.find("div", class_="submitted")
                if date_div:
                    if date_div.a:
                        date_div.a.decompose()

                    full_text = date_div.get_text(strip=True)
                    date = full_text.split(" - ")[0]
                    
                content_div = article_soup.find("div", class_="txt-wrap")
                if not content_div:
                    print("no content")
                    return ""
                
                paragraphs = content_div.find_all(["p", "blockquote"])
                full_text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
                print("title: ", title)


                article = Article(
                    id= article_url,
                    source= "Anti-Malware",
                    title= title,
                    title_translated="",
                    url= article_url,
                    content= full_text,
                    content_translated="",
                    language= "ru",
                    scraped_at= datetime.now().isoformat(),
                    published_date=self.normalize_date(date)
                )
                all_articles.append(article)

        print("Success:", len(all_articles), "articles collected")
        return all_articles
    
    def scrape_all(self):
        anti = self.scrape_anti_malware_news()
        return anti




if __name__ == "__main__":
    scraper = RussianScraper()
    articles = scraper.scrape_all()
    for art in articles:
        print(f"ID: {art.id}")
        print(f"Source: {art.source}")
        print(f"Title: {art.title}")
        print(f"Link: {art.url}")
        print(f"Language: {art.language}")
        print(f"Scraped at: {art.scraped_at}")
        print(f"Content preview:\n{art.content[:300]}") 
        print(f"date: {art.published_date}"  ) # first 300 chars
        print("-" * 40)