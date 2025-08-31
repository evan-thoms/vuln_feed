#!/usr/bin/env python3
"""
Simple in-memory rate limiting for the cybersecurity intelligence API
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import threading
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.rate_limit_window = int(os.getenv('RATE_LIMIT_WINDOW_MINUTES', '60'))  # 1 hour default
        self.rate_limit_requests = int(os.getenv('RATE_LIMIT_REQUESTS', '10'))  # 10 requests per hour default
        self.requests = {}  # {ip: [(timestamp, count), ...]}
        self.lock = threading.Lock()
        
        # Clean up old entries every hour
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread to clean up old rate limit entries"""
        def cleanup_loop():
            while True:
                time.sleep(3600)  # Run every hour
                self._cleanup_old_entries()
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_old_entries(self):
        """Remove old rate limit entries"""
        cutoff_time = time.time() - (self.rate_limit_window * 60)
        
        with self.lock:
            for ip in list(self.requests.keys()):
                # Filter out old entries
                self.requests[ip] = [
                    (timestamp, count) 
                    for timestamp, count in self.requests[ip] 
                    if timestamp > cutoff_time
                ]
                
                # Remove IP if no entries left
                if not self.requests[ip]:
                    del self.requests[ip]
    
    def check_rate_limit(self, ip_address: str, endpoint: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits
        
        Args:
            ip_address: Client IP address
            endpoint: API endpoint being accessed
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        window_start = current_time - (self.rate_limit_window * 60)
        
        with self.lock:
            # Get requests for this IP
            ip_requests = self.requests.get(ip_address, [])
            
            # Filter to current window
            current_requests = [
                (timestamp, count) 
                for timestamp, count in ip_requests 
                if timestamp > window_start
            ]
            
            # Count total requests in window
            total_requests = sum(count for _, count in current_requests)
            
            # Check if limit exceeded
            if total_requests >= self.rate_limit_requests:
                # Find earliest request in window
                if current_requests:
                    earliest_timestamp = min(timestamp for timestamp, _ in current_requests)
                    retry_after = int(earliest_timestamp + (self.rate_limit_window * 60) - current_time)
                    return False, max(0, retry_after)
                else:
                    return False, self.rate_limit_window * 60
            
            return True, None
    
    def record_request(self, ip_address: str, endpoint: str) -> bool:
        """
        Record a new request for rate limiting
        
        Args:
            ip_address: Client IP address
            endpoint: API endpoint being accessed
            
        Returns:
            True if recorded successfully
        """
        current_time = time.time()
        
        with self.lock:
            if ip_address not in self.requests:
                self.requests[ip_address] = []
            
            # Add current request
            self.requests[ip_address].append((current_time, 1))
            
            # Keep only recent entries to prevent memory bloat
            window_start = current_time - (self.rate_limit_window * 60)
            self.requests[ip_address] = [
                (timestamp, count) 
                for timestamp, count in self.requests[ip_address] 
                if timestamp > window_start
            ]
        
        return True
    
    def get_rate_limit_info(self, ip_address: str, endpoint: str) -> dict:
        """
        Get current rate limit information for debugging
        
        Args:
            ip_address: Client IP address
            endpoint: API endpoint being accessed
            
        Returns:
            Dictionary with rate limit information
        """
        current_time = time.time()
        window_start = current_time - (self.rate_limit_window * 60)
        
        with self.lock:
            ip_requests = self.requests.get(ip_address, [])
            
            # Filter to current window
            current_requests = [
                (timestamp, count) 
                for timestamp, count in ip_requests 
                if timestamp > window_start
            ]
            
            total_requests = sum(count for _, count in current_requests)
            
            return {
                'ip_address': ip_address,
                'endpoint': endpoint,
                'current_requests': total_requests,
                'limit': self.rate_limit_requests,
                'window_minutes': self.rate_limit_window,
                'window_count': len(current_requests),
                'remaining': max(0, self.rate_limit_requests - total_requests)
            }

# Global rate limiter instance
rate_limiter = RateLimiter()
