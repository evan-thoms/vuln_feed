from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from agent import scrape_and_store_articles

scheduler = BackgroundScheduler()

def scheduled_job():
    print(f"Scheduled scraping at {datetime.now()}")
    scrape_and_store_articles() 

def start_scheduler():
    scheduler.add_job(scheduled_job, 'interval', hours=24)
    scheduler.start()
