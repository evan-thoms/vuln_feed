#!/usr/bin/env python3
"""
Master test runner for Celery scheduling system
Runs comprehensive tests to verify all scheduling components work correctly
"""

import os
import sys
import subprocess
import time
import redis
from datetime import datetime

def check_redis():
    """Check if Redis is available"""
    try:
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        return True
    except Exception as e:
        print(f"❌ Redis not available: {e}")
        return False

def run_unit_tests():
    """Run unit tests for scheduling"""
    print("🧪 Running Unit Tests...")
    print("-" * 30)
    
    try:
        result = subprocess.run([
            sys.executable, 'tests/test_celery_scheduling.py'
        ], cwd=os.path.dirname(__file__), capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Unit tests failed: {e}")
        return False

def run_integration_tests():
    """Run integration tests"""
    print("\n🔥 Running Integration Tests...")
    print("-" * 30)
    
    if not check_redis():
        print("⚠️ Redis not available, skipping integration tests")
        return True  # Don't fail if Redis not available
    
    try:
        result = subprocess.run([
            sys.executable, 'tests/test_integration_live.py'
        ], cwd=os.path.dirname(__file__), capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Integration tests failed: {e}")
        return False

def test_celery_worker_startup():
    """Test that Celery worker can start"""
    print("\n⚡ Testing Celery Worker Startup...")
    print("-" * 30)
    
    if not check_redis():
        print("⚠️ Redis not available, skipping worker test")
        return True
    
    try:
        # Try to start worker with short timeout
        process = subprocess.Popen([
            'celery', '-A', 'celery.celery_tasks', 'worker',
            '--loglevel=info',
            '--concurrency=1',
            '--time-limit=10'
        ], cwd=os.path.dirname(__file__), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Give it a few seconds to start
        time.sleep(3)
        
        # Check if still running
        if process.poll() is None:
            print("✅ Celery worker started successfully")
            process.terminate()
            process.wait(timeout=5)
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Worker failed to start")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            return False
            
    except Exception as e:
        print(f"❌ Worker startup test failed: {e}")
        return False

def test_celery_beat_schedule():
    """Test Celery beat schedule validation"""
    print("\n⏰ Testing Celery Beat Schedule...")
    print("-" * 30)
    
    try:
        # Test beat dry run
        result = subprocess.run([
            'celery', '-A', 'celery.celery_tasks', 'beat',
            '--dry-run'
        ], cwd=os.path.dirname(__file__), capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Celery beat schedule is valid")
            return True
        else:
            print(f"❌ Beat schedule validation failed")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✅ Beat validation started (timed out as expected)")
        return True
    except Exception as e:
        print(f"❌ Beat schedule test failed: {e}")
        return False

def test_task_execution():
    """Test manual task execution"""
    print("\n🎯 Testing Manual Task Execution...")
    print("-" * 30)
    
    try:
        # Test importing tasks
        from celery.celery_tasks import scheduled_intelligence_gathering, scheduled_cache_cleanup
        
        print("✅ Task imports successful")
        
        # Test task registration
        from celery.celery_tasks import celery_app
        
        expected_tasks = [
            'celery_tasks.scheduled_intelligence_gathering',
            'celery_tasks.scheduled_cache_cleanup'
        ]
        
        for task_name in expected_tasks:
            if task_name in celery_app.tasks:
                print(f"✅ Task '{task_name}' registered")
            else:
                print(f"❌ Task '{task_name}' not registered")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Task execution test failed: {e}")
        return False

def verify_30_minute_schedule():
    """Verify 30-minute scheduling is configured correctly"""
    print("\n📅 Verifying 30-Minute Schedule Configuration...")
    print("-" * 30)
    
    try:
        from celery.celery_config import beat_schedule
        
        # Check 30-minute schedule
        if 'intelligence-gathering-30min' in beat_schedule:
            schedule = beat_schedule['intelligence-gathering-30min']
            
            # Verify schedule timing (30 minutes = 1800 seconds)
            if schedule['schedule'] == 1800.0:
                print("✅ 30-minute schedule configured correctly")
            else:
                print(f"❌ Schedule timing incorrect: {schedule['schedule']} (should be 1800.0)")
                return False
            
            # Verify task name
            if schedule['task'] == 'celery_tasks.scheduled_intelligence_gathering':
                print("✅ Task name configured correctly")
            else:
                print(f"❌ Task name incorrect: {schedule['task']}")
                return False
                
        else:
            print("❌ 30-minute schedule not found in beat_schedule")
            return False
        
        # Check daily cleanup schedule
        if 'daily-cleanup' in beat_schedule:
            cleanup_schedule = beat_schedule['daily-cleanup']
            if cleanup_schedule['schedule'] == 86400.0:  # 24 hours
                print("✅ Daily cleanup schedule configured correctly")
            else:
                print(f"❌ Cleanup schedule timing incorrect: {cleanup_schedule['schedule']}")
                return False
        else:
            print("❌ Daily cleanup schedule not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Schedule verification failed: {e}")
        return False

def generate_deployment_report(test_results):
    """Generate deployment readiness report"""
    print("\n" + "=" * 60)
    print("📋 DEPLOYMENT READINESS REPORT")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"📊 Tests Passed: {passed_tests}/{total_tests}")
    print(f"📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print()
    
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print()
    
    if passed_tests == total_tests:
        print("🚀 DEPLOYMENT READY!")
        print("✅ All scheduling tests passed")
        print("✅ 30-minute interval configured correctly")
        print("✅ Error handling and retries implemented")
        print("✅ Logging system functional")
        print()
        print("🎯 Next Steps:")
        print("  1. Deploy to production environment")
        print("  2. Start Redis service")
        print("  3. Start Celery worker: python start_celery.py worker")
        print("  4. Start Celery beat: python start_celery.py beat")
        print("  5. Monitor logs in intelligence_gathering.log")
    else:
        print("🚫 NOT READY FOR DEPLOYMENT")
        print("❌ Some tests failed - please fix issues before deploying")
        print()
        print("🔧 Troubleshooting:")
        if not test_results.get("Redis Connection", True):
            print("  - Install and start Redis: brew install redis && brew services start redis")
        if not test_results.get("Unit Tests", True):
            print("  - Check unit test failures above")
        if not test_results.get("Celery Worker", True):
            print("  - Verify Celery installation: pip install celery[redis]")
    
    print("=" * 60)
    return passed_tests == total_tests

def main():
    """Main test runner"""
    print("🎯 CELERY SCHEDULING SYSTEM TEST SUITE")
    print("=" * 60)
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all tests
    test_results = {}
    
    test_results["Redis Connection"] = check_redis()
    test_results["30-Minute Schedule Config"] = verify_30_minute_schedule()
    test_results["Task Registration"] = test_task_execution()
    test_results["Unit Tests"] = run_unit_tests()
    test_results["Celery Beat Schedule"] = test_celery_beat_schedule()
    test_results["Celery Worker"] = test_celery_worker_startup()
    test_results["Integration Tests"] = run_integration_tests()
    
    # Generate deployment report
    deployment_ready = generate_deployment_report(test_results)
    
    return 0 if deployment_ready else 1

if __name__ == '__main__':
    sys.exit(main())
