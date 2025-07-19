import requests
from bs4 import BeautifulSoup



class RussianScraper():
    

    def scrape_anti_malware_news(self,page=1):
        url = f"https://www.anti-malware.ru/news?page={page}"
        headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        max_pages = 3
        

        BASE_URL = "https://www.anti-malware.ru"

        for page in range(1,max_pages+1):
            print("PAGE ",page)
            LISTING_URL = f"{BASE_URL}/news?page={page}"

            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            all_articles = []

            articles = soup.select("div.node-news")

            for article in articles:
                a_tag = article.find("h2").find("a")
                title = a_tag.text.strip()
                url = BASE_URL + a_tag["href"]
  
                # Summary (first paragraph)
                summary_tag = article.select_one("div.content p")
                summary = summary_tag.text.strip() if summary_tag else ""

                print(f"Title: {title}")
                print(f"URL: {url}")
                print(f"Summary: {summary}")
                print("-" * 80)
        print("Success: ", all_articles)
        return all_articles



if __name__ == "__main__":
    scraper = RussianScraper()
    articles = scraper.scrape_anti_malware_news()
    print(articles)
    # for art in articles:
    #     print(f"ID: {art.id}")
    #     print(f"Source: {art.source}")
    #     print(f"Title: {art.title}")
    #     print(f"Link: {art.url}")
    #     print(f"Language: {art.language}")
    #     print(f"Scraped at: {art.scraped_at}")
    #     print(f"Content preview:\n{art.content[:300]}") 
    #     print(f"date: {art.published_date}"  ) # first 300 chars
    #     print("-" * 40)