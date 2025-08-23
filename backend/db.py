import sqlite3
from datetime import datetime, timedelta
import json
from models import Vulnerability, NewsItem
import os
import asyncio

# Database configuration - supports both SQLite and PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///articles.db')

def get_db_path():
    """Get the database path for use in Celery tasks"""
    if DATABASE_URL.startswith('sqlite'):
        # Use /tmp directory on Render for writable SQLite database
        db_name = DATABASE_URL.replace('sqlite:///', '')
        if db_name == 'articles.db':
            return '/tmp/articles.db'
        return db_name
    return DATABASE_URL

def get_connection():
    """Get database connection - using SQLite for now to avoid compatibility issues"""
    return sqlite3.connect(get_db_path())

def init_db():
    """Initialize database with proper schema"""
    conn = sqlite3.connect(get_db_path())
    
    # Create tables directly instead of reading from schema.sql
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS raw_articles (
            id INTEGER PRIMARY KEY,
            source TEXT,
            url TEXT UNIQUE,
            title TEXT,
            title_translated TEXT,
            content TEXT,
            content_translated TEXT,
            language TEXT,
            scraped_at TEXT,
            published_date TEXT,
            processed INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS cves (
            id INTEGER PRIMARY KEY,
            cve_id TEXT UNIQUE,
            title TEXT,
            title_translated TEXT,
            summary TEXT,
            severity TEXT,
            cvss_score REAL,
            published_date TEXT,
            original_language TEXT,
            source TEXT,
            url TEXT,
            intrigue REAL,
            affected_products TEXT
        );
        
        CREATE TABLE IF NOT EXISTS newsitems (
            id INTEGER PRIMARY KEY,
            title TEXT,
            title_translated TEXT,
            summary TEXT,
            published_date TEXT,
            original_language TEXT,
            source TEXT,
            url TEXT UNIQUE,
            intrigue REAL
        );
    """)
    conn.commit()
    conn.close()

def is_article_scraped(link):
    print("Checking if ", link, " is scraped ")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 from raw_articles WHERE url = %s", (link,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_raw_article(article):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO raw_articles (source, url, title, title_translated, content, content_translated, language, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING
        """, (article.source, article.url, article.title, article.title_translated, article.content, article.content_translated, article.language, article.scraped_at))
        conn.commit()
    finally:
        conn.close()

def get_unprocessed_articles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM raw_articles WHERE processed = FALSE")
    rows = cursor.fetchall()
    conn.close()
    return rows

def mark_as_processed(raw_article_id):
    print("Marked as processed: ", raw_article_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE raw_articles SET processed = TRUE WHERE url = %s", (raw_article_id,))
    conn.commit()
    conn.close()

def insert_cve(cve):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cves (cve_id, title, title_translated, summary, severity, cvss_score, published_date, original_language, source, url, intrigue, affected_products)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (cve_id) DO NOTHING
    """, (
        cve.cve_id,
        cve.title,
        cve.title_translated,
        cve.summary,
        cve.severity,
        cve.cvss_score,
        cve.published_date,
        cve.original_language,
        cve.source,
        cve.url,
        cve.intrigue,
        ",".join(cve.affected_products)
    ))
    conn.commit()
    conn.close()

def insert_newsitem(news):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO newsitems (title, title_translated, summary, published_date, original_language, source, url, intrigue)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING
    """, (
        news.title,
        news.title_translated,
        news.summary,
        news.published_date,
        news.original_language,
        news.source,
        news.url,
        news.intrigue
    ))
    conn.commit()
    conn.close()

def get_cves_by_filters(severity_filter=None, after_date=None, limit=50):
    """Get CVEs with filters for agent decision making"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM cves WHERE 1=1"
        params = []
        
        if severity_filter:
            if isinstance(severity_filter, list):
                placeholders = ",".join("?" * len(severity_filter))
                query += f" AND UPPER(severity) IN ({placeholders})"
                params.extend([s.upper() for s in severity_filter])
            else:
                query += " AND UPPER(severity) = ?"
                params.append(severity_filter.upper())
        
        if after_date:
            query += " AND published_date >= ?"
            params.append(after_date.isoformat())
        
        query += " ORDER BY (cvss_score * 0.6 + intrigue * 0.4) DESC LIMIT ?"
        params.append(limit)
        print(f"🔍 DEBUG: SQL QUERY: {query}")
        print(f"🔍 DEBUG: PARAMS: {params}")
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        print(f"🔍 DEBUG: DB rows fetched: {len(rows)} rows")
        conn.close()
        
        # Convert to Vulnerability objects
        vulnerabilities = []
        for row in rows:
            vuln = Vulnerability(
                cve_id=row[1],
                title=row[2], 
                title_translated=row[3],
                summary=row[4],
                severity=row[5],
                cvss_score=float(row[6]),
                published_date=datetime.fromisoformat(row[7]),
                original_language=row[8],
                source=row[9],
                url=row[10],
                intrigue=float(row[11]),
                affected_products=row[12].split(',') if row[12] else []
            )
            vulnerabilities.append(vuln)
        
        return vulnerabilities
    except Exception as e:
        print(f"❌ CVE Database error: {e}")
        return []  # Return empty list instead of None

def get_news_by_filters(after_date=None, limit=50):
    """Get news items with filters"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM newsitems WHERE 1=1"
    params = []
    
    if after_date:
        query += " AND published_date >= ?"
        params.append(after_date.isoformat())
    
    query += " ORDER BY intrigue DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Convert to NewsItem objects
    news_items = []
    for row in rows:
        news = NewsItem(
            title=row[1],
            title_translated=row[2], 
            summary=row[3],
            published_date=datetime.fromisoformat(row[4]),
            original_language=row[5],
            source=row[6],
            url=row[7],
            intrigue=float(row[8])
        )
        news_items.append(news)
    
    return news_items

