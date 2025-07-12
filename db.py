import sqlite3
from datetime import datetime

DB_PATH = "articles.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open("schema.sql", "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def is_article_scraped(link):
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE raw_articles SET processed = 1 WHERE id = ?", (raw_article_id,))
    conn.commit()
    conn.close()

def insert_cve(cve):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cves (cve_id, title, title_translated, summary, severity, cvss_score, published_date, original_language, source, url, affected_products)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ",".join(cve.affected_products)
    ))
    conn.commit()
    conn.close()

def insert_newsitem( news):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO newsitems (title, title_translated, summary, published_date, source, url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        news.title,
        news.title_translated,
        news.summary,
        news.published_date,
        news.source,
        news.url
    ))
    conn.commit()
    conn.close()