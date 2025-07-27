# from langchain.tools import tool
# from scrapers.chinese_scrape import ChineseScraper
# from scrapers.english_scrape import EnglishScraper
# from scrapers.russian_scrape import RussianScraper
# from pipeline import translate_articles, classify_articles, save_to_json
# from db import insert_raw_article, insert_cve, insert_newsitem, mark_as_processed, get_unprocessed_articles
# from models import Article
# import datetime

# @tool
# def scrape_articles(language: str = "ru", num_articles: int = 2) -> list:
#     # """Scrape CVE articles in Chinese, English, or Russian."""
#     # if language == "zh":
#     #     scraper = ChineseScraper(limit)
#     # elif language == "en":
#     #     scraper = EnglishScraper(limit)
#     # else:
#     #     scraper = RussianScraper(limit)
#     # return scraper.scrape_all()
#     articles = []
#     c_scraper = ChineseScraper(num_articles)
#     articles += c_scraper.scrape_all()

#     r_scraper = RussianScraper()
#     articles+= r_scraper.scrape_all()

#     e_scraper = EnglishScraper(num_articles)
#     articles+= e_scraper.scrape_all()

# @tool
# def translate(articles: list) -> list:
#     """Translate non-English articles to English using Argos Translate."""
#     return translate_articles(articles)

# @tool
# def classify(articles: list) -> dict:
#     """Classify articles as CVE or News and extract relevant fields."""
#     return classify_articles(articles)

# @tool
# def store_articles(articles: list, classified: dict) -> str:
#     """Save articles, CVEs, and news items to DB and JSON."""
#     for art in articles:
#         insert_raw_article(art)

#     for cve in classified[0]:
#         insert_cve(cve)
#         mark_as_processed(cve.url)

#     for news in classified[1]:
#         insert_newsitem(news)
#         mark_as_processed(news.url)

#     save_to_json(classified[0], "cves.json")
#     save_to_json(classified[1], "newsitems.json")
#     return "All articles processed and stored successfully."

# @tool
# def load_unprocessed_articles() -> list:
#     """Load articles that were previously scraped but not processed."""
#     from pipeline import row_to_article
#     rows = get_unprocessed_articles()
#     return [row_to_article(row) for row in rows]