def get_last_scrape_time():
    """Get last scrape time by source for freshness calculation"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get most recent scrape time by source
    query = """
    SELECT source, MAX(scraped_at) as last_scrape
    FROM raw_articles 
    GROUP BY source
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    last_scrapes = {}
    for source, last_scrape_str in rows:
        if last_scrape_str:
            try:
                last_scrapes[source.lower()] = datetime.fromisoformat(last_scrape_str)
            except ValueError:
                last_scrapes[source.lower()] = None
    
    return last_scrapes

def get_data_statistics():
    """Get overall database statistics for agent insights"""
    conn = get_connection()
    cursor = conn.cursor()
    
    stats = {}
    
    # CVE stats
    cursor.execute("SELECT COUNT(*), AVG(cvss_score), AVG(intrigue) FROM cves")
    cve_stats = cursor.fetchone()
    stats["cves"] = {
        "total": cve_stats[0],
        "avg_cvss": round(cve_stats[1] or 0, 2),
        "avg_intrigue": round(cve_stats[2] or 0, 2)
    }
    
    # News stats
    cursor.execute("SELECT COUNT(*), AVG(intrigue) FROM newsitems")
    news_stats = cursor.fetchone()
    stats["news"] = {
        "total": news_stats[0],
        "avg_intrigue": round(news_stats[1] or 0, 2)
    }
    
    # Recent activity (last 24 hours)
    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
    cursor.execute("SELECT COUNT(*) FROM raw_articles WHERE scraped_at >= ?", (yesterday,))
    stats["recent_articles"] = cursor.fetchone()[0]
    
    conn.close()
    return stats

def record_scraping_session(sources_scraped, articles_found, triggered_by="agent"):
    """Record scraping session for agent learning"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create scraping_sessions table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scraping_sessions (
        id INTEGER PRIMARY KEY,
        started_at TEXT,
        sources_scraped TEXT,
        articles_found INTEGER,
        triggered_by TEXT
    )
    """)
    
    cursor.execute("""
    INSERT INTO scraping_sessions (started_at, sources_scraped, articles_found, triggered_by)
    VALUES (?, ?, ?, ?)
    """, (datetime.now().isoformat(), json.dumps(sources_scraped), articles_found, triggered_by))
    
    conn.commit()
    conn.close()

def is_article_classified(url):
    """Check if an article has already been classified (exists in cves or newsitems)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check both cves and newsitems tables
    cursor.execute("SELECT 1 FROM cves WHERE url = ?", (url,))
    cve_exists = cursor.fetchone()
    
    cursor.execute("SELECT 1 FROM newsitems WHERE url = ?", (url,))
    news_exists = cursor.fetchone()
    
    conn.close()
    return cve_exists is not None or news_exists is not None

def get_classified_article(url):
    """Get already classified article data by URL"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check cves table first
    cursor.execute("SELECT * FROM cves WHERE url = ?", (url,))
    cve_row = cursor.fetchone()
    
    if cve_row:
        conn.close()
        return {
            "type": "CVE",
            "data": {
                "cve_id": cve_row[1],
                "title": cve_row[2],
                "title_translated": cve_row[3],
                "summary": cve_row[4],
                "severity": cve_row[5],
                "cvss_score": float(cve_row[6]),
                "published_date": datetime.fromisoformat(cve_row[7]),
                "original_language": cve_row[8],
                "source": cve_row[9],
                "url": cve_row[10],
                "intrigue": float(cve_row[11]),
                "affected_products": cve_row[12].split(',') if cve_row[12] else []
            }
        }
    
    # Check newsitems table
    cursor.execute("SELECT * FROM newsitems WHERE url = ?", (url,))
    news_row = cursor.fetchone()
    
    if news_row:
        conn.close()
        return {
            "type": "News",
            "data": {
                "title": news_row[1],
                "title_translated": news_row[2],
                "summary": news_row[3],
                "published_date": datetime.fromisoformat(news_row[4]),
                "original_language": news_row[5],
                "source": news_row[6],
                "url": news_row[7],
                "intrigue": float(news_row[8])
            }
        }
    
    conn.close()
    return None

