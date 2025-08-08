from langchain.tools import tool
from typing import List
from models import QueryParams
from datetime import datetime, timedelta
import json
import argostranslate.package
import argostranslate.translate

from typing import Dict, List, Optional

# Import your existing functions
from scrapers.chinese_scrape import ChineseScraper
from scrapers.english_scrape import EnglishScraper
from scrapers.russian_scrape import RussianScraper
from classify import classify_article
from models import Article, Vulnerability, NewsItem
from db import (
    init_db,
    insert_raw_article,
    is_article_scraped,
    mark_as_processed,
    get_unprocessed_articles,
    insert_cve,
    insert_newsitem,
    get_cves_by_filters, get_news_by_filters, get_last_scrape_time, get_data_statistics
)
# Your existing translation functions
def translate_articles(articles):
    """Reuse your existing translation logic"""
    for i, art in enumerate(articles):
        print(f"Translating article {i+1}/{len(articles)} title")
        art.title_translated = translate(art.title, art.language)
        print(f"Translating article {i+1}/{len(articles)} content")
        art.content_translated = translate(art.content, art.language)
    return articles

def translate(text: str, source_lang, target_lang="en") -> str:
    """Your existing translate function"""
    if source_lang == "en":
        print("Source language is English, skipping translation.")
        return text
    # Use your existing chunk_text and translate_argos functions
    chunks = chunk_text(text, max_length=5000)
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"Translating chunk {i+1}/{len(chunks)} (length {len(chunk)})")
        translated = translate_argos(chunk, source_lang)
        translated_chunks.append(translated)
    return "\n".join(translated_chunks)

def chunk_text(text, max_length=5000):
    """Your existing chunk_text function"""
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
    """Your existing argos translate function"""
    return argostranslate.translate.translate(text, source_lang, target_lang)

def truncate_text(text, max_length=3000):
    """Your existing truncate function"""
    return text[:max_length]
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

