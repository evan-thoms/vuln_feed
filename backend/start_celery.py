#!/usr/bin/env python3
"""
Production Celery startup script
Run this to start the Celery worker and beat scheduler
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def start_celery_worker():
    """Start Celery worker"""
    print("🚀 Starting Celery worker...")
    
    # Set environment variables for production
    os.environ.setdefault('CELERY_CONFIG_MODULE', 'celery.celery_config')
    
    # Start worker
    worker_cmd = [
        'celery', '-A', 'celery.celery_tasks', 'worker',
        '--loglevel=info',
        '--concurrency=2',  # Limit concurrency for production
        '--max-tasks-per-child=1000',  # Restart worker after 1000 tasks
        '--without-gossip',  # Disable gossip for single worker
        '--without-mingle',  # Disable mingle for single worker
        '--without-heartbeat'  # Disable heartbeat for single worker
    ]
    
    try:
        subprocess.run(worker_cmd, check=True)
    except KeyboardInterrupt:
        print("🛑 Celery worker stopped")
    except Exception as e:
        print(f"❌ Failed to start Celery worker: {e}")

def start_celery_beat():
    """Start Celery beat scheduler"""
    print("⏰ Starting Celery beat scheduler...")
    
    # Set environment variables for production
    os.environ.setdefault('CELERY_CONFIG_MODULE', 'celery.celery_config')
    
    # Start beat
    beat_cmd = [
        'celery', '-A', 'celery.celery_tasks', 'beat',
        '--loglevel=info',
        '--scheduler=celery.beat.PersistentScheduler',  # Persistent scheduler
        '--pidfile=celerybeat.pid'  # PID file for process management
    ]
    
    try:
        subprocess.run(beat_cmd, check=True)
    except KeyboardInterrupt:
        print("🛑 Celery beat stopped")
    except Exception as e:
        print(f"❌ Failed to start Celery beat: {e}")

def start_redis():
    """Start Redis if not running"""
    print("🔍 Checking Redis...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print(f"⚠️ Redis not available: {e}")
        print("💡 Please start Redis: brew services start redis (macOS) or redis-server (Linux)")
        return False

if __name__ == "__main__":
    print("🎯 CyberIntel Production Celery Manager")
    print("=" * 50)
    
    # Check Redis
    if not start_redis():
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "worker":
            start_celery_worker()
        elif command == "beat":
            start_celery_beat()
        elif command == "both":
            print("🔄 Starting both worker and beat...")
            # Start beat in background
            import threading
            beat_thread = threading.Thread(target=start_celery_beat)
            beat_thread.daemon = True
            beat_thread.start()
            
            # Start worker in foreground
            time.sleep(2)  # Give beat time to start
            start_celery_worker()
        else:
            print("Usage: python start_celery.py [worker|beat|both]")
    else:
        print("Usage: python start_celery.py [worker|beat|both]")
        print("  worker: Start Celery worker only")
        print("  beat: Start Celery beat scheduler only")
        print("  both: Start both worker and beat")
