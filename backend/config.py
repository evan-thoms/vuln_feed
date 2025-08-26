import os

# Environment-based configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Resource limits based on environment
if ENVIRONMENT == 'production':
    MAX_WORKERS = 10  # Full performance
    SCRAPING_TIMEOUT = 60
    ENABLE_CELERY = True
elif ENVIRONMENT == 'free_tier':
    MAX_WORKERS = 2   # Limited for free tier
    SCRAPING_TIMEOUT = 30
    ENABLE_CELERY = False
else:
    MAX_WORKERS = 5   # Development
    SCRAPING_TIMEOUT = 45
    ENABLE_CELERY = True

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///articles.db')

# Redis configuration (optional for free tier)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0') if ENABLE_CELERY else None

# Cost-optimized settings
CACHE_TTL = 3600  # 1 hour cache
BATCH_SIZE = 100  # Process in smaller batches
