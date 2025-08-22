import os

# Use environment variables for production, fallback to local for development
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Beat schedule for periodic tasks
beat_schedule = {
    'weekly-intelligence-gathering': {
        'task': 'celery_tasks.weekly_intelligence_task',
        'schedule': 60.0 * 60 * 24 * 7,  # Every 7 days (weekly)
    },
    'data-cleanup': {
        'task': 'celery_tasks.cleanup_old_data_task',
        'schedule': 60.0 * 60 * 24 * 7,  # Weekly cleanup
    }
}