from scrapers.chinese_scrape import ChineseScraper
# from scrapers.english_scrape import EnglishScraper
# from scrapers.russian_scrape import RussianScraper
# from aggregator import aggregate_vulnerabilities
# from reporter import generate_html_report
# from emailer import send_report_email

def main():
    print("Starting multilingual scrape...")

    all_vulns = []

    # Run each scraper
    # all_vulns.extend(EnglishScraper().scrape_all())
    all_vulns.extend(ChineseScraper().scrape_freebuf())
    # all_vulns.extend(RussianScraper().scrape_xakep())

    print("VULNS", all_vulns)
    return
    # Combine, dedupe, prioritize
    top_vulns = aggregate_vulnerabilities(all_vulns)

    # Build report
    # html_report = generate_html_report(top_vulns)

    # Email
    # send_report_email(html_report, ...)

    print(f"Done. Found {len(top_vulns)} high-priority vulnerabilities.")

if __name__ == "__main__":
    main()
