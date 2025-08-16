from langchain.tools import tool
from typing import List, Dict, Optional
from models import QueryParams, Article, Vulnerability, NewsItem
from datetime import datetime, timedelta
import json
import argostranslate.package
import argostranslate.translate
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from openai import OpenAI
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# Import your existing functions
from scrapers.chinese_scrape import ChineseScraper
from scrapers.english_scrape import EnglishScraper
from scrapers.russian_scrape import RussianScraper
from classify import classify_article, classify_articles_parallel
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

# _current_session = {
#     "scraped_articles": [],
#     "classified_cves": [],
#     "classified_news": [],
#     "session_id": None
# }

# def new_session():
#     """Start a new processing session"""
#     global _current_session
#     _current_session = {
#         "scraped_articles": [],
#         "classified_cves": [],
#         "classified_news": [],
#         "session_id": datetime.now().strftime("%Y%m%d_%H%M%S")
#     }
# Your existing helper functions
def translate_openai(text: str, source_lang: str, target_lang: str = "en") -> str:
    """Fast OpenAI translation"""
    if source_lang == target_lang:
        return text
    
    # Language mapping
    lang_map = {
        "zh": "Chinese",
        "ru": "Russian", 
        "en": "English"
    }
    source_name = lang_map.get(source_lang, source_lang)
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Fastest and cheapest
            messages=[{
                "role": "user", 
                "content": f"Translate this {source_name} text to English. Return only the translation, no explanations:\n\n{text}"
            }],
            temperature=0,
            max_tokens=len(text) + 100  # Efficient token usage
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text
def translate_articles_parallel(articles):
    """Parallel OpenAI translation - super fast"""
    print(f"🌍 Translating {len(articles)} articles with OpenAI...")

    non_english_articles = [art for art in articles if art.language != "en"]
    print(f"📊 Skipping {len(articles) - len(non_english_articles)} English articles")
    
    with ThreadPoolExecutor(max_workers=50) as executor:  # Higher workers for OpenAI
        # Submit all translation jobs
        future_to_article = {}

        for art in non_english_articles:
            if art.language != "en":
                # Translate title
                title_future = executor.submit(translate_openai, art.title, art.language)
                content_future = executor.submit(translate_openai, art.content, art.language)
                future_to_article[title_future] = (art, 'title')
                future_to_article[content_future] = (art, 'content')

        for art in articles:
            if art.language == "en":
                art.title_translated = art.title
                art.content_translated = art.content
        
        # Collect results
        for future in as_completed(future_to_article):
            art, field = future_to_article[future]
            try:
                result = future.result()
                if field == 'title':
                    art.title_translated = result
                else:
                    art.content_translated = result
            except Exception as e:
                print(f"Translation failed: {e}")
                # Fallback to original text
                if field == 'title':
                    art.title_translated = art.title
                else:
                    art.content_translated = art.content
    
    return articles

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

