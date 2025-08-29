#!/usr/bin/env python3
"""
Test script for Render cron job
Run this locally to test the cron scheduler before deploying
"""

import os
import sys
from datetime import datetime

# Set environment variables for testing
os.environ['CRON_SCHEDULE_TYPE'] = 'testing'

print(f"🧪 Testing cron scheduler locally...")
print(f"📅 Current time: {datetime.now()}")
print(f"🔧 Environment: CRON_SCHEDULE_TYPE={os.environ.get('CRON_SCHEDULE_TYPE')}")

try:
    # Import and run the cron scheduler
    from cron_scheduler import main
    main()
    print("✅ Local test completed successfully!")
except Exception as e:
    print(f"❌ Local test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
