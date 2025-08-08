import sqlite3
from datetime import datetime, timedelta

DB_PATH = "articles.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open("schema.sql", "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def is_article_scraped(link):
    print("Checking if ", link, " is scraped ")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 from raw_articles WHERE url = ?", (link,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_raw_article(article):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO raw_articles (source, url, title, title_translated, content, content_translated, language, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (article.source, article.url, article.title, article.title_translated, article.content, article.content_translated, article.language, article.scraped_at))
        conn.commit()
    finally:
        conn.close()

def get_unprocessed_articles():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM raw_articles WHERE processed = 0")
    rows = cursor.fetchall()
    conn.close()
    return rows

def mark_as_processed(raw_article_id):
    print("Marked as processed: ", raw_article_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE raw_articles SET processed = 1 WHERE url = ?", (raw_article_id,))
    conn.commit()
    conn.close()

def insert_cve(cve):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cves (cve_id, title, title_translated, summary, severity, cvss_score, published_date, original_language, source, url, intrigue, affected_products)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

def insert_newsitem( news):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO newsitems (title, title_translated, summary, published_date, source, url, intrigue)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        news.title,
        news.title_translated,
        news.summary,
        news.published_date,
        news.source,
        news.url,
        news.intrigue
    ))
    conn.commit()
    conn.close()

def get_cves_by_filters(severity_filter=None, after_date=None, limit=50):
    """Get CVEs with filters for agent decision making"""
    conn = sqlite3.connect(DB_PATH)
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
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
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
            affected_products=json.loads(row[12]) if row[12] else []
        )
        vulnerabilities.append(vuln)
    
    return vulnerabilities

def get_news_by_filters(after_date=None, limit=50):
    """Get news items with filters"""
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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