def truncate_text(text, language,max_length=2000):
    """Your existing truncate function"""
    if language == "zh":
        max_length = int(max_length * 0.4)  # 800 chars for Chinese
    elif language == "ru": 
        max_length = int(max_length * 0.7)
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
def analyze_data_needs(content_type: str = "both", severity = None, days_back: int = 7, max_results: int = 10) -> str:
    """Analyze current intelligence database to determine if fresh scraping is needed."""
    print(f"🔍 Analyzing intelligence needs...")
    init_db()

    if severity is None:
        severity_list = None
    elif isinstance(severity, str):
        severity_list = [severity.upper()]
    elif isinstance(severity, list):
        severity_list = [s.upper() for s in severity] if severity else None
    else:
        severity_list = None
    cutoff_date = datetime.now() - timedelta(days=days_back)
    num_cves = 0
    num_news = 0

    if content_type == "cve":
        existing_cves = get_cves_by_filters(
            severity_filter=severity_list,
            after_date=cutoff_date,
            limit=max_results
        )
        num_cves = len(existing_cves)
        needed_cves = max_results
        needed_news = 0
    elif content_type == "news":
        existing_news = get_news_by_filters(
            after_date=cutoff_date,
            limit=max_results
        )
        num_news = len(existing_news)
        needed_cves = 0
        needed_news = max_results
    # Count items based on content type requested
    else:
        needed_cves = max_results//2
        needed_news = max_results-needed_cves
        existing_cves = get_cves_by_filters(
            severity_filter=severity_list,
            after_date=cutoff_date,
            limit=needed_cves
        )
        existing_news = get_news_by_filters(
            after_date=cutoff_date,
            limit=needed_news
        )

        num_cves = len(existing_cves or [])
        num_news = len(existing_news or [])

    # Simple decision: do we have enough items?
    if num_cves >= needed_cves and num_news >=needed_news:
        recommendation = "sufficient"
        reasoning = f"Found {num_cves}/{needed_cves} and {num_news}/{needed_news}  items in database"
    else:
        recommendation = "urgent_scrape"
        reasoning = f"Need {needed_cves} cves and {needed_news} news items, only have {num_cves} cves and {num_news} news"
    
    print(f"📊 Analysis: {recommendation} - {reasoning}")
    
    return json.dumps({
        "recommendation": recommendation,
        "reasoning": reasoning,
        "existing_cves": num_cves,
        "existing_news": num_news,
        "needed_news": needed_news,
        "needed_cves": needed_cves
    })


@tool
def retrieve_existing_data(content_type: str = "both", severity: str = None, days_back: int = 7, max_results: int = 10) -> str:
    """Retrieve existing intelligence from database without scraping."""
    agent = retrieve_existing_data._agent_instance
    print(f"🗄️ Retrieving existing intelligence...")
    
    if severity is None:
        severity_list = None
    elif isinstance(severity, str):
        severity_list = [severity.upper()]
    elif isinstance(severity, list):
        severity_list = [s.upper() for s in severity] if severity else None
    else:
        severity_list = None
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    cves = []
    news = []
    
    if content_type == "both":
        cve_limit = max_results // 2
        news_limit = max_results - cve_limit 
        
        cves = get_cves_by_filters(
            severity_filter=severity_list,
            after_date=cutoff_date,
            limit=cve_limit
        )
        
        news = get_news_by_filters(
            after_date=cutoff_date,
            limit=news_limit
        )
    elif content_type == "cve":
        cves = get_cves_by_filters(
            severity_filter=severity_list,
            after_date=cutoff_date,
            limit=max_results
        )
    else:  # news
        news = get_news_by_filters(
            after_date=cutoff_date,
            limit=max_results
        )
    
    # Store in session, return summary only
    agent.current_session["classified_cves"] = cves
    agent.current_session["classified_news"] = news
    
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
    agent = scrape_fresh_intel._agent_instance
    print(f"🌐 Initiating fresh intelligence collection...")
    
    articles = []
    target_per_source = max(max_results // 2, 5)
    
    try:
        # # Multi-source scraping
        # print("🇨🇳 Scraping Chinese sources...")
        # c_scraper = ChineseScraper(target_per_source)
        # articles.extend(c_scraper.scrape_all())
        
        # print("🇷🇺 Scraping Russian sources...")
        # r_scraper = RussianScraper()
        # articles.extend(r_scraper.scrape_all())
        
        # print("🇺🇸 Scraping English sources...")
        # e_scraper = EnglishScraper(target_per_source)
        # articles.extend(e_scraper.scrape_all())
        scrapers = [
            ChineseScraper(target_per_source),
            RussianScraper(),
            EnglishScraper(target_per_source)
        ]
        
        articles = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(scraper.scrape_all) for scraper in scrapers]
            for future in as_completed(futures):
                articles.extend(future.result())
        
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
            art.content = truncate_text(art.content, art.language, max_length=2000)
        
        translated_articles = translate_articles_parallel(articles)
        
        agent.current_session["scraped_articles"] = translated_articles
        
        print(f"✅ Fresh intel collected: {len(translated_articles)} articles")
        
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
def should_classify_article(article, min_length=200):
    """Filter out articles that aren't worth classifying"""
    content = article.content_translated or article.content
    
    # Skip if too short (your logs show 81-99 char articles being processed)
    if not content or len(content.strip()) < min_length:
        return False
    
    # Skip if no cybersecurity keywords
    text = (article.title + " " + content).lower()
    security_keywords = [
        "cve", "vulnerability", "exploit", "security", "attack", 
        "breach", "malware", "ransomware", "patch", "zero-day"
    ]
    
    if not any(keyword in text for keyword in security_keywords):
        return False
    
    return True

