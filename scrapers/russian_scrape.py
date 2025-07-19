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
        print(response)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        print(response.text)
        all_articles = []

        articles = soup.select("div.news-list-item")

        for article in articles:
            link_tag = article.find("a")
            if not link_tag:
                continue

            title = link_tag.text.strip()
            relative_url = link_tag["href"]
            full_url = self.base_url + relative_url

            all_articles.append({
                "title": title,
                "url": full_url
            })

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