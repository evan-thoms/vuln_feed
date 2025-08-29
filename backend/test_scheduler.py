#!/usr/bin/env python3
"""
Test script for Sentinel Cron Scheduler
Tests both testing (30-minute) and production (3-day) configurations
"""

import os
import sys
import json
from datetime import datetime
from cron_scheduler import SentinelCronScheduler
from utils.email_notifications import test_email_configuration

def test_scheduler_configuration():
    """Test scheduler configuration and initialization"""
    print("🧪 Testing Scheduler Configuration...")
    
    # Test testing configuration
    print("\n1. Testing 30-minute configuration...")
    try:
        scheduler_testing = SentinelCronScheduler("testing")
        print(f"✅ Testing config: {scheduler_testing.config}")
        print(f"✅ Schedule name: {scheduler_testing.schedule_name}")
    except Exception as e:
        print(f"❌ Testing configuration failed: {e}")
        return False
    
    # Test production configuration
    print("\n2. Testing 3-day production configuration...")
    try:
        scheduler_production = SentinelCronScheduler("production")
        print(f"✅ Production config: {scheduler_production.config}")
        print(f"✅ Schedule name: {scheduler_production.schedule_name}")
    except Exception as e:
        print(f"❌ Production configuration failed: {e}")
        return False
    
    return True

def test_environment_variables():
    """Test required environment variables"""
    print("\n🧪 Testing Environment Variables...")
    
    required_vars = [
        'OPENAI_API_KEY',
        'SUPABASE_URL',
        'SUPABASE_KEY'
    ]
    
    optional_vars = [
        'SENTINEL_NOTIFICATION_EMAIL',
        'SMTP_USERNAME',
        'SMTP_PASSWORD'
    ]
    
    print("Required variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
        else:
            print(f"❌ {var}: Not set")
    
    print("\nOptional variables (for email notifications):")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
        else:
            print(f"⚠️ {var}: Not set (email notifications disabled)")
    
    return True

def test_email_configuration():
    """Test email configuration"""
    print("\n🧪 Testing Email Configuration...")
    
    email_address = os.getenv('SENTINEL_NOTIFICATION_EMAIL')
    if not email_address:
        print("⚠️ SENTINEL_NOTIFICATION_EMAIL not set, skipping email test")
        return True
    
    smtp_username = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if not smtp_username or not smtp_password:
        print("⚠️ SMTP credentials not set, skipping email test")
        return True
    
    try:
        success = test_email_configuration()
        if success:
            print("✅ Email configuration test successful")
        else:
            print("❌ Email configuration test failed")
        return success
    except Exception as e:
        print(f"❌ Email test error: {e}")
        return False

def test_scheduler_execution(schedule_type: str = "testing"):
    """Test actual scheduler execution"""
    print(f"\n🧪 Testing Scheduler Execution ({schedule_type})...")
    
    try:
        scheduler = SentinelCronScheduler(schedule_type)
        print(f"✅ Scheduler initialized for {schedule_type}")
        
        # Run the scheduler
        print("🔄 Running intelligence gathering...")
        result = scheduler.run_scheduled_intelligence_gathering()
        
        if result.get("success"):
            print("✅ Scheduler execution successful")
            print(f"📊 Results: {result.get('results', {})}")
            return True
        else:
            print(f"❌ Scheduler execution failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Scheduler execution error: {e}")
        return False

def test_log_files():
    """Test log file creation"""
    print("\n🧪 Testing Log Files...")
    
    log_files = [
        "scheduled_intelligence_testing.log",
        "scheduled_intelligence_production.log",
        "cron_scheduler.log"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"✅ {log_file}: Exists")
            # Show last few lines
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"   Last entry: {lines[-1].strip()[:100]}...")
            except Exception as e:
                print(f"   Error reading log: {e}")
        else:
            print(f"⚠️ {log_file}: Not found (will be created on first run)")
    
    return True

def main():
    """Main test function"""
    print("🚀 Sentinel Cron Scheduler Test Suite")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Scheduler Configuration", test_scheduler_configuration),
        ("Email Configuration", test_email_configuration),
        ("Testing Schedule Execution", lambda: test_scheduler_execution("testing")),
        ("Log Files", test_log_files)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 Test Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your cron scheduler is ready for deployment.")
        print("\nNext steps:")
        print("1. Deploy to Render using render.yaml")
        print("2. Set environment variables in Render dashboard")
        print("3. For testing: Set CRON_SCHEDULE_TYPE=testing and schedule to */30 * * * *")
        print("4. For production: Set CRON_SCHEDULE_TYPE=production and schedule to 0 0 */3 * *")
    else:
        print("⚠️ Some tests failed. Please fix the issues before deployment.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