@tool
def classify_intelligence(content_type: str = "both", severity: str = None, days_back: int = 7, max_results: int = 10, max_workers: int = 10) -> str:
    """Process and classify raw intelligence into CVEs and news items using parallel processing."""
    agent = classify_intelligence._agent_instance
    print(f"🤖 Starting PARALLEL classification...")
    
    if not agent.current_session["scraped_articles"]:
        return json.dumps({"error": "No scraped articles to classify"})
    
    articles = agent.current_session["scraped_articles"]
    if severity is None:
        severity_list = []
    elif isinstance(severity, str):
        severity_list = [severity.upper()]
    elif isinstance(severity, list):
        severity_list = [s.upper() for s in severity] if severity else []
    else:
        severity_list = []
    
    print(f"🎯 Severity filter: {severity_list}")  # Debug line
    cutoff_date = datetime.now() - timedelta(days=days_back)

    recent_articles = []
    for art in articles:
        # Skip if outside date range
        if art.scraped_at < cutoff_date:
            continue
        # Skip if too short (your logs show 81-99 char articles)
        content_to_check = art.content_translated or art.content
        if not content_to_check or len(content_to_check.strip()) < 200:
            print(f"⚠️  Skipping short article: {len(content_to_check) if content_to_check else 0} chars")
            continue
        recent_articles.append(art)
    
    print(f"📅 Filtered to {len(recent_articles)} recent articles (within {days_back} days, min 200 chars)")
    
    if not recent_articles:
        return json.dumps({"error": "No recent articles to process"})
    max_to_process = min(len(recent_articles), max_results * 2)
    articles_to_process = recent_articles[:max_to_process]
    print(f"📊 Processing {len(articles_to_process)} articles (limited from {len(recent_articles)})")

    try:
        # Prepare data for parallel processing
        articles_data = []
        for i, art in enumerate(articles_to_process):
            content_to_classify = art.content_translated or art.content
            if content_to_classify:  # Only include articles with content
                articles_data.append((i, content_to_classify, art.url))
        
        print(f"📊 Prepared {len(articles_data)} articles for parallel classification")
        
        if not articles_data:
            return json.dumps({"error": "No articles with content to classify"})
        
        # Parallel classification
        parallel_results = classify_articles_parallel(articles_data, max_workers=max_workers, target_results=max_results )
        
        # Process results
        cves = []
        news = []
        successful_classifications = 0
        failed_classifications = 0
        
        # Create a mapping from index to article object
        article_map = {i: recent_articles[i] for i in range(len(recent_articles))}

        
        for index, success, results, error_msg in parallel_results:
            art = article_map[index]
            
            if not success or not results:
                print(f"❌ Failed to classify {art.url}: {error_msg}")
                failed_classifications += 1
                mark_as_processed(art.url)  # Still mark as processed
                continue
            
            # Process each classification result for this article
            for result in results:
                try:
                    print(f"🔍 Processing result: {result}")
                    if result["type"] == "CVE" and content_type in ["cve", "both"]:
                        print(f"🚨 Found CVE: {result['cve_id']}")

                        if severity_list and result["severity"].upper() not in severity_list:
                            print(f"⚠️  CVE {result['cve_id']} severity '{result['severity']}' not in filter {severity_list}")
                            continue
                            
                        # Handle cve_id being a list or single value
                        cve_id_value = result["cve_id"]
                        if isinstance(cve_id_value, list):
                            cve_id = cve_id_value[0] if cve_id_value else "Unknown"
                        else:
                            cve_id = cve_id_value or "Unknown"
                            
                        vul = Vulnerability(
                            cve_id=cve_id,
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
                            affected_products=result.get("affected_products", [])
                        )
           
                        cves.append(vul)
                        insert_cve(vul)
                        print(f"✅ Added CVE to list: {cve_id}")
                            
                    elif result["type"] != "CVE" and content_type in ["news", "both"]:  # News item
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
                        
                        news.append(news_item)
                        insert_newsitem(news_item)
                    
                    successful_classifications += 1
                
                   
                
                    
                except Exception as e:
                    print(f"⚠️  Error processing classification result for {art.url}: {e}")
                    failed_classifications += 1
                    continue
            
            # Mark article as processed regardless of classification success
            mark_as_processed(art.url)
        
        print(f"📊 Classification Summary:")
        print(f"  ✅ Successful: {successful_classifications}")
        print(f"  ❌ Failed: {failed_classifications}")
        print(f"  📈 CVEs found: {len(cves)}")
        print(f"  📰 News found: {len(news)}")
        
        # Rank and store in session (same logic as before)
        ranked_cves = sorted(
            cves,
            key=lambda c: (c.cvss_score * 0.6 + c.intrigue * 0.4),
            reverse=True
        )
        ranked_news = sorted(
            news,   
            key=lambda n: n.intrigue, 
            reverse=True
        )

        if content_type == "cve":
            final_cves = ranked_cves[:max_results]
            final_news = []
        elif content_type == "news":
            final_cves = []
            final_news = ranked_news[:max_results]
        else:  # both - dynamic allocation
            target_cves = max_results // 2
            target_news = max_results // 2
            
            # Take what we can get for CVEs
            final_cves = ranked_cves[:target_cves]
            remaining_slots = max_results - len(final_cves)
            
            # Fill remaining slots with news
            final_news = ranked_news[:remaining_slots]
        
        agent.current_session["classified_cves"] = final_cves
        agent.current_session["classified_news"] = final_news
        
        # Save to files for backup
        save_to_json(final_cves, "classified_cves.json")
        save_to_json(final_news, "classified_news.json")
        
        print(f"🎯 PARALLEL classification complete!")
        print(f"🚀 Final results: {len(final_cves)} CVEs and {len(final_news)} news items")
        
        # Return summary
        return json.dumps({
            "success": True,
            "cves_found": len(final_cves),
            "news_found": len(final_news),
            "successful_classifications": successful_classifications,
            "failed_classifications": failed_classifications,
            "status": "parallel_classification_complete"
        })
        
    except Exception as e:
        print(f"❌ Critical error in parallel classification: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "cves_found": 0,
            "news_found": 0
        })
