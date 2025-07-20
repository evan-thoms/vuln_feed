from scrapers.chinese_scrape import ChineseScraper
from scrapers.english_scrape import EnglishScraper
from scrapers.russian_scrape import RussianScraper
from deep_translator import GoogleTranslator
from models import NewsItem, Vulnerability

from agent import classify_article
import json
import argostranslate.package
import argostranslate.translate
from models import Article
import datetime
from db import (
    init_db,
    insert_raw_article,
    is_article_scraped,
    mark_as_processed,
    get_unprocessed_articles,
    insert_cve,
    insert_newsitem,
)

def truncate_text(text, max_length=3000):
    return text[:max_length]

def setup_argos():
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    
    zh_en_package = next(
        filter(lambda x: x.from_code == "zh" and x.to_code == "en", available_packages)
    )
    argostranslate.package.install_from_path(zh_en_package.download())
    
    ru_en_package = next(
        filter(lambda x: x.from_code == "ru" and x.to_code == "en", available_packages)
    )
    argostranslate.package.install_from_path(ru_en_package.download())

def translate_articles(articles):
    for i, art in enumerate(articles):
        print(f"Translating article {i+1}/{len(articles)} title")
        art.title_translated = translate(art.title, art.language)
        print(f"Translating article {i+1}/{len(articles)} content")
        art.content_translated = translate(art.content, art.language)
    return articles

def chunk_text(text, max_length=5000):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_length, len(text))
        chunk = text[start:end]
        last_newline = chunk.rfind('\n')
        last_space = chunk.rfind(' ')
        break_pos = max(last_newline, last_space)
        if break_pos > 0 and end < len(text):
            end = start + break_pos
        chunks.append(text[start:end])
        start = end
    return chunks


def translate_argos(text: str, source_lang: str, target_lang: str = "en") -> str:
    return argostranslate.translate.translate(text, source_lang, target_lang)

def translate(text: str, source_lang, target_lang="en") -> str:
    if source_lang == "en":
        print("Source language is English, skipping translation.")
        return text
    chunks = chunk_text(text, max_length=5000)
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"Translating chunk {i+1}/{len(chunks)} (length {len(chunk)})")
        translated = translate_argos(chunk, source_lang)
        translated_chunks.append(translated)
    return "\n".join(translated_chunks)
    

def classify_articles(articles):
    cves = []
    news = []

    for art in articles:
        result = classify_article(art.content_translated)
        print("URL: ",art.url)
        # print(f"Agent result: {result}")

        if result["type"] == "CVE":
            vul = Vulnerability(
                cve_id=result["cve_id"][0] if result["cve_id"] else "Unknown",
                title=art.title,
                title_translated=art.title_translated,
                summary=result["summary"],
                severity=result["severity"],
                cvss_score=float(result["cvss_score"]) if result["cvss_score"] else 0.0,
                published_date=art.scraped_at,
                original_language=art.language,
                source=art.source,
                url=art.url,
                affected_products=[], 
            )
            cves.append(vul)
        else:
            news_item = NewsItem(
                title=art.title,
                title_translated=art.title_translated,
                summary=result["summary"],
                published_date=art.scraped_at,
                original_language=art.language,
                source=art.source,
                url=art.url,
            )
            news.append(news_item)

    return cves, news

def save_to_json(items, path):
    with open(path, "w") as f:
        json.dump([vars(item) for item in items], f, ensure_ascii=False, indent=2)

def main():
    init_db()
    setup_argos()

    articles = []
    # num_articles = 2
    # c_scraper = ChineseScraper(num_articles)
    # articles += c_scraper.scrape_all()

    r_scraper = RussianScraper()
    articles+= r_scraper.scrape_all()

    # e_scraper = EnglishScraper(num_articles)
    # articles+= e_scraper.scrape_all()

    print(f"Scraped {len(articles)} articles")
    unprocessed_rows = get_unprocessed_articles()
    if unprocessed_rows:
        print("processing " ,len(unprocessed_rows), " unprocessed rows")
    leftover_articles = [row_to_article(row) for row in unprocessed_rows]

    articles+= leftover_articles
    for art in articles:
        art.content = truncate_text(art.content, max_length=3000)
    print(f"Collected  {len(articles)} articles")

    translated_articles = translate_articles(articles)
    
    print(f"Translated {len(translated_articles)} articles")

    for art in translated_articles:
        print("Inserted Article ", art.title_translated)
        insert_raw_article(art)

    cves, newsitems = classify_articles(translated_articles)
 
    for cve in cves:
        print("Inserted CVE ", cve.title_translated)
        insert_cve(cve)
        mark_as_processed(cve.url)

    for newsitem in newsitems:
        print("Inserted News ", newsitem.title_translated)
        insert_newsitem(newsitem)
        mark_as_processed(newsitem.url)
    
    save_to_json(cves, "cves.json")
    save_to_json(newsitems, "newsitems.json")
        
def row_to_article(row):
    return Article(
        id=row[0],
        source=row[1],
        title=row[2],
        title_translated=row[3],
        url=row[4],
        content=row[5],
        content_translated=row[6],
        language=row[7],
        scraped_at=row[8],
        published_date=row[9]
    )

def test_classify():
    pass
if __name__ == "__main__":
    # result = classify_article(cool)
    # print(f"Agent result: {result}")
    main()