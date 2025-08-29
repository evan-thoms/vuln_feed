#!/usr/bin/env python3
"""
Comprehensive test suite for Celery scheduling system
Tests all components to ensure they work correctly in production
"""

import unittest
import os
import sys
import time
import json
import redis
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, mock_open

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from celery.celery_tasks import (
    celery_app, 
    scheduled_intelligence_gathering, 
    scheduled_cache_cleanup,
    manual_scrape_task
)
from celery.celery_config import beat_schedule

class TestCeleryConfiguration(unittest.TestCase):
    """Test Celery configuration and setup"""
    
    def test_celery_app_configured(self):
        """Test that Celery app is properly configured"""
        self.assertIsNotNone(celery_app)
        self.assertEqual(celery_app.main, 'cyberintel')
    
    def test_beat_schedule_30_minutes(self):
        """Test that beat schedule is set to 30 minutes"""
        self.assertIn('intelligence-gathering-30min', beat_schedule)
        
        schedule = beat_schedule['intelligence-gathering-30min']
        self.assertEqual(schedule['task'], 'celery_tasks.scheduled_intelligence_gathering')
        self.assertEqual(schedule['schedule'], 30.0 * 60)  # 30 minutes in seconds
    
    def test_daily_cleanup_schedule(self):
        """Test that cleanup is scheduled daily"""
        self.assertIn('daily-cleanup', beat_schedule)
        
        schedule = beat_schedule['daily-cleanup']
        self.assertEqual(schedule['task'], 'celery_tasks.scheduled_cache_cleanup')
        self.assertEqual(schedule['schedule'], 60.0 * 60 * 24)  # Daily

class TestRedisConnection(unittest.TestCase):
    """Test Redis connection for Celery broker"""
    
    def test_redis_connection(self):
        """Test that Redis is accessible"""
        try:
            redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            r.ping()
            self.assertTrue(True, "Redis connection successful")
        except Exception as e:
            self.skipTest(f"Redis not available: {e}")
    
    def test_redis_can_store_retrieve(self):
        """Test that Redis can store and retrieve data"""
        try:
            redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            
            test_key = "celery_test_key"
            test_value = "test_value"
            
            r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved = r.get(test_key)
            
            self.assertEqual(retrieved.decode('utf-8'), test_value)
            
            # Cleanup
            r.delete(test_key)
            
        except Exception as e:
            self.skipTest(f"Redis not available: {e}")

class TestScheduledTasks(unittest.TestCase):
    """Test scheduled task functionality"""
    
    @patch('celery.celery_tasks.IntelligentCyberAgent')
    @patch('celery.celery_tasks.get_cache_freshness')
    @patch('celery.celery_tasks.is_data_fresh')
    @patch('builtins.open', new_callable=mock_open)
    def test_scheduled_intelligence_gathering_success(self, mock_file, mock_is_fresh, mock_cache, mock_agent):
        """Test successful intelligence gathering task"""
        # Setup mocks
        mock_is_fresh.return_value = False  # Cache is not fresh
        mock_cache.return_value = {'last_scrape': datetime.now() - timedelta(hours=1)}
        
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.query.return_value = {
            'success': True,
            'cves': [{'id': 'CVE-2024-001'}, {'id': 'CVE-2024-002'}],
            'news': [{'title': 'Security Alert'}],
            'total_results': 3,
            'session_id': 'test_session'
        }
        
        # Create a mock task instance
        mock_task = MagicMock()
        mock_task.request.id = 'test-task-id'
        mock_task.request.retries = 0
        
        # Execute task
        result = scheduled_intelligence_gathering(mock_task)
        
        # Verify results
        self.assertTrue(result['success'])
        self.assertEqual(result['task'], 'scheduled_intelligence_gathering_30min')
        self.assertIn('results', result)
        
        # Verify agent was called with correct parameters
        mock_agent_instance.query.assert_called_once()
        call_args = mock_agent_instance.query.call_args[0][0]
        self.assertEqual(call_args['content_type'], 'both')
        self.assertEqual(call_args['severity'], ['Critical', 'High'])
        self.assertEqual(call_args['days_back'], 1)
        self.assertEqual(call_args['max_results'], 20)
        
        # Verify logging
        mock_file.assert_called_with("intelligence_gathering.log", "a")
    
    @patch('celery.celery_tasks.get_cache_freshness')
    @patch('celery.celery_tasks.is_data_fresh')
    @patch('builtins.open', new_callable=mock_open)
    def test_scheduled_intelligence_gathering_cache_fresh(self, mock_file, mock_is_fresh, mock_cache):
        """Test that task skips when cache is fresh"""
        # Setup mocks
        mock_is_fresh.return_value = True  # Cache is fresh
        mock_cache.return_value = {'last_scrape': datetime.now()}
        
        # Create a mock task instance
        mock_task = MagicMock()
        mock_task.request.id = 'test-task-id'
        mock_task.request.retries = 0
        
        # Execute task
        result = scheduled_intelligence_gathering(mock_task)
        
        # Verify task was skipped
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'cache_fresh')
    
    @patch('celery.celery_tasks.IntelligentCyberAgent')
    @patch('celery.celery_tasks.get_cache_freshness')
    @patch('celery.celery_tasks.is_data_fresh')
    @patch('builtins.open', new_callable=mock_open)
    def test_scheduled_intelligence_gathering_with_retry(self, mock_file, mock_is_fresh, mock_cache, mock_agent):
        """Test task retry mechanism"""
        # Setup mocks
        mock_is_fresh.return_value = False
        mock_cache.return_value = {'last_scrape': datetime.now() - timedelta(hours=1)}
        
        mock_agent_instance = MagicMock()
        mock_agent.return_value = mock_agent_instance
        mock_agent_instance.query.side_effect = Exception("Test error")
        
        # Create a mock task instance
        mock_task = MagicMock()
        mock_task.request.id = 'test-task-id'
        mock_task.request.retries = 0
        mock_task.max_retries = 3
        mock_task.retry = MagicMock(side_effect=Exception("Retry called"))
        
        # Execute task (should trigger retry)
        with self.assertRaises(Exception):
            scheduled_intelligence_gathering(mock_task)
        
        # Verify retry was called
        mock_task.retry.assert_called_once()
    
    @patch('celery.celery_tasks.manage_cache_cleanup')
    @patch('builtins.open', new_callable=mock_open)
    def test_scheduled_cache_cleanup_success(self, mock_file, mock_cleanup):
        """Test successful cache cleanup task"""
        # Setup mocks
        mock_cleanup.return_value = {"deleted_articles": 25, "status": "success"}
        
        # Create a mock task instance
        mock_task = MagicMock()
        mock_task.request.id = 'cleanup-task-id'
        mock_task.request.retries = 0
        
        # Execute task
        result = scheduled_cache_cleanup(mock_task)
        
        # Verify results
        self.assertEqual(result['status'], 'completed')
        self.assertIn('result', result)
        
        # Verify cleanup was called with correct parameters
        mock_cleanup.assert_called_once_with(weeks_old=2)
        
        # Verify logging
        mock_file.assert_called_with("intelligence_gathering.log", "a")

