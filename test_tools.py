# Import tools directly
from tools.scrape_tools import scrape_site
from tools.cve_tools import fetch_cves
from tools.translate_tools import translate_text
from tools.db_tools import initialize_db, list_recent_articles

# ---- Test Scrape Tool ----
print("🔍 Testing scrape_site()")
scraped = scrape_site(language="chinese")
print(f"Scraped {len(scraped)} items.")
print(scraped[:1])  # show one result

# ---- Test CVE Tool ----
print("\n🛡️ Testing fetch_cves()")
cves = fetch_cves()
print(f"Fetched {len(cves)} CVEs.")
print(cves[:1])  # show one result

# ---- Test Translate Tool ----
print("\n🌍 Testing translate_text()")
sample = "你好，世界！这是一个测试。"
translated = translate_text(text=sample, target_lang="en")
print(f"Original: {sample}")
print(f"Translated: {translated}")

# ---- Test DB Init ----
print("\n🗂️ Testing initialize_db()")
init_status = initialize_db()
print(init_status)

# ---- Test list_recent_articles() ----
print("\n📰 Testing list_recent_articles()")
recent = list_recent_articles(limit=3)
print(f"Fetched {len(recent)} articles from DB.")
for i, article in enumerate(recent, 1):
    print(f"{i}. {article.get('title', 'No title')} — {article.get('url')}")
