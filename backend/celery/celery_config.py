broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Beat schedule for periodic tasks
beat_schedule = {
    'intelligent-scraping': {
        'task': 'celery_tasks.intelligent_scraping_task',
        'schedule': 60.0 * 60 * 6,  # Every 6 hours
    },
    'data-cleanup': {
        'task': 'celery_tasks.cleanup_old_data_task',
        'schedule': 60.0 * 60 * 24,  # Daily
    },
    'trend-analysis': {
        'task': 'celery_tasks.trend_analysis_task',
        'schedule': 60.0 * 60 * 12,  # Every 12 hours
    }
}