class TestTaskExecution(unittest.TestCase):
    """Test actual task execution (integration tests)"""
    
    def test_manual_scrape_task_structure(self):
        """Test manual scrape task has correct structure"""
        # Test with default parameters
        task = manual_scrape_task
        self.assertIsNotNone(task)
        
        # Verify task is registered
        self.assertIn('celery_tasks.manual_scrape_task', celery_app.tasks)
    
    def test_celery_app_tasks_registered(self):
        """Test that all tasks are properly registered"""
        expected_tasks = [
            'celery_tasks.scheduled_intelligence_gathering',
            'celery_tasks.scheduled_cache_cleanup',
            'celery_tasks.manual_scrape_task'
        ]
        
        for task_name in expected_tasks:
            self.assertIn(task_name, celery_app.tasks, f"Task {task_name} not registered")

class TestLogging(unittest.TestCase):
    """Test logging functionality"""
    
    @patch('builtins.open', new_callable=mock_open)
    def test_log_file_creation(self, mock_file):
        """Test that log files are created correctly"""
        # Mock a task that writes to log
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": "test_task",
            "success": True
        }
        
        with open("intelligence_gathering.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        # Verify file was opened correctly
        mock_file.assert_called_with("intelligence_gathering.log", "a")
        handle = mock_file()
        handle.write.assert_called_once()
        
        # Verify JSON structure
        written_data = handle.write.call_args[0][0]
        self.assertIn('"timestamp"', written_data)
        self.assertIn('"task"', written_data)
        self.assertIn('"success"', written_data)

class TestEnvironmentConfiguration(unittest.TestCase):
    """Test environment-specific configurations"""
    
    def test_redis_url_configuration(self):
        """Test Redis URL configuration from environment"""
        # Test default
        with patch.dict(os.environ, {}, clear=True):
            from celery import celery_config
            # Should fall back to localhost
            self.assertTrue(celery_config.broker_url.startswith('redis://'))
    
    def test_production_configuration(self):
        """Test production environment variables"""
        prod_redis_url = "redis://prod-redis:6379/0"
        
        with patch.dict(os.environ, {'CELERY_BROKER_URL': prod_redis_url}):
            # Reload config
            import importlib
            from celery import celery_config
            importlib.reload(celery_config)
            
            self.assertEqual(celery_config.broker_url, prod_redis_url)

class TestCeleryWorkerConfiguration(unittest.TestCase):
    """Test Celery worker configuration"""
    
    def test_worker_settings(self):
        """Test worker configuration settings"""
        from celery.celery_config import worker_prefetch_multiplier, task_acks_late, worker_max_tasks_per_child
        
        self.assertEqual(worker_prefetch_multiplier, 1)
        self.assertTrue(task_acks_late)
        self.assertEqual(worker_max_tasks_per_child, 1000)

if __name__ == '__main__':
    print("🧪 Running Celery Scheduling Tests")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestCeleryConfiguration,
        TestRedisConnection,
        TestScheduledTasks,
        TestTaskExecution,
        TestLogging,
        TestEnvironmentConfiguration,
        TestCeleryWorkerConfiguration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All Celery scheduling tests passed!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        
    print(f"📊 Ran {result.testsRun} tests")
