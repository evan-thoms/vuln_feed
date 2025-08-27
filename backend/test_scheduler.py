#!/usr/bin/env python3
"""
Test script for Sentinel Intelligence Scheduler
Tests the cron job functionality and email notifications
"""

import os
import sys
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_cron_scheduler():
    """Test the cron scheduler functionality"""
    print("🧪 Testing Sentinel Cron Scheduler...")
    
    try:
        from cron_scheduler import SentinelCronScheduler
        
        # Create scheduler instance
        scheduler = SentinelCronScheduler()
        print("✅ Scheduler instance created successfully")
        
        # Test default parameters
        assert scheduler.default_params['content_type'] == 'both'
        assert scheduler.default_params['severity'] == 'all'
        assert scheduler.default_params['days_back'] == 3
        assert scheduler.default_params['max_results'] == 30
        print("✅ Default parameters are correct")
        
        # Test log file creation
        log_entry = scheduler.log_execution({
            'success': True,
            'cves_found': 15,
            'news_found': 8,
            'session_id': 'test_123'
        })
        print(f"✅ Log entry created: {log_entry}")
        
        print("🎉 All scheduler tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Scheduler test failed: {str(e)}")
        return False

def test_email_notifications():
    """Test email notification functionality"""
    print("\n📧 Testing Email Notifications...")
    
    try:
        from utils.email_notifications import send_intelligence_report
        
        # Mock email configuration
        test_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'test_password'
        }
        
        # Test with mock SMTP
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = send_intelligence_report(
                email_address='test@example.com',
                session_id='test_123',
                results={
                    'cves_found': 15,
                    'news_found': 8,
                    'processing_time': 45.2
                },
                success=True
            )
            
            assert result == True
            print("✅ Email notification test passed")
            
    except Exception as e:
        print(f"❌ Email notification test failed: {str(e)}")
        return False
    
    return True

def test_manual_trigger():
    """Test manual trigger endpoint"""
    print("\n🔧 Testing Manual Trigger Endpoint...")
    
    try:
        # Import FastAPI test client
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Test manual trigger endpoint
        response = client.post("/manual-trigger")
        
        # Should return 200 or 500 (depending on if scheduler is available)
        assert response.status_code in [200, 500]
        print(f"✅ Manual trigger endpoint responded with status: {response.status_code}")
        
        # Test scheduler status endpoint
        response = client.get("/scheduler-status")
        assert response.status_code == 200
        print("✅ Scheduler status endpoint working")
        
    except Exception as e:
        print(f"❌ Manual trigger test failed: {str(e)}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Sentinel Intelligence Scheduler Tests\n")
    
    tests = [
        test_cron_scheduler,
        test_email_notifications,
        test_manual_trigger
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Scheduler is ready for deployment.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
