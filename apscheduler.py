from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

app = FastAPI()
scheduler = BackgroundScheduler()

def scrape_vulnerabilities():
    #scraping logic
    print("Running scraper...")

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(scrape_vulnerabilities, "interval", hours=24)
    scheduler.start()
