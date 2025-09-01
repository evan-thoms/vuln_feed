from langchain.tools import tool
from typing import List, Dict, Optional
from models import QueryParams, Article, Vulnerability, NewsItem
from datetime import datetime, timedelta
import json
# Translation handled by OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.date_utils import parse_date_safe, normalize_date_for_article
import os
from openai import OpenAI
try:
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception as e:
    print("⚠️ OpenAI API key not configured. Some features disabled.")
    openai_client = None

# Import WebSocket manager for progress updates
try:
    from main import manager
except ImportError:
    # Fallback if main.py not available
    manager = None

async def send_progress_update(status: str, progress: int):
    """Send progress update via WebSocket"""
    if manager:
        try:
            await manager.broadcast(json.dumps({
                "type": "progress",
                "status": status,
                "progress": progress
            }))
        except Exception as e:
            print(f"⚠️ WebSocket update failed: {e}")


# Import your existing functions
from scrapers.chinese_scrape import ChineseScraper
from scrapers.russian_scrape import RussianScraper
# EnglishScraperWithVulners will be imported conditionally to handle Vulners API failures
from classify import classify_article, classify_articles_parallel
from db import (
    init_db, insert_raw_article, is_article_scraped, mark_as_processed,
    get_unprocessed_articles, insert_cve, insert_newsitem, get_cves_by_filters, 
    get_news_by_filters, get_last_scrape_time, get_data_statistics,
    get_classified_article, is_article_classified
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
def translate_openai(text: str, source_lang: str) -> str:
    """Fast OpenAI translation with optimized settings"""
    if source_lang == "en":
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
            model="gpt-3.5-turbo",  # Faster than gpt-4
            messages=[
                {"role": "system", "content": f"Translate the following text from {source_lang} to English. Keep it concise and accurate."},
                {"role": "user", "content": text}
            ],
            max_tokens=200,  # Limit response length
            temperature=0.1,  # More deterministic
            timeout=15  # Increased timeout for translation
        )
        result = response.choices[0].message.content.strip()
        return result
    except Exception as e:
        print(f"❌ Translation error: {e}")
        return text