def get_data_freshness_info():
    """Get information about data freshness for user feedback"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get latest scrape times by source
    cursor.execute("""
        SELECT source, MAX(scraped_at) as last_scrape, COUNT(*) as total_articles
        FROM raw_articles 
        GROUP BY source
    """)
    scrape_stats = cursor.fetchall()
    
    # Get latest classification times
    cursor.execute("""
        SELECT 'cves' as type, MAX(published_date) as last_classified, COUNT(*) as total
        FROM cves
        UNION ALL
        SELECT 'news' as type, MAX(published_date) as last_classified, COUNT(*) as total
        FROM newsitems
    """)
    classification_stats = cursor.fetchall()
    
    conn.close()
    
    freshness_info = {
        "scraping": {},
        "classification": {}
    }
    
    for source, last_scrape, total in scrape_stats:
        if last_scrape:
            try:
                last_scrape_dt = datetime.fromisoformat(last_scrape)
                # Handle timezone-aware datetimes
                if last_scrape_dt.tzinfo is not None:
                    last_scrape_dt = last_scrape_dt.replace(tzinfo=None)
                hours_ago = (datetime.now() - last_scrape_dt).total_seconds() / 3600
                freshness_info["scraping"][source] = {
                    "last_scrape": last_scrape_dt,
                    "hours_ago": round(hours_ago, 1),
                    "total_articles": total
                }
            except ValueError:
                pass
    
    for type_name, last_classified, total in classification_stats:
        if last_classified:
            try:
                last_classified_dt = datetime.fromisoformat(last_classified)
                # Handle timezone-aware datetimes
                if last_classified_dt.tzinfo is not None:
                    last_classified_dt = last_classified_dt.replace(tzinfo=None)
                hours_ago = (datetime.now() - last_classified_dt).total_seconds() / 3600
                freshness_info["classification"][type_name] = {
                    "last_classified": last_classified_dt,
                    "hours_ago": round(hours_ago, 1),
                    "total_items": total
                }
            except ValueError:
                pass
    
    return freshness_info

def get_all_classified_data_with_freshness(limit=50):
    """Get all classified data (CVEs and News) with freshness information for frontend"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get CVEs
    cursor.execute("""
        SELECT * FROM cves 
        ORDER BY (cvss_score * 0.6 + intrigue * 0.4) DESC 
        LIMIT ?
    """, (limit,))
    cve_rows = cursor.fetchall()
    
    # Get News
    cursor.execute("""
        SELECT * FROM newsitems 
        ORDER BY intrigue DESC 
        LIMIT ?
    """, (limit,))
    news_rows = cursor.fetchall()
    
    # Get freshness info
    cursor.execute("""
        SELECT MAX(scraped_at) as last_scrape, COUNT(*) as total_articles
        FROM raw_articles
    """)
    scrape_info = cursor.fetchone()
    
    cursor.execute("""
        SELECT MAX(published_date) as last_cve, COUNT(*) as total_cves
        FROM cves
    """)
    cve_info = cursor.fetchone()
    
    cursor.execute("""
        SELECT MAX(published_date) as last_news, COUNT(*) as total_news
        FROM newsitems
    """)
    news_info = cursor.fetchone()
    
    conn.close()
    
    # Convert to objects
    cves = []
    for row in cve_rows:
        vuln = Vulnerability(
            cve_id=row[1],
            title=row[2], 
            title_translated=row[3],
            summary=row[4],
            severity=row[5],
            cvss_score=float(row[6]),
            published_date=datetime.fromisoformat(row[7]),
            original_language=row[8],
            source=row[9],
            url=row[10],
            intrigue=float(row[11]),
            affected_products=row[12].split(',') if row[12] else []
        )
        cves.append(vuln)
    
    news_items = []
    for row in news_rows:
        news = NewsItem(
            title=row[1],
            title_translated=row[2], 
            summary=row[3],
            published_date=datetime.fromisoformat(row[4]),
            original_language=row[5],
            source=row[6],
            url=row[7],
            intrigue=float(row[8])
        )
        news_items.append(news)
    
    # Calculate freshness
    freshness = {
        "last_scrape": None,
        "last_cve": None,
        "last_news": None,
        "total_articles": 0,
        "total_cves": 0,
        "total_news": 0
    }
    
    if scrape_info[0]:
        try:
            freshness["last_scrape"] = datetime.fromisoformat(scrape_info[0])
            freshness["total_articles"] = scrape_info[1]
        except ValueError:
            pass
    
    if cve_info[0]:
        try:
            freshness["last_cve"] = datetime.fromisoformat(cve_info[0])
            freshness["total_cves"] = cve_info[1]
        except ValueError:
            pass
    
    if news_info[0]:
        try:
            freshness["last_news"] = datetime.fromisoformat(news_info[0])
            freshness["total_news"] = news_info[1]
        except ValueError:
            pass
    
    return {
        "cves": cves,
        "news": news_items,
        "freshness": freshness
    }

if __name__ == "__main__":
    # Initialize DB first if needed
    init_db()
    
    # Test the function
    stats = get_data_statistics()
    print("Database Statistics:")
    print(f"CVEs: {stats['cves']}")
    print(f"News: {stats['news']}")
    print(f"Recent articles (24h): {stats['recent_articles']}")