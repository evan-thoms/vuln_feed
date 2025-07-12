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
    url TEXT,
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
    url TEXT
);