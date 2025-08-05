import json
from pathlib import Path
from datetime import datetime
from tools.tools import (
    scrape_and_process_articles,
    classify_articles,
    filter_and_rank_items,
    format_and_present_results,
)
from models import QueryParams, Vulnerability, NewsItem

def load_json_file(path, cls):
    """Helper to load JSON and convert to dataclass instances"""
    raw = json.loads(Path(path).read_text())
    return [cls(**item) for item in raw]

def test_pipeline():
    # 🔹 Load inputs
    cves = load_json_file("cves.json", Vulnerability)
    news_items = load_json_file("newsitems.json", NewsItem)

    # 🔧 Create QueryParams
    params = QueryParams(
        content_type="all",            # "cve", "news", or "all"
        severity=["High", "Critical"], # Optional severity filter
        days_back=7,                   # Lookback window
        max_results=5,                 # Max items to show
        output_format="console",       # or "email"
        email_address=None             # optional
    )

    # ⚙️ Run filter & rank
    print("\n===== TESTING: filter_and_rank_items =====")
    result = filter_and_rank_items.invoke({
        "cves": cves,
        "news_items": news_items,
        "params": params
    })
    print(f"✅ Filtered down to {len(result)} items")

    # 🖨️ Format final output
    print("\n===== TESTING: format_and_present_results =====")
    output = format_and_present_results.invoke({
        "results": result,
        "params": params
    })

    print("\n" + "="*80 + "\n")
    print("✅ Final Output:\n")
    print(output)


if __name__ == "__main__":
    test_pipeline()
