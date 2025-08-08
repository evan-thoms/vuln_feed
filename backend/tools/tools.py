from langchain.tools import tool
from typing import List, Dict, Optional
from models import QueryParams, Article, Vulnerability, NewsItem
from datetime import datetime, timedelta
import json
import argostranslate.package
import argostranslate.translate

# Import your existing functions
from scrapers.chinese_scrape import ChineseScraper
from scrapers.english_scrape import EnglishScraper
from scrapers.russian_scrape import RussianScraper
from classify import classify_article
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

_current_session = {
    "scraped_articles": [],
    "classified_cves": [],
    "classified_news": [],
    "session_id": None
}

def new_session():
    """Start a new processing session"""
    global _current_session
    _current_session = {
        "scraped_articles": [],
        "classified_cves": [],
        "classified_news": [],
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S")
    }
# Your existing helper functions
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

def truncate_text(text, max_length=2000):
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
        published_date=row[9] if len(row) > 9 else row[8]
    )

def save_to_json(items: list, filename: str) -> None:
    def convert(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    with open(filename, "w", encoding="utf-8") as f:
        json.dump([vars(item) for item in items], f, ensure_ascii=False, indent=2, default=convert)
@tool
def analyze_data_needs(content_type: str = "both", severity: str = None, days_back: int = 7, max_results: int = 10) -> str:
    """Analyze current intelligence database to determine if fresh scraping is needed."""
    print(f"🔍 Analyzing intelligence needs...")
    
    stats = get_data_statistics()
    severity_list = [severity] if severity else None
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    existing_cves = get_cves_by_filters(
        severity_filter=severity_list,
        after_date=cutoff_date,
        limit=max_results * 2
    )
    
    existing_news = get_news_by_filters(
        after_date=cutoff_date,
        limit=max_results * 2
    )
    
    last_scrapes = get_last_scrape_time()
    
    def hours_since_scrape(last_scrape):
        if not last_scrape:
            return 999
        return (datetime.now() - last_scrape).total_seconds() / 3600
    
    avg_age = sum([
        hours_since_scrape(last_scrapes.get("chinese")),
        hours_since_scrape(last_scrapes.get("russian")),
        hours_since_scrape(last_scrapes.get("english"))
    ]) / 3
    
    total_items = len(existing_cves) + len(existing_news)
    
    if total_items >= max_results and avg_age < 12:
        recommendation = "sufficient"
        reasoning = f"Found {total_items} recent items, avg age {avg_age:.1f}h"
    elif total_items >= max_results // 2 and avg_age < 48:
        recommendation = "scrape_needed"
        reasoning = f"Partial data ({total_items} items) but aging ({avg_age:.1f}h old)"
    else:
        recommendation = "urgent_scrape"
        reasoning = f"Critical need: only {total_items} items, {avg_age:.1f}h old"
    
    print(f"📊 Analysis: {recommendation} - {reasoning}")
    
    # Return minimal response to save tokens
    return json.dumps({
        "recommendation": recommendation,
        "reasoning": reasoning,
        "existing_items": total_items,
        "avg_age_hours": round(avg_age, 1)
    })


@tool
def retrieve_existing_data(content_type: str = "both", severity: str = None, days_back: int = 7, max_results: int = 10) -> str:
    """Retrieve existing intelligence from database without scraping."""
    global _current_session
    print(f"🗄️ Retrieving existing intelligence...")
    
    severity_list = [severity] if severity else None
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    cves = []
    news = []
    
    if content_type in ["cve", "both"]:
        cves = get_cves_by_filters(
            severity_filter=severity_list,
            after_date=cutoff_date,
            limit=max_results
        )
    
    if content_type in ["news", "both"]:
        news = get_news_by_filters(
            after_date=cutoff_date,
            limit=max_results
        )
    
    # Store in session, return summary only
    _current_session["classified_cves"] = cves[:max_results]
    _current_session["classified_news"] = news[:max_results]
    
    print(f"✅ Retrieved {len(cves)} CVEs and {len(news)} news items")
    
    return json.dumps({
        "success": True,
        "cves_found": len(cves),
        "news_found": len(news),
        "source": "database_cache"
    })


@tool
def scrape_fresh_intel(content_type: str = "both", max_results: int = 10) -> str:
    """Execute fresh intelligence collection from all sources."""
    global _current_session
    print(f"🌐 Initiating fresh intelligence collection...")
    
    articles = []
    target_per_source = max(max_results // 2, 5)
    
    try:
        # Multi-source scraping
        print("🇨🇳 Scraping Chinese sources...")
        c_scraper = ChineseScraper(target_per_source)
        articles.extend(c_scraper.scrape_all())
        
        print("🇷🇺 Scraping Russian sources...")
        r_scraper = RussianScraper()
        articles.extend(r_scraper.scrape_all())
        
        print("🇺🇸 Scraping English sources...")
        e_scraper = EnglishScraper(target_per_source)
        articles.extend(e_scraper.scrape_all())
        
        # Process unprocessed articles
        unprocessed_rows = get_unprocessed_articles()
        if unprocessed_rows:
            print(f"📥 Processing {len(unprocessed_rows)} backlog articles...")
            for row in unprocessed_rows:
                article = Article(
                    id=row[0], source=row[1], title=row[2], title_translated=row[3],
                    url=row[4], content=row[5], content_translated=row[6],
                    language=row[7], scraped_at=row[8], published_date=row[9] if len(row) > 9 else row[8]
                )
                articles.append(article)
        
        # Translate and truncate
        
        for art in articles:
            art.content = truncate_text(art.content, max_length=3000)
        
        translated_articles = translate_articles(articles)
        
        # Store in session instead of returning full data
        _current_session["scraped_articles"] = translated_articles
        
        print(f"✅ Fresh intel collected: {len(translated_articles)} articles")
        
        # Return summary only
        return json.dumps({
            "success": True,
            "articles_collected": len(translated_articles),
            "status": "ready_for_classification"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "articles_collected": 0
        })


@tool
def classify_intelligence(content_type: str = "both", severity: str = None, days_back: int = 7, max_results: int = 10) -> str:
    """Process and classify raw intelligence into CVEs and news items."""
    global _current_session
    print(f"🤖 Classifying intelligence...")
    
    if not _current_session["scraped_articles"]:
        return json.dumps({"error": "No scraped articles to classify"})
    
    articles = _current_session["scraped_articles"]
    cves = []
    news = []
    severity_list = [severity.upper()] if severity else []
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    try:
        for art in articles:
            print(f"🔍 Processing: {art.url[:50]}...")
            
            results = classify_article(art.content_translated)
            for result in results:
                if result["type"] == "CVE":
                    if severity_list and result["severity"].upper() not in severity_list:
                        continue
                        
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
                        intrigue=float(result["intrigue"]) if result["intrigue"] else 0.0,
                        affected_products=result["affected_products"]
                    )
                    
                    if vul.published_date >= cutoff_date:
                        cves.append(vul)
                        insert_cve(vul)
                        
                else:  # News item
                    news_item = NewsItem(
                        title=art.title,
                        title_translated=art.title_translated,
                        summary=result["summary"],
                        published_date=art.scraped_at,
                        original_language=art.language,
                        source=art.source,
                        intrigue=float(result["intrigue"]) if result["intrigue"] else 0.0,
                        url=art.url
                    )
                    
                    if news_item.published_date >= cutoff_date:
                        news.append(news_item)
                        insert_newsitem(news_item)
                
                mark_as_processed(art.url)
        
        # Rank and store in session
        ranked_cves = sorted(
            cves,
            key=lambda c: (c.cvss_score * 0.6 + c.intrigue * 0.4),
            reverse=True
        )[:max_results]
        
        ranked_news = sorted(
            news, 
            key=lambda n: n.intrigue, 
            reverse=True
        )[:max_results]
        
        _current_session["classified_cves"] = ranked_cves
        _current_session["classified_news"] = ranked_news
        
        # Save to files for backup
        from tools.tools import save_to_json
        save_to_json(ranked_cves, "classified_cves.json")
        save_to_json(ranked_news, "classified_news.json")
        
        print(f"🤖 Classified into {len(ranked_cves)} CVEs and {len(ranked_news)} news items")
        
        # Return summary only
        return json.dumps({
            "success": True,
            "cves_found": len(ranked_cves),
            "news_found": len(ranked_news),
            "status": "classification_complete"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "cves_found": 0,
            "news_found": 0
        })


@tool
def evaluate_intel_sufficiency(content_type: str = "both", max_results: int = 10) -> str:
    """Evaluate if classified intelligence meets requirements."""
    global _current_session
    print(f"📊 Evaluating intelligence sufficiency...")
    
    cves = _current_session.get("classified_cves", [])
    news = _current_session.get("classified_news", [])
    total_found = len(cves) + len(news)
    
    # Quality assessment
    high_quality_items = 0
    for cve in cves:
        if cve.cvss_score >= 7.0 or cve.severity.upper() in ["HIGH", "CRITICAL"]:
            high_quality_items += 1
    
    for news_item in news:
        if news_item.intrigue >= 7.0:
            high_quality_items += 1
    
    target_threshold = max_results * 0.7
    quality_threshold = max_results * 0.3
    
    if total_found >= target_threshold and high_quality_items >= quality_threshold:
        recommendation = "proceed"
        reasoning = f"Found {total_found} items ({high_quality_items} high-quality), exceeds thresholds"
        sufficient = True
    elif total_found >= target_threshold:
        recommendation = "proceed"
        reasoning = f"Sufficient quantity ({total_found} items) despite lower quality"
        sufficient = True
    else:
        recommendation = "intensive_rescrape"
        reasoning = f"Insufficient intel: only {total_found}/{max_results} items, {high_quality_items} high-quality"
        sufficient = False
    
    print(f"🎯 Sufficiency: {recommendation} - {reasoning}")
    
    return json.dumps({
        "sufficient": sufficient,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "items_found": total_found,
        "high_quality_items": high_quality_items
    })


@tool
def intensive_rescrape(content_type: str = "both", max_results: int = 10) -> str:
    """Execute intensive re-scraping with increased targets."""
    global _current_session
    print(f"🔥 Initiating INTENSIVE intelligence collection...")
    
    articles = _current_session.get("scraped_articles", [])  # Keep existing
    intensive_target = max(max_results, 10)
    
    try:
        print("🎯 INTENSIVE MODE: Expanding source coverage...")
        
        print("🇨🇳 Intensive Chinese scraping...")
        c_scraper = ChineseScraper(intensive_target)
        articles.extend(c_scraper.scrape_all())
        
        print("🇷🇺 Intensive Russian scraping...")
        r_scraper = RussianScraper()
        for round_num in range(2):
            print(f"  Round {round_num + 1}/2...")
            articles.extend(r_scraper.scrape_all())
        
        print("🇺🇸 Intensive English scraping...")
        e_scraper = EnglishScraper(intensive_target)
        articles.extend(e_scraper.scrape_all())
        
        # Remove duplicates
        unique_articles = []
        seen_urls = set()
        for art in articles:
            if art.url not in seen_urls:
                unique_articles.append(art)
                seen_urls.add(art.url)
        
        # Process articles
        for art in unique_articles:
            art.content = truncate_text(art.content, max_length=3000)
        
        translated_articles = translate_articles(unique_articles)
        _current_session["scraped_articles"] = translated_articles
        
        print(f"🔥 INTENSIVE collection complete: {len(translated_articles)} unique articles")
        
        return json.dumps({
            "success": True,
            "articles_collected": len(translated_articles),
            "intensive_mode": True,
            "status": "ready_for_classification"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "articles_collected": 0
        })


@tool
def present_results(output_format: str = "display") -> str:
    """Format and present the final intelligence report."""
    global _current_session
    print(f"📋 Preparing intelligence report...")
    
    cves = _current_session.get("classified_cves", [])
    news = _current_session.get("classified_news", [])
    
    if not cves and not news:
        return "❌ No intelligence data available. Run the data collection workflow first."
    
    # Build comprehensive report
    report = f"""
🔒 **CYBERSECURITY INTELLIGENCE REPORT**
📊 **Summary**: {len(cves)} Vulnerabilities | {len(news)} News Items
⏰ **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
🆔 **Session**: {_current_session.get('session_id', 'Unknown')}
{"="*60}

"""
    
    # Vulnerabilities Section
    if cves:
        report += f"""
🚨 **CRITICAL VULNERABILITIES ({len(cves)})**

"""
        for i, cve in enumerate(cves, 1):
            severity_emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠", 
                "MEDIUM": "🟡",
                "LOW": "🟢"
            }.get(cve.severity.upper(), "⚪")
            
            pub_date = cve.published_date
            if isinstance(pub_date, datetime):
                pub_date = pub_date.strftime('%Y-%m-%d')
            
            report += f"""**{i}. {cve.title_translated}**
{severity_emoji} **{cve.cve_id}** | Severity: {cve.severity} | CVSS: {cve.cvss_score:.1f}
📝 {cve.summary[:300]}{'...' if len(cve.summary) > 300 else ''}
📅 Published: {pub_date}
🌐 Source: {cve.source} ({cve.original_language})
🎯 Intrigue Score: {cve.intrigue:.1f}/10
🔗 {cve.url}
{"-"*40}

"""
    
    # News Section
    if news:
        report += f"""
📰 **THREAT INTELLIGENCE NEWS ({len(news)})**

"""
        for i, item in enumerate(news, 1):
            pub_date = item.published_date
            if isinstance(pub_date, datetime):
                pub_date = pub_date.strftime('%Y-%m-%d')
                
            report += f"""**{i}. {item.title_translated}**
📝 {item.summary[:300]}{'...' if len(item.summary) > 300 else ''}
📅 Published: {pub_date}
🌐 Source: {item.source} ({item.original_language})
🎯 Intrigue Score: {item.intrigue:.1f}/10
🔗 {item.url}
{"-"*40}

"""
    
    if not cves and not news:
        report += "\n❌ **No intelligence items found matching your criteria.**\n"
        report += "💡 Try expanding your search parameters or check back later for fresh intelligence.\n"
    
    report += f"""
{"="*60}
🤖 **Intelligence gathered by CyberIntel Agent**
📈 **Next automatic collection**: Every 6 hours
🔄 **Manual refresh**: Available on demand
"""
    
    return report