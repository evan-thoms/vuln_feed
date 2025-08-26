import sqlite3
from datetime import datetime, timedelta
import json
from models import Vulnerability, NewsItem
import os
import asyncio

# Database configuration - supports both SQLite and PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///articles.db')

def get_placeholder():
    """Get the correct SQL placeholder based on database type"""
    return "%s" if DATABASE_URL.startswith('postgresql') else "?"

def get_ignore_clause():
    """Get the correct INSERT IGNORE clause based on database type"""
    if DATABASE_URL.startswith('postgresql'):
        return "ON CONFLICT (url) DO NOTHING"
    else:
        return "OR IGNORE"

def get_db_path():
    """Get the database path for use in Celery tasks"""
    if DATABASE_URL.startswith('sqlite'):
        # Use persistent directory on Render
        if os.getenv('RENDER'):
            # Try multiple writable directories on Render
            possible_paths = [
                '/tmp/articles.db',
                '/opt/render/project/src/articles.db',
                os.path.join(os.getcwd(), 'articles.db')
            ]
            for path in possible_paths:
                try:
                    # Test if we can write to this directory
                    test_path = path.replace('articles.db', 'test.db')
                    test_conn = sqlite3.connect(test_path)
                    test_conn.close()
                    os.remove(test_path)  # Clean up test file
                    print(f"✅ Using database path: {path}")
                    return path
                except (sqlite3.OperationalError, PermissionError, OSError):
                    continue
            # If all fail, fall back to in-memory
            print("⚠️ All file paths failed, using in-memory database")
            return ':memory:'
        db_name = DATABASE_URL.replace('sqlite:///', '')
        return os.path.join(os.getcwd(), db_name)
    return DATABASE_URL

def _create_tables(conn):
    """Create database tables using schema.sql"""
    import os
    
    # Find schema.sql file - check both current directory and backend directory
    schema_paths = [
        "schema.sql",
        "backend/schema.sql",
        os.path.join(os.path.dirname(__file__), "schema.sql"),
        os.path.join(os.path.dirname(__file__), "..", "schema.sql")
    ]
    
    for schema_path in schema_paths:
        if os.path.exists(schema_path):
            with open(schema_path, "r") as f:
                conn.executescript(f.read())
            conn.commit()
            return
    
    # Fallback if schema.sql not found
    print("⚠️ schema.sql not found, using inline table creation")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS raw_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            title TEXT,
            title_translated TEXT,
            url TEXT UNIQUE,
            content TEXT,
            content_translated TEXT,
            language TEXT,
            scraped_at DATETIME,
            published_date DATETIME,
            processed INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS cves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cve_id TEXT,
            title TEXT,
            title_translated TEXT,
            summary TEXT,
            severity TEXT,
            cvss_score REAL,
            published_date DATETIME,
            original_language TEXT,
            source TEXT,
            url TEXT UNIQUE,
            intrigue REAL,
            affected_products TEXT
        );
        
        CREATE TABLE IF NOT EXISTS newsitems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            title_translated TEXT,
            summary TEXT,
            published_date DATETIME,
            original_language TEXT,
            source TEXT,
            url TEXT UNIQUE,
            intrigue REAL
        );
    """)
    conn.commit()

def get_connection():
    """Get database connection - supports both SQLite and PostgreSQL"""
    if DATABASE_URL.startswith('postgresql'):
        # PostgreSQL connection (Supabase)
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # print(f"🔗 Connecting to PostgreSQL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'Supabase'}")
            
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            
            # Test the connection
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            # print(f"✅ PostgreSQL connected successfully: {version[0] if version else 'Unknown version'}")
            
            # Check if tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('raw_articles', 'cves', 'newsitems')
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            # print(f"📊 Existing tables: {existing_tables}")
            
            # Create tables if they don't exist
            if not existing_tables:
                print("🔨 Creating PostgreSQL tables...")
                _create_postgresql_tables(conn)
            
            return conn
            
        except ImportError:
            print("❌ psycopg2 not installed, falling back to SQLite")
            return _get_sqlite_connection()
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            print("⚠️ Falling back to SQLite")
            return _get_sqlite_connection()
    else:
        # SQLite connection (fallback)
        return _get_sqlite_connection()

def _get_sqlite_connection():
    """Get SQLite connection with fallback logic"""
    try:
        conn = sqlite3.connect(get_db_path())
        # Check if tables exist, if not create them
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='raw_articles'")
        if not cursor.fetchone():
            _create_tables(conn)
        return conn
    except sqlite3.OperationalError:
        # If file-based database fails, fall back to in-memory
        print("⚠️ File-based database failed, using in-memory database")
        conn = sqlite3.connect(':memory:')
        _create_tables(conn)
        return conn

def _create_postgresql_tables(conn):
    """Create PostgreSQL tables for Supabase"""
    cursor = conn.cursor()
    
    # Create raw_articles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_articles (
            id SERIAL PRIMARY KEY,
            source TEXT,
            title TEXT,
            title_translated TEXT,
            url TEXT UNIQUE,
            content TEXT,
            content_translated TEXT,
            language TEXT,
            scraped_at TIMESTAMP,
            published_date TIMESTAMP,
            processed INTEGER DEFAULT 0
        );
    """)
    
    # Create cves table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cves (
            id SERIAL PRIMARY KEY,
            cve_id TEXT,
            title TEXT,
            title_translated TEXT,
            summary TEXT,
            severity TEXT,
            cvss_score REAL,
            published_date TIMESTAMP,
            original_language TEXT,
            source TEXT,
            url TEXT UNIQUE,
            intrigue REAL,
            affected_products TEXT
        );
    """)
    
    # Create newsitems table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS newsitems (
            id SERIAL PRIMARY KEY,
            title TEXT,
            title_translated TEXT,
            summary TEXT,
            published_date TIMESTAMP,
            original_language TEXT,
            source TEXT,
            url TEXT UNIQUE,
            intrigue REAL
        );
    """)
    
    conn.commit()
    print("✅ PostgreSQL tables created successfully")