# @tool
# def classify_intelligence(content_type: str = "both", severity: str = None, days_back: int = 7, max_results: int = 10) -> str:
#     """Process and classify raw intelligence into CVEs and news items."""
#     agent = classify_intelligence._agent_instance
#     print(f"🤖 Classifying intelligence...")
    
#     if not agent.current_session["scraped_articles"]:
#         return json.dumps({"error": "No scraped articles to classify"})
    
#     articles = agent.current_session["scraped_articles"]
#     cves = []
#     news = []
#     severity_list = [severity.upper()] if severity else []
#     cutoff_date = datetime.now() - timedelta(days=days_back)

#     recent_articles = [art for art in articles if art.scraped_at >= cutoff_date]
#     print(f"📅 Filtered to {len(recent_articles)} recent articles (within {days_back} days)")
 
#     try:
#         for art in recent_articles:
#             print(f"🔍 Processing: {art.url[:50]}...")
            
#             results = classify_article(art.content_translated)
#             for result in results:
#                 if result["type"] == "CVE" and content_type in ["cve", "both"]:
#                     if severity_list and result["severity"].upper() not in severity_list:
#                         continue
                        
#                     vul = Vulnerability(
#                         cve_id=result["cve_id"][0] if result["cve_id"] else "Unknown",
#                         title=art.title,
#                         title_translated=art.title_translated,
#                         summary=result["summary"],
#                         severity=result["severity"],
#                         cvss_score=float(result["cvss_score"]) if result["cvss_score"] else 0.0,
#                         published_date=art.scraped_at,
#                         original_language=art.language,
#                         source=art.source,
#                         url=art.url,
#                         intrigue=float(result["intrigue"]) if result["intrigue"] else 0.0,
#                         affected_products=result["affected_products"]
#                     )
       
