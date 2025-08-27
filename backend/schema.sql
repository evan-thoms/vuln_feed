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
    processed INTEGER DEFAULT 0,
    session_id VARCHAR(50) DEFAULT 'unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    affected_products TEXT,
    session_id VARCHAR(50) DEFAULT 'unknown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
    intrigue REAL,
    session_id VARCHAR(50) DEFAULT 'unknown',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_cves_session_id ON cves(session_id);
CREATE INDEX IF NOT EXISTS idx_cves_created_at ON cves(created_at);
CREATE INDEX IF NOT EXISTS idx_news_session_id ON newsitems(session_id);
CREATE INDEX IF NOT EXISTS idx_news_created_at ON newsitems(created_at);
CREATE INDEX IF NOT EXISTS idx_raw_session_id ON raw_articles(session_id);
CREATE INDEX IF NOT EXISTS idx_raw_created_at ON raw_articles(created_at);