@tool
def scrape_and_process_articles(params: QueryParams) -> List[Article]:
    """Scrape fresh articles from all sources and prepare them for classification"""
    print(f"🔍 Scraping articles for query: {params.content_type}, {params.max_results} results, {params.days_back} days back")
    
    articles = []
    # Use more articles than requested to account for filtering
    num_articles = max(params.max_results * 2, 10)
    
    # Reuse your existing scrapers
    c_scraper = ChineseScraper(num_articles // 3)
    articles += c_scraper.scrape_all()

    r_scraper = RussianScraper()
    articles += r_scraper.scrape_all()

    e_scraper = EnglishScraper(num_articles // 3)
    articles += e_scraper.scrape_all()

    print(f"Scraped {len(articles)} articles")

    unprocessed_rows = get_unprocessed_articles()
    if unprocessed_rows:
        print("processing " ,len(unprocessed_rows), " unprocessed rows")
    leftover_articles = [row_to_article(row) for row in unprocessed_rows]

    articles+= leftover_articles
    
    # Truncate content and translate using your existing functions
    for art in articles:
        art.content = truncate_text(art.content, max_length=3000)
    
    translated_articles = translate_articles(articles)
    print(f"Translated {len(translated_articles)} articles")

    
    return translated_articles
def save_to_json(items: list, filename: str) -> None:
    def convert(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    with open(filename, "w", encoding="utf-8") as f:
        json.dump([vars(item) for item in items], f, ensure_ascii=False, indent=2, default=convert)

@tool
def classify_articles(articles: List[Article], params: QueryParams) -> tuple[List[Vulnerability], List[NewsItem]]:
    """Classify articles using your existing classify_article function"""
    print(f"🤖 Classifying {len(articles)} articles...")
    
    cves = []
    news = []

    for art in articles:
        # Reuse your existing classify_article function
        print("Processing URL:", art.url)

        results = classify_article(art.content_translated)
        for result in results:
            if result["type"] == "CVE":
                vul = Vulnerability(
                    cve_id=result["cve_id"][0] if result["cve_id"] else "Unknown",
                    title=art.title,
                    title_translated=art.title_translated,
                    summary=result["summary"],
                    severity=result["severity"],
                    cvss_score=float(result["cvss_score"]) if result["cvss_score"] is not None else 0.0,
                    published_date=art.scraped_at,
                    original_language=art.language,
                    source=art.source,
                    url=art.url,
                    intrigue = float(result["intrigue"]) if result["intrigue"] is not None else 0.0,
                    affected_products=result["affected_products"], 
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
                    intrigue = float(result["intrigue"]) if result["intrigue"] is not None else 0.0,
                    url=art.url,
                )
                news.append(news_item)
    for cve in cves:
        print("Inserted CVE ", cve.title_translated)
        insert_cve(cve)
        mark_as_processed(cve.url)

    for newsitem in news:
        print("Inserted News ", newsitem.title_translated)
        insert_newsitem(newsitem)
        mark_as_processed(newsitem.url)
    
    save_to_json(cves, "cves.json")
    save_to_json(news, "newsitems.json")
    print(f"✅ Classified into {len(cves)} CVEs and {len(news)} news items")
    return cves, news

# @tool
# def filter_and_rank_items(cves: List[Vulnerability], news_items: List[NewsItem], params: QueryParams) -> List:
#     """Filter items by user criteria and rank them"""
#     print(f"🔧 Filtering and ranking items...")
    
#     all_items = []
    
#     # Filter by content type
#     if params.content_type in ["cve", "both"]:
#         filtered_cves = cves
#         # Apply severity filter if specified
#         if params.severity:
#             filtered_cves = [cve for cve in cves if cve.severity == params.severity]
#         all_items.extend(filtered_cves)
    
#     if params.content_type in ["news", "both"]:
#         all_items.extend(news_items)
    
#     # Apply date filter
#     cutoff_date = datetime.now() - timedelta(days=params.days_back)
#     date_filtered = []
#     for item in all_items:
#         published = item.published_date
#         if isinstance(published, str):
#             try:
#                 published = datetime.fromisoformat(published)
#             except ValueError:
#                 continue  
#         if published and published >= cutoff_date:
#             date_filtered.append(item)
    
#     # Simple ranking by CVSS score for CVEs, recency for news
#     def rank_item(item):
#         if hasattr(item, 'cvss_score') and item.cvss_score:
#             return item.cvss_score
#         return 1.0  # Default score for news items
    
#     ranked_items = sorted(date_filtered, key=rank_item, reverse=True)
    
#     # Limit results
#     final_items = ranked_items[:params.max_results]
    
#     print(f"✅ Filtered to {len(final_items)} final items")
#     return final_items
@tool
def filter_and_rank_items(cves: List[Vulnerability], news_items: List[NewsItem], params: QueryParams) -> List:
    """Filter items by user criteria and rank them"""
    print(f"\n🔧 Starting filter_and_rank_items()")
    print(f"📥 Received {len(cves)} CVEs and {len(news_items)} news items")
    print(f"🧾 Parameters: content_type={params.content_type}, severity={params.severity}, days_back={params.days_back}, max_results={params.max_results}")

    cutoff_date = datetime.now() - timedelta(days=params.days_back)

    # 🧪 Filter CVEs
    filtered_cves = []
    
    for cve in cves:
        
        if params.severity:
            allowed = [s.upper() for s in params.severity]
            print("Allowed Severities: ",allowed)
            if cve.severity.upper() not in allowed:
                continue
        if isinstance(cve.published_date, str):
            cve.published_date = datetime.fromisoformat(cve.published_date)
        if cve.published_date >= cutoff_date:
            filtered_cves.append(cve)
    print(f"🔍 Filtered CVEs count: {len(filtered_cves)}")
    ranked_cves = sorted(
    cves,
    key=lambda c: (c.cvss_score * 0.6 + c.intrigue * 0.4),
    reverse=True
)
    

    # 🧪 Filter News
    filtered_news = []
    for news in news_items:
        if isinstance(news.published_date, str):
            news.published_date = datetime.fromisoformat(news.published_date)
        if news.published_date >= cutoff_date:
            filtered_news.append(news)
    print(f"🔍 Filtered News  count: {len(filtered_news)}")
    ranked_news = sorted(news_items, key=lambda n: n.intrigue, reverse=True)


    print(f"✅ Filtered {len(ranked_cves)} CVEs and {len(ranked_news)} News items")
    
    return {
        "cves": ranked_cves[:params.max_results],
        "news": ranked_news[:params.max_results],
    }

@tool  
def format_and_present_results(results: dict, params: QueryParams) -> str:
    """Format CVEs and News separately"""
    cves = results.get("cves", [])
    news = results.get("news", [])

    output = f"🔒 **Cybersecurity Report**\n"
    output += f"📅 Past {params.days_back} day(s)\n"
    if params.severity:
        output += f"⚠️ Severity filter: {', '.join(params.severity)}\n"
    output += "\n" + "="*60 + "\n"

    # 🔹 CVEs Section
    output += f"\n🚨 **Vulnerabilities ({len(cves)})**\n\n"
    for i, cve in enumerate(cves, 1):
        output += f"**{i}. {cve.title_translated}**\n"
        output += f"🔗 URL: {cve.url}\n"
        output += f"🧾 CVE: {cve.cve_id} | Severity: {cve.severity} | CVSS: {cve.cvss_score}\n"
        output += f"📝 {cve.summary}\n"
        output += f"📅 {cve.published_date.strftime('%Y-%m-%d')}\n"
        output += f"🌐 Source: {cve.source} ({cve.original_language})\n"
   
        output += "-"*40 + "\n"

    # 🔸 News Section
    output += f"\n📰 **News Items ({len(news)})**\n\n"
    for i, item in enumerate(news, 1):
        output += f"**{i}. {item.title_translated}**\n"
        output += f"🔗 URL: {item.url}\n"
        output += f"📝 {item.summary}\n"
        output += f"📅 {item.published_date.strftime('%Y-%m-%d')}\n"
        output += f"🌐 Source: {item.source} ({item.original_language})\n"
        output += "-"*40 + "\n"

    if params.output_format == "email" and params.email_address:
        output += f"\n📧 Would send to: {params.email_address}\n"

    return output


# @tool  
# def format_and_present_results(items: List, params: QueryParams) -> str:
#     """Format results for display or email"""
#     print(f"📋 Formatting {len(items)} items for {params.output_format}")
    
#     if not items:
#         return "No items found matching your criteria."
    
#     # Generate formatted output
#     output = f"🔒 **Cybersecurity Report** - {len(items)} item(s)\n"
#     output += f"📅 From the last {params.days_back} day(s)\n"
#     output += f"🎯 Type: {params.content_type.upper()}\n"
#     if params.severity:
#         output += f"⚡ Severity: {params.severity.upper()}\n"
#     output += "\n" + "="*60 + "\n\n"
    
#     for i, item in enumerate(items, 1):
#         output += f"**{i}. {item.title_translated}**\n"
        
#         # Check if it's a CVE (has cve_id attribute)
#         if hasattr(item, 'cve_id'):
#             output += f"🚨 **CVE**: {item.cve_id or 'TBD'} | "
#             output += f"**Severity**: {item.severity or 'Unknown'}"
#             if item.cvss_score:
#                 output += f" | **CVSS**: {item.cvss_score}"
#             output += "\n"
#         if isinstance(item.published_date, str):
#             item.published_date = datetime.fromisoformat(item.published_date)
        
#         output += f"📝 **Summary**: {item.summary}\n"
#         output += f"🌐 **Source**: {item.source} ({item.original_language})\n"
#         output += f"🔗 **URL**: {item.url}\n"
#         output += f"📅 **Date**: {item.published_date.strftime('%Y-%m-%d %H:%M')}\n"
#         output += "\n" + "-"*40 + "\n\n"
    
#     # Handle email delivery
#     if params.output_format == "email" and params.email_address:
#         # TODO: Implement email sending using your SMTP config
#         output += f"\n📧 (Email would be sent to {params.email_address})"
    
#     return output


@tool
def check_data_sufficiency(params: QueryParams) -> Dict:
    """Agent checks if existing data is sufficient for the query"""
    print(f"🔍 Agent checking data sufficiency for query...")
    
    cutoff_date = datetime.now() - timedelta(days=params.days_back)
    
    # Check existing CVEs
    existing_cves = get_cves_by_filters(
        severity_filter=params.severity,
        after_date=cutoff_date,
        limit=params.max_results * 2  # Check for more than needed
    )
    
    # Check existing news
    existing_news = get_news_by_filters(
        after_date=cutoff_date,
        limit=params.max_results * 2
    )
    
    # Get last scrape times by source
    last_scrapes = get_last_scrape_time()
    
    # Calculate data freshness score
    def calculate_freshness(last_scrape):
        if not last_scrape:
            return 0.0
        hours_ago = (datetime.now() - last_scrape).total_seconds() / 3600
        return max(0, 1 - (hours_ago / 24))  # Linear decay over 24 hours
    
    analysis = {
        "sufficient_data": False,
        "existing_cves": len(existing_cves),
        "existing_news": len(existing_news),
        "data_freshness": {
            "chinese": calculate_freshness(last_scrapes.get("chinese")),
            "russian": calculate_freshness(last_scrapes.get("russian")), 
            "english": calculate_freshness(last_scrapes.get("english"))
        },
        "recommendation": "scrape_all",
        "reasoning": ""
    }
    
    # Decision logic
    total_existing = len(existing_cves) + len(existing_news)
    avg_freshness = sum(analysis["data_freshness"].values()) / 3
    
    if total_existing >= params.max_results and avg_freshness > 0.7:
        analysis["sufficient_data"] = True
        analysis["recommendation"] = "use_existing"
        analysis["reasoning"] = f"Found {total_existing} recent items with {avg_freshness:.1%} avg freshness"
    elif total_existing >= params.max_results // 2 and avg_freshness > 0.4:
        analysis["recommendation"] = "targeted_scrape"
        analysis["reasoning"] = f"Partial data ({total_existing} items) but moderate freshness"
    else:
        analysis["recommendation"] = "full_scrape"
        analysis["reasoning"] = f"Insufficient data ({total_existing} items) or stale ({avg_freshness:.1%} freshness)"
    
    print(f"📊 Data Analysis: {analysis['recommendation']} - {analysis['reasoning']}")
    return analysis

@tool
def get_existing_data(params: QueryParams) -> Dict:
    """Retrieve existing data from database without scraping"""
    print(f"🗄️ Agent retrieving existing data from database...")
    
    cutoff_date = datetime.now() - timedelta(days=params.days_back)
    
    # Get filtered data from database
    if params.content_type in ["cve", "both"]:
        cves = get_cves_by_filters(
            severity_filter=params.severity,
            after_date=cutoff_date,
            limit=params.max_results
        )
    else:
        cves = []
    
    if params.content_type in ["news", "both"]:
        news = get_news_by_filters(
            after_date=cutoff_date,
            limit=params.max_results
        )
    else:
        news = []
    
    # Sort by intrigue/relevance
    cves.sort(key=lambda x: (x.cvss_score * 0.6 + x.intrigue * 0.4), reverse=True)
    news.sort(key=lambda x: x.intrigue, reverse=True)
    
    return {
        "cves": cves[:params.max_results],
        "news": news[:params.max_results],
        "source": "database"
    }

@tool
def targeted_scrape(params: QueryParams, sources_to_scrape: List[str]) -> List[Article]:
    """Agent performs targeted scraping of specific sources"""
    print(f"🎯 Agent performing targeted scrape of: {sources_to_scrape}")
    
    articles = []
    num_articles = max(params.max_results, 5)
    
    if "chinese" in sources_to_scrape:
        c_scraper = ChineseScraper(num_articles)
        articles += c_scraper.scrape_all()
        
    if "russian" in sources_to_scrape:
        r_scraper = RussianScraper()
        articles += r_scraper.scrape_all()
        
    if "english" in sources_to_scrape:
        e_scraper = EnglishScraper(num_articles)
        articles += e_scraper.scrape_all()
    
    # Process articles
    for art in articles:
        art.content = truncate_text(art.content, max_length=3000)
    
    translated_articles = translate_articles(articles)
    print(f"🎯 Targeted scrape complete: {len(translated_articles)} articles")
    
    return translated_articles