#                     cves.append(vul)
#                     insert_cve(vul)
                        
#                 elif result["type"] != "CVE" and content_type in ["news", "both"]:  # News item
#                     news_item = NewsItem(
#                         title=art.title,
#                         title_translated=art.title_translated,
#                         summary=result["summary"],
#                         published_date=art.scraped_at,
#                         original_language=art.language,
#                         source=art.source,
#                         intrigue=float(result["intrigue"]) if result["intrigue"] else 0.0,
#                         url=art.url
#                     )
                    

#                     news.append(news_item)
#                     insert_newsitem(news_item)
                
#                 mark_as_processed(art.url)
        
#         # Rank and store in session
#         ranked_cves = sorted(
#             cves,
#             key=lambda c: (c.cvss_score * 0.6 + c.intrigue * 0.4),
#             reverse=True
#         )
#         ranked_news = sorted(
#             news,   
#             key=lambda n: n.intrigue, 
#             reverse=True
#         )

#         if content_type == "cve":
#             final_cves = ranked_cves[:max_results]
#             final_news = []
#         elif content_type == "news":
#             final_cves = []
#             final_news = ranked_news[:max_results]
#         else:  # both - dynamic allocation
#             target_cves = max_results // 2
#             target_news = max_results // 2
            
#             # Take what we can get for CVEs
#             final_cves = ranked_cves[:target_cves]
#             remaining_slots = max_results - len(final_cves)
            
#             # Fill remaining slots with news
#             final_news = ranked_news[:remaining_slots]
        
#         agent.current_session["classified_cves"] = final_cves
#         agent.current_session["classified_news"] = final_news
        
#         # Save to files for backup
#         save_to_json(final_cves, "classified_cves.json")
#         save_to_json(final_news, "classified_news.json")
        
#         print(f"🤖 Classified into {len(final_cves)} CVEs and {len(final_news)} news items")
        
#         # Return summary only
#         return json.dumps({
#             "success": True,
#             "cves_found": len(final_cves),
#             "news_found": len(final_news),
#             "status": "classification_complete"
#         })
        
#     except Exception as e:
#         return json.dumps({
#             "success": False,
#             "error": str(e),
#             "cves_found": 0,
#             "news_found": 0
#         })


@tool
def evaluate_intel_sufficiency(content_type: str = "both", max_results: int = 10) -> str:
    """Evaluate if classified intelligence meets requirements."""
    agent = evaluate_intel_sufficiency._agent_instance
    print(f"📊 Evaluating intelligence sufficiency...")
    
    cves = agent.current_session.get("classified_cves", [])
    news = agent.current_session.get("classified_news", [])
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
    agent = intensive_rescrape._agent_instance
    print(f"🔥 Initiating INTENSIVE intelligence collection...")
    
    articles = agent.current_session["scraped_articles"]
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
        agent.current_session["scraped_articles"] = translated_articles
        
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
def present_results(output_format: str = "json") -> str:
    """Return final intelligence data as JSON for frontend consumption."""
    agent = present_results._agent_instance
    print(f"📋 Preparing intelligence data...")
    
    cves = agent.current_session.get("classified_cves", [])
    news = agent.current_session.get("classified_news", [])
    
    if not cves and not news:
        return json.dumps({
            "success": False,
            "error": "No intelligence data available",
            "cves": [],
            "news": []
        })
    
    # Convert to JSON-serializable format
    cves_data = []
    for cve in cves:
        cves_data.append({
            "cve_id": cve.cve_id,
            "title": cve.title,
            "title_translated": cve.title_translated,
            "summary": cve.summary,
            "severity": cve.severity,
            "cvss_score": float(cve.cvss_score),
            "intrigue": float(cve.intrigue),
            "published_date": cve.published_date.isoformat() if hasattr(cve.published_date, 'isoformat') else str(cve.published_date),
            "original_language": cve.original_language,
            "source": cve.source,
            "url": cve.url,
            "affected_products": getattr(cve, 'affected_products', [])
        })
    
    news_data = []
    for news_item in news:
        news_data.append({
            "title": news_item.title,
            "title_translated": news_item.title_translated,
            "summary": news_item.summary,
            "intrigue": float(news_item.intrigue),
            "published_date": news_item.published_date.isoformat() if hasattr(news_item.published_date, 'isoformat') else str(news_item.published_date),
            "original_language": news_item.original_language,
            "source": news_item.source,
            "url": news_item.url
        })
    
    result = {
        "success": True,
        "cves_count": len(cves),
        "news_count": len(news),
        "total_results": len(cves) + len(news),
        "session_id": agent.current_session.get('session_id', 'Unknown'),
        "generated_at": datetime.now().isoformat(),
        "status": "Data available in session"  # Key point - data is in session
    }
    
    print(f"✅ Summary prepared: {len(cves)} CVEs, {len(news)} news items in session")
    
    return json.dumps(result)

