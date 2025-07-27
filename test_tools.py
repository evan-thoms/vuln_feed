from tools.tools import (
    scrape_and_process_articles,
    classify_articles,
    filter_and_rank_items,
    format_and_present_results,
)
from models import QueryParams

# Step 0: Prepare QueryParams
params = QueryParams(
    content_type="both",  # or "cve", "news"
    severity="high",      # optional
    days_back=7,
    max_results=5,
    output_format="display",
    email_address=None,
)

# Step 1: Scrape & Translate
print("===== TESTING: scrape_and_process_articles =====")
articles = scrape_and_process_articles.invoke(params)
print(f"✅ Got {len(articles)} articles")
print("Sample article title:", articles[0].title_translated)

# Step 2: Classify
print("\n===== TESTING: classify_articles =====")
cves, news = classify_articles.invoke({"articles": articles, "params": params})
print(f"✅ Classified {len(cves)} CVEs and {len(news)} news articles")
if cves:
    print("Sample CVE title:", cves[0].title_translated)

# Step 3: Filter & Rank
print("\n===== TESTING: filter_and_rank_items =====")
final_items = filter_and_rank_items.invoke({"cves": cves, "news_items": news, "params": params})
print(f"✅ Filtered down to {len(final_items)} items")

# Step 4: Format Output
print("\n===== TESTING: format_and_present_results =====")
formatted = format_and_present_results.invoke({"items": final_items, "params": params})
print("✅ Final Output:\n")
print(formatted)