def translate_articles_parallel(articles):
    """Parallel OpenAI translation - super fast"""
    # Filter out articles that are already translated
    articles_to_translate = []
    already_translated = []
    
    for art in articles:
        if art.language == "en":
            # English articles don't need translation
            art.title_translated = art.title
            art.content_translated = art.content
            already_translated.append(art)
        elif art.title_translated and art.content_translated:
            # Already translated articles
            already_translated.append(art)
        else:
            # Need translation
            articles_to_translate.append(art)

    if not articles_to_translate:
        return articles  # All articles are already translated
    
    with ThreadPoolExecutor(max_workers=40) as executor:
        # Submit all translation jobs
        future_to_article = {}

        for art in articles_to_translate:
            if art.language != "en":
                # Translate title
                title_future = executor.submit(translate_openai, art.title, art.language)
                content_future = executor.submit(translate_openai, art.content, art.language)
                future_to_article[title_future] = (art, 'title')
                future_to_article[content_future] = (art, 'content')

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
                print(f"❌ Translation failed: {e}")
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
    """Translation handled by OpenAI - placeholder for compatibility"""
    # This function is no longer used since we use OpenAI for translation
    return text

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
        scraped_at=parse_date_safe(row[8]) or datetime.now(),
        published_date=parse_date_safe(row[9] if len(row) > 9 else row[8]) or datetime.now()
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
    if num_cves >= needed_cves and num_news >= needed_news:
        recommendation = "sufficient"
        reasoning = f"Found {num_cves}/{needed_cves} CVEs and {num_news}/{needed_news} news items in database"
    else:
        recommendation = "urgent_scrape"
        reasoning = f"Need {needed_cves} CVEs and {needed_news} news items, only have {num_cves} CVEs and {num_news} news items"
    
    # Debug logging for production troubleshooting
    print(f"🔍 DEBUG: Content type: {content_type}")
    print(f"🔍 DEBUG: Severity filter: {severity_list}")
    print(f"🔍 DEBUG: Days back: {days_back} (cutoff: {cutoff_date.isoformat()})")
    print(f"🔍 DEBUG: Found CVEs: {num_cves}, needed: {needed_cves}")
    print(f"🔍 DEBUG: Found news: {num_news}, needed: {needed_news}")
    print(f"🔍 DEBUG: Recommendation: {recommendation}")
    
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
def retrieve_existing_data(content_type: str = "both", severity = None, days_back: int = 7, max_results: int = 10) -> str:
    """Retrieve existing intelligence from database without scraping."""
    agent = retrieve_existing_data._agent_instance
    print(f"🗄️ Retrieving existing intelligence...")
    print(f"🔍 DEBUG: Received severity parameter: {severity} (type: {type(severity)})")
    
    if severity is None:
        severity_list = None
    elif isinstance(severity, str):
        severity_list = [severity.upper()]
    elif isinstance(severity, list):
        severity_list = [s.upper() for s in severity] if severity else None
    else:
        severity_list = None
    
    print(f"🔍 DEBUG: Processed severity_list: {severity_list}")
    
    # Use a more generous date filter to include recently scraped articles
    # This accounts for articles that were scraped recently but might have older published dates
    cutoff_date = datetime.now() - timedelta(days=days_back)  # Back to original logic
    
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
    print(f"📅 Using cutoff date: {cutoff_date.isoformat()}")
    print(f"🎯 Severity filter: {severity_list}")
    print(f"📊 Content type: {content_type}, Max results: {max_results}")
    
    return json.dumps({
        "success": True,
        "cves_found": len(cves),
        "news_found": len(news),
        "source": "database_cache"
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
def classify_intelligence(content_type: str = "both", severity: Optional[str] = None, days_back: int = 7, max_results: int = 10, max_workers: int = 10) -> str:
    """Process and classify raw intelligence into CVEs and news items using parallel processing."""
    agent = classify_intelligence._agent_instance
    print(f"🤖 Starting PARALLEL classification...")
    
    # Send progress update (non-blocking)
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(send_progress_update("Classifying threats...", 75))
    except:
        pass
    
    if not agent.current_session["scraped_articles"]:
        print("⚠️ No articles to classify - returning empty results")
        agent.current_session["classified_cves"] = []
        agent.current_session["classified_news"] = []
        return json.dumps({
            "success": True,
            "cves_found": 0,
            "news_found": 0,
            "status": "no_articles_to_classify"
        })
    
    # Get severity from agent's current parameters if not provided
    if severity is None and hasattr(agent, 'current_params'):
        severity = agent.current_params.get('severity', [])
    
    articles = agent.current_session["scraped_articles"]
    if severity is None:
        severity_list = []
    elif isinstance(severity, str):
        severity_list = [severity.upper()]
    elif isinstance(severity, list):
        severity_list = [s.upper() for s in severity] if severity else []
    else:
        severity_list = []
    
    # Debug: Print the actual severity parameter being used
    print(f"🔍 DEBUG: Original severity parameter: {severity}")
    print(f"🔍 DEBUG: Agent current_params severity: {getattr(agent, 'current_params', {}).get('severity', 'Not found')}")
    print(f"🔍 DEBUG: Final severity_list: {severity_list}")
    
    print(f"🎯 Severity filter: {severity_list}")  # Debug line
    cutoff_date = datetime.now() - timedelta(days=days_back)

    recent_articles = []
    for art in articles:
        # Debug: Print article filtering info
        print(f"🔍 Filtering article: {art.source} - {art.title[:50]}...")
        print(f"  Scraped at: {art.scraped_at}")
        print(f"  Cutoff date: {cutoff_date}")
        print(f"  Days old: {(datetime.now() - art.scraped_at).days}")
        
        # Skip if outside date range
        if art.scraped_at < cutoff_date:
            print(f"  ❌ Filtered out: Too old")
            continue
            
        # Skip if too short (your logs show 81-99 char articles)
        content_to_check = art.content_translated or art.content
        if not content_to_check or len(content_to_check.strip()) < 200:
            print(f"  ❌ Filtered out: Too short ({len(content_to_check) if content_to_check else 0} chars)")
            continue
        
        # Early filtering: skip if no security keywords
        text = (art.title + " " + content_to_check).lower()
        security_keywords = ["cve", "vulnerability", "exploit", "security", "attack", "breach", "malware"]
        if not any(keyword in text for keyword in security_keywords):
            print(f"  ❌ Filtered out: No security keywords")
            continue
            
        print(f"  ✅ Passed all filters")
        recent_articles.append(art)
    
    print(f"📅 Filtered to {len(recent_articles)} recent articles (within {days_back} days, min 200 chars)")
    
    if not recent_articles:
        print("⚠️ No recent articles to process - returning empty results")
        agent.current_session["classified_cves"] = []
        agent.current_session["classified_news"] = []
        return json.dumps({
            "success": True,
            "cves_found": 0,
            "news_found": 0,
            "status": "no_recent_articles"
        })
    
    # Process ALL articles that passed filters - don't waste scraping effort
    articles_to_process = recent_articles
    print(f"📊 Processing {len(articles_to_process)} articles (limited from {len(recent_articles)})")

    try:
        # Prepare data for parallel processing
        articles_data = []
        
        for i, art in enumerate(articles_to_process):
            # All articles here are already unscraped, so they can't be classified
            content_to_classify = art.content_translated or art.content
            if content_to_classify:  # Only include articles with content
                articles_data.append((i, content_to_classify, art.url))
        
        print(f"📊 Prepared {len(articles_data)} articles for parallel classification")
        print(f"⏭️  All articles are new (already filtered out scraped ones)")
        
        if not articles_data:
            print("⚠️ No articles with content to classify - returning empty results")
            agent.current_session["classified_cves"] = []
            agent.current_session["classified_news"] = []
            return json.dumps({
                "success": True,
                "cves_found": 0,
                "news_found": 0,
                "status": "no_articles_with_content"
            })
        
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
                try:
                    mark_as_processed(art.url)  # Still mark as processed
                except Exception as e:
                    print(f"⚠️ Error marking as processed: {e}")
                continue
            
            # Process each classification result for this article
            for result in results:
                try:
                    # print(f"🔍 Processing result: {result}")
                    if result["type"] == "CVE" and content_type in ["cve", "both"]:
                        print(f"🚨 Found CVE: {result['cve_id']}")

                        # Apply severity filter to newly classified CVEs
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
                            published_date=art.published_date,
                            original_language=art.language,
                            source=art.source,
                            url=art.url,
                            intrigue=float(result["intrigue"]) if result["intrigue"] else 0.0,
                            affected_products=result.get("affected_products", [])
                        )
           
                        cves.append(vul)
                        try:
                            session_id = agent.current_session.get('session_id', 'unknown')
                            insert_cve(vul, session_id)
                        except Exception as e:
                            print(f"⚠️ Error inserting CVE: {e}")
                        print(f"✅ Added CVE to list: {cve_id}")
                            
                    elif result["type"] != "CVE" and content_type in ["news", "both"]:  # News item
                        news_item = NewsItem(
                            title=art.title,
                            title_translated=art.title_translated,
                            summary=result["summary"],
                            published_date=art.published_date,
                            original_language=art.language,
                            source=art.source,
                            intrigue=float(result["intrigue"]) if result["intrigue"] else 0.0,
                            url=art.url
                        )
                        
                        news.append(news_item)
                        try:
                            session_id = agent.current_session.get('session_id', 'unknown')
                            insert_newsitem(news_item, session_id)
                        except Exception as e:
                            print(f"⚠️ Error inserting news item: {e}")
                    
                    successful_classifications += 1
                
                   
                
                    
                except Exception as e:
                    print(f"⚠️  Error processing classification result for {art.url}: {e}")
                    failed_classifications += 1
                    continue
            
            # Mark article as processed regardless of classification success
            try:
                mark_as_processed(art.url)
            except Exception as e:
                print(f"⚠️ Error marking as processed: {e}")
        
        print(f"📊 Classification Summary:")
        print(f"  ✅ Successful: {successful_classifications}")
        print(f"  ❌ Failed: {failed_classifications}")
        print(f"  📈 CVEs found: {len(cves)}")
        print(f"  📰 News found: {len(news)}")
        
        # Already classified articles will be queried from database at the end
        # No need to add them here since the database query handles this
        
        # QUERY DATABASE FOR EXISTING HIGH-QUALITY ARTICLES
        print(f"🗄️ Querying database for existing high-quality articles...")
        
        # Query existing CVEs from database
        if content_type in ["cve", "both"]:
            try:
                existing_cves = get_cves_by_filters(
                    severity_filter=severity_list,
                    after_date=cutoff_date,
                    limit=max_results * 3  # Get more existing CVEs for ranking
                )
                print(f"📊 Found {len(existing_cves)} existing CVEs in database")
                
                # Add existing CVEs to our list
                for existing_cve in existing_cves:
                    # Avoid duplicates by checking URL
                    if not any(cve.url == existing_cve.url for cve in cves):
                        cves.append(existing_cve)
                        print(f"📋 Added existing CVE from database: {existing_cve.cve_id}")
                    else:
                        print(f"⚠️ Skipping duplicate CVE: {existing_cve.cve_id}")
                        
            except Exception as e:
                print(f"⚠️ Error querying existing CVEs: {e}")
        
        # Query existing news from database
        if content_type in ["news", "both"]:
            try:
                existing_news = get_news_by_filters(
                    after_date=cutoff_date,
                    limit=max_results * 3  # Get more existing news for ranking
                )
                print(f"📊 Found {len(existing_news)} existing news items in database")
                
                # Add existing news to our list
                for existing_news_item in existing_news:
                    # Avoid duplicates by checking URL
                    if not any(news_item.url == existing_news_item.url for news_item in news):
                        news.append(existing_news_item)
                        print(f"📋 Added existing news from database: {existing_news_item.title[:50]}...")
                    else:
                        print(f"⚠️ Skipping duplicate news: {existing_news_item.title[:50]}...")
                        
            except Exception as e:
                print(f"⚠️ Error querying existing news: {e}")
        
        print(f"📊 Combined results: {len(cves)} CVEs, {len(news)} news items")
        print(f"🔍 DEBUG: CVE sources - New: {len([c for c in cves if c.source in ['FreeBuf', 'Anquanke', 'Anti-Malware']])}, Database: {len([c for c in cves if c.source not in ['FreeBuf', 'Anquanke', 'Anti-Malware']])}")
        print(f"🔍 DEBUG: News sources - New: {len([n for n in news if n.source in ['FreeBuf', 'Anquanke', 'Anti-Malware']])}, Database: {len([n for n in news if n.source not in ['FreeBuf', 'Anquanke', 'Anti-Malware']])}")
        
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
        else:  # both - proper ranking across all items
            # For "both" content type, ensure 50/50 split of max_results
            half_results = max_results // 2
            
            # Take top CVEs (up to half)
            final_cves = ranked_cves[:half_results]
            
            # Take top news items (up to half)
            final_news = ranked_news[:half_results]
            
            # If we have room for more items, fill with the best remaining
            remaining_slots = max_results - len(final_cves) - len(final_news)
            if remaining_slots > 0:
                # Create a combined list of remaining items
                remaining_cves = ranked_cves[half_results:]
                remaining_news = ranked_news[half_results:]
                
                combined_remaining = []
                
                for cve in remaining_cves:
                    combined_remaining.append({
                        'item': cve,
                        'score': cve.cvss_score * 0.6 + cve.intrigue * 0.4,
                        'type': 'CVE'
                    })
                
                for news_item in remaining_news:
                    combined_remaining.append({
                        'item': news_item,
                        'score': news_item.intrigue,
                        'type': 'News'
                    })
                
                # Sort remaining items by score
                combined_remaining.sort(key=lambda x: x['score'], reverse=True)
                
                # Add best remaining items
                for combined_item in combined_remaining[:remaining_slots]:
                    if combined_item['type'] == 'CVE':
                        final_cves.append(combined_item['item'])
                    else:
                        final_news.append(combined_item['item'])
        
        agent.current_session["classified_cves"] = final_cves
        agent.current_session["classified_news"] = final_news
        
        # Save to files for backup
        try:
            save_to_json(final_cves, "classified_cves.json")
            save_to_json(final_news, "classified_news.json")
        except Exception as e:
            print(f"⚠️ Error saving to JSON: {e}")
        
        print(f"🎯 PARALLEL classification complete!")
        print(f"🚀 Final results: {len(final_cves)} CVEs and {len(final_news)} news items")
        print(f"🔍 DEBUG: Final CVE sources - New: {len([c for c in final_cves if c.source in ['FreeBuf', 'Anquanke', 'Anti-Malware']])}, Database: {len([c for c in final_cves if c.source not in ['FreeBuf', 'Anquanke', 'Anti-Malware']])}")
        print(f"🔍 DEBUG: Final News sources - New: {len([n for n in final_news if n.source in ['FreeBuf', 'Anquanke', 'Anti-Malware']])}, Database: {len([n for n in final_news if n.source not in ['FreeBuf', 'Anquanke', 'Anti-Malware']])}")
        
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
        # Return empty results instead of failure to prevent infinite loops
        agent.current_session["classified_cves"] = []
        agent.current_session["classified_news"] = []
        return json.dumps({
            "success": True,
            "cves_found": 0,
            "news_found": 0,
            "status": "classification_error",
            "note": f"Classification failed but continuing: {str(e)}"
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
        # Simplified: instead of intensive_rescrape, just proceed with what we have
        recommendation = "proceed"
        reasoning = f"Limited results ({total_found} items) but proceeding to avoid infinite loops"
        sufficient = True
    
    print(f"🎯 Sufficiency: {recommendation} - {reasoning}")
    
    return json.dumps({
        "sufficient": sufficient,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "items_found": total_found,
        "high_quality_items": high_quality_items
    })


# Removed intensive_rescrape function to prevent infinite loops and improve performance
@tool
def scrape_fresh_intel(content_type: str = "both", max_results: int = None) -> str:
    """Scrape fresh intelligence from multiple sources."""
    try:
        # Get max_results from agent's current parameters if not provided
        if max_results is None:
            agent = scrape_fresh_intel._agent_instance
            if hasattr(agent, 'current_params'):
                max_results = agent.current_params.get('max_results', 10)
            else:
                max_results = 10
        
        # Send progress update (non-blocking)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(send_progress_update("Scraping intelligence sources...", 25))
        except:
            pass
        
        # Calculate target per source - reduced for Render performance
        target_per_source = max(max_results // 3, 2)  # Much smaller targets
        
        print(f"🌐 Initiating fresh intelligence collection...")
        
        # Initialize scrapers
        scrapers = [
            ChineseScraper(target_per_source),
            RussianScraper(target_per_source),
        ]
        
        # Add English scraper with Vulners
        try:
            from scrapers.english_scrape_with_vulners import EnglishScraperWithVulners
            scrapers.append(EnglishScraperWithVulners(target_per_source))
            print("✅ Using Vulners scraper")
        except Exception as e:
            print(f"❌ Vulners scraper failed: {e}")
            # Continue with just Chinese and Russian scrapers
        
        articles = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(scraper.scrape_all) for scraper in scrapers]
            for i, future in enumerate(as_completed(futures)):
                try:
                    # Much shorter timeout for Render
                    result = future.result(timeout=20)  # 20 second timeout per scraper
                    print(f"✅ Scraper {i+1} completed: {len(result)} articles")
                    articles.extend(result)
                except TimeoutError:
                    print(f"⏰ Scraper {i+1} timed out after 20s - skipping")
                except Exception as e:
                    print(f"❌ Scraper {i+1} error: {e}")
        
        # Process unprocessed articles
        try:
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
        except Exception as e:
            print(f"⚠️ Error processing unprocessed articles: {e}")
        
        # All articles are already filtered for unscraped ones, so no need to check classification
        articles_to_process = articles
        print(f"📊 Processing {len(articles_to_process)} new articles (already filtered for unscraped ones)")
        
        # Translate and truncate only new articles
        for art in articles_to_process:
            try:
                art.content = truncate_text(art.content, art.language, max_length=1000)  # Reduced from 2000 to 1000
            except Exception as e:
                print(f"⚠️ Error truncating article {art.url}: {e}")
        
        # Send translation progress update (non-blocking)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(send_progress_update("Translating articles...", 50))
        except:
            pass
        
        translated_articles = translate_articles_parallel(articles_to_process)
        
        # Store new articles only (already classified ones will be queried from database)
        agent = scrape_fresh_intel._agent_instance
        agent.current_session["scraped_articles"] = translated_articles
        
        print(f"✅ Fresh intel collected: {len(translated_articles)} articles")
        print(f"📊 Detailed breakdown:")
        print(f"  - Total raw articles collected: {len(articles)}")
        print(f"  - Articles to process: {len(articles_to_process)}")
        print(f"  - Final translated articles: {len(translated_articles)}")
        
        # Debug the first few articles for troubleshooting
        if translated_articles:
            print(f"🔍 Sample articles:")
            for i, art in enumerate(translated_articles[:3]):
                print(f"  {i+1}. {art.source}: {art.title[:50]}... ({art.language})")
        else:
            print("⚠️ No articles were collected - but continuing with empty list")
        
        return json.dumps({
            "success": True,
            "articles_collected": len(translated_articles),
            "status": "ready_for_classification"
        })
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        # Return success with empty list instead of failure to prevent infinite loops
        return json.dumps({
            "success": True,
            "articles_collected": 0,
            "status": "ready_for_classification",
            "note": f"Scraping failed but continuing: {str(e)}"
        })


# Removed unnecessary caching and background scraping functions to simplify the workflow

@tool
def present_results(output_format: str = "json") -> str:
    """Return final intelligence data as JSON for frontend consumption."""
    agent = present_results._agent_instance
    print(f"📋 Preparing intelligence data...")
    
    cves = agent.current_session.get("classified_cves", [])
    news = agent.current_session.get("classified_news", [])
    
    if not cves and not news:
        return json.dumps({
            "success": True,
            "cves_count": 0,
            "news_count": 0,
            "total_results": 0,
            "session_id": agent.current_session.get('session_id', 'Unknown'),
            "generated_at": datetime.now().isoformat(),
            "status": "No data found"
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
        "status": "Data available in session"
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

def translate_batch_openai(texts: list, source_lang: str) -> list:
    """Batch translate multiple texts in one API call for efficiency"""
    if source_lang == "en":
        return texts
    
    # Combine texts with separators
    combined_text = "\n---\n".join(texts[:5])  # Limit to 5 texts per batch
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"Translate the following {len(texts)} texts from {source_lang} to English. Separate each translation with '---'."},
                {"role": "user", "content": combined_text}
            ],
            max_tokens=500,
            temperature=0.1,
            timeout=15
        )
        result = response.choices[0].message.content.strip()
        return result.split("---")
    except Exception as e:
        print(f"Batch translation error: {e}")
        return texts  # Return original texts as fallback