# @tool
# def present_results(output_format: str = "display") -> str:
#     """Format and present the final intelligence report."""
#     global _current_session
#     print(f"📋 Preparing intelligence report...")
    
#     cves = _current_session.get("classified_cves", [])
#     news = _current_session.get("classified_news", [])
    
#     if not cves and not news:
#         return "❌ No intelligence data available. Run the data collection workflow first."
    
#     # Build comprehensive report
#     report = f"""
# 🔒 **CYBERSECURITY INTELLIGENCE REPORT**
# 📊 **Summary**: {len(cves)} Vulnerabilities | {len(news)} News Items
# ⏰ **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
# 🆔 **Session**: {_current_session.get('session_id', 'Unknown')}
# {"="*60}

# """
    
#     # Vulnerabilities Section
#     if cves:
#         report += f"""
# 🚨 **CRITICAL VULNERABILITIES ({len(cves)})**

# """
#         for i, cve in enumerate(cves, 1):
#             severity_emoji = {
#                 "CRITICAL": "🔴",
#                 "HIGH": "🟠", 
#                 "MEDIUM": "🟡",
#                 "LOW": "🟢"
#             }.get(cve.severity.upper(), "⚪")
            
#             pub_date = cve.published_date
#             if isinstance(pub_date, datetime):
#                 pub_date = pub_date.strftime('%Y-%m-%d')
            
#             report += f"""**{i}. {cve.title_translated}**
# {severity_emoji} **{cve.cve_id}** | Severity: {cve.severity} | CVSS: {cve.cvss_score:.1f}
# 📝 {cve.summary[:300]}{'...' if len(cve.summary) > 300 else ''}
# 📅 Published: {pub_date}
# 🌐 Source: {cve.source} ({cve.original_language})
# 🎯 Intrigue Score: {cve.intrigue:.1f}/10
# 🔗 {cve.url}
# {"-"*40}

# """
    
#     # News Section
#     if news:
#         report += f"""
# 📰 **THREAT INTELLIGENCE NEWS ({len(news)})**

# """
#         for i, item in enumerate(news, 1):
#             pub_date = item.published_date
#             if isinstance(pub_date, datetime):
#                 pub_date = pub_date.strftime('%Y-%m-%d')
                
#             report += f"""**{i}. {item.title_translated}**
# 📝 {item.summary[:300]}{'...' if len(item.summary) > 300 else ''}
# 📅 Published: {pub_date}
# 🌐 Source: {item.source} ({item.original_language})
# 🎯 Intrigue Score: {item.intrigue:.1f}/10
# 🔗 {item.url}
# {"-"*40}

# """
    
#     if not cves and not news:
#         report += "\n❌ **No intelligence items found matching your criteria.**\n"
#         report += "💡 Try expanding your search parameters or check back later for fresh intelligence.\n"
    
#     report += f"""
# {"="*60}
# 🤖 **Intelligence gathered by CyberIntel Agent**
# 📈 **Next automatic collection**: Every 6 hours
# 🔄 **Manual refresh**: Available on demand
# """
    
#     return report