def init_db():
    """Initialize database with proper schema"""
    # Tables are now created automatically by get_connection()
    conn = get_connection()
    conn.close()

def is_article_scraped(link):
    print("Checking if ", link, " is scraped ")
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = get_placeholder()
    cursor.execute(f"SELECT 1 from raw_articles WHERE url = {placeholder}", (link,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_raw_article(article):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        placeholder = get_placeholder()
        ignore_clause = get_ignore_clause()
        cursor.execute(f"""
            INSERT {ignore_clause} INTO raw_articles (source, url, title, title_translated, content, content_translated, language, scraped_at)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """, (article.source, article.url, article.title, article.title_translated, article.content, article.content_translated, article.language, article.scraped_at))
        conn.commit()
    finally:
        conn.close()

def get_unprocessed_articles():
    conn = get_connection()
    cursor = conn.cursor()
    # Fix for PostgreSQL: use integer comparison instead of boolean
    if DATABASE_URL.startswith('postgresql'):
        cursor.execute("SELECT * FROM raw_articles WHERE processed = 0")
    else:
        cursor.execute("SELECT * FROM raw_articles WHERE processed = FALSE")
    rows = cursor.fetchall()
    conn.close()
    return rows

def mark_as_processed(raw_article_id):
    print("Marked as processed: ", raw_article_id)
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = get_placeholder()
    cursor.execute(f"UPDATE raw_articles SET processed = {placeholder} WHERE url = {placeholder}", (1, raw_article_id,))
    conn.commit()
    conn.close()

def insert_cve(cve):
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = get_placeholder()
    ignore_clause = get_ignore_clause()
    cursor.execute(f"""
        INSERT {ignore_clause} INTO cves (cve_id, title, title_translated, summary, severity, cvss_score, published_date, original_language, source, url, intrigue, affected_products)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
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
    placeholder = get_placeholder()
    ignore_clause = get_ignore_clause()
    cursor.execute(f"""
        INSERT {ignore_clause} INTO newsitems (title, title_translated, summary, published_date, original_language, source, url, intrigue)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
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
        
        placeholder = get_placeholder()
        
        if severity_filter:
            if isinstance(severity_filter, list):
                # Fix: Use proper placeholder formatting for PostgreSQL
                if DATABASE_URL.startswith('postgresql'):
                    placeholders = ",".join(["%s"] * len(severity_filter))
                else:
                    placeholders = ",".join(["?"] * len(severity_filter))
                query += f" AND UPPER(severity) IN ({placeholders})"
                params.extend([s.upper() for s in severity_filter])
            else:
                query += f" AND UPPER(severity) = {placeholder}"
                params.append(severity_filter.upper())
        
        if after_date:
            query += f" AND published_date >= {placeholder}"
            params.append(after_date.isoformat())
        
        query += f" ORDER BY (cvss_score * 0.6 + intrigue * 0.4) DESC LIMIT {placeholder}"
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
    placeholder = get_placeholder()
    
    if after_date:
        query += f" AND published_date >= {placeholder}"
        params.append(after_date.isoformat())
    
    query += f" ORDER BY intrigue DESC LIMIT {placeholder}"
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

def get_cache_freshness():
    """Check how fresh the cached data is"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get the most recent scrape time
    cursor.execute("""
        SELECT MAX(scraped_at) as last_scrape 
        FROM raw_articles 
        WHERE scraped_at IS NOT NULL
    """)
    result = cursor.fetchone()
    last_scrape = result[0] if result and result[0] else None
    
    # Get total counts
    cursor.execute("SELECT COUNT(*) FROM cves")
    cve_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM newsitems") 
    news_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM raw_articles")
    total_articles = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "last_scrape": last_scrape,
        "cve_count": cve_count,
        "news_count": news_count,
        "total_articles": total_articles,
        "is_fresh": is_data_fresh(last_scrape)
    }

def is_data_fresh(last_scrape, max_age_hours=12):
    """Check if data is fresh enough (within max_age_hours)"""
    if not last_scrape:
        return False
    
    if isinstance(last_scrape, str):
        last_scrape = datetime.fromisoformat(last_scrape.replace('Z', '+00:00'))
    
    age_hours = (datetime.now() - last_scrape).total_seconds() / 3600
    return age_hours < max_age_hours

def cleanup_old_data(weeks_old=3):
    """Delete data older than specified weeks"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cutoff_date = datetime.now() - timedelta(weeks=weeks_old)
    
    # Delete old CVEs
    cursor.execute("DELETE FROM cves WHERE published_date < ?", (cutoff_date,))
    cves_deleted = cursor.rowcount
    
    # Delete old news
    cursor.execute("DELETE FROM newsitems WHERE published_date < ?", (cutoff_date,))
    news_deleted = cursor.rowcount
    
    # Delete old raw articles
    cursor.execute("DELETE FROM raw_articles WHERE scraped_at < ?", (cutoff_date,))
    articles_deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    return {
        "cves_deleted": cves_deleted,
        "news_deleted": news_deleted,
        "articles_deleted": articles_deleted
    }

def get_cached_intelligence(content_type="both", severity=None, days_back=7, max_results=10):
    """Get intelligence from cache with smart filtering"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if severity is None:
        severity_list = None
    elif isinstance(severity, str):
        severity_list = [severity.upper()]
    elif isinstance(severity, list):
        severity_list = [s.upper() for s in severity] if severity else None
    
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    cves = []
    news = []
    
    if content_type in ["cve", "both"]:
        if severity_list:
            placeholders = ','.join(['?' for _ in severity_list])
            cursor.execute(f"""
                SELECT * FROM cves 
                WHERE published_date >= ? 
                AND UPPER(severity) IN ({placeholders})
                ORDER BY (cvss_score * 0.6 + intrigue * 0.4) DESC 
                LIMIT ?
            """, [cutoff_date] + severity_list + [max_results])
        else:
            cursor.execute("""
                SELECT * FROM cves 
                WHERE published_date >= ? 
                ORDER BY (cvss_score * 0.6 + intrigue * 0.4) DESC 
                LIMIT ?
            """, (cutoff_date, max_results))
        
        cves = cursor.fetchall()
    
    if content_type in ["news", "both"]:
        news_limit = max_results - len(cves) if content_type == "both" else max_results
        cursor.execute("""
            SELECT * FROM newsitems 
            WHERE published_date >= ? 
            ORDER BY intrigue DESC 
            LIMIT ?
        """, (cutoff_date, news_limit))
        
        news = cursor.fetchall()
    
    conn.close()
    
    return {
        "cves": cves,
        "news": news,
        "total_found": len(cves) + len(news)
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