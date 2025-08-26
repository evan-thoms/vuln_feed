"""
Date utility functions for consistent date handling across the application.
Handles PostgreSQL vs SQLite differences and provides robust date parsing.
"""

from datetime import datetime, timezone
from typing import Union, Optional
import re

def parse_date_safe(date_value: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Safely parse a date value that could be a string, datetime object, or None.
    Handles various date formats and timezone issues.
    
    Args:
        date_value: Date value that could be string, datetime, or None
        
    Returns:
        datetime object or None if parsing fails
    """
    if date_value is None:
        return None
    
    # If it's already a datetime object, return it
    if isinstance(date_value, datetime):
        # Remove timezone info if present to ensure consistency
        if date_value.tzinfo is not None:
            return date_value.replace(tzinfo=None)
        return date_value
    
    # If it's a string, try to parse it
    if isinstance(date_value, str):
        try:
            # Handle various date formats
            date_str = date_value.strip()
            
            # Handle ISO format with 'Z' timezone
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            
            # Try parsing with fromisoformat first (most reliable)
            try:
                parsed_date = datetime.fromisoformat(date_str)
                # Remove timezone info for consistency
                if parsed_date.tzinfo is not None:
                    parsed_date = parsed_date.replace(tzinfo=None)
                return parsed_date
            except ValueError:
                pass
            
            # Try common date formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%S.%f%z',
                '%Y-%m-%d',
                '%d/%m/%Y',
                '%m/%d/%Y'
            ]
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    # Remove timezone info for consistency
                    if parsed_date.tzinfo is not None:
                        parsed_date = parsed_date.replace(tzinfo=None)
                    return parsed_date
                except ValueError:
                    continue
            
            # If all parsing attempts fail, return None
            print(f"⚠️ Warning: Could not parse date string: {date_str}")
            return None
            
        except Exception as e:
            print(f"⚠️ Error parsing date '{date_value}': {e}")
            return None
    
    # If it's any other type, return None
    print(f"⚠️ Warning: Unexpected date type: {type(date_value)}")
    return None

def format_date_for_db(date_value: Union[str, datetime, None]) -> Optional[str]:
    """
    Format a date value for database storage.
    Ensures consistent ISO format for both PostgreSQL and SQLite.
    
    Args:
        date_value: Date value to format
        
    Returns:
        ISO format string or None
    """
    parsed_date = parse_date_safe(date_value)
    if parsed_date is None:
        return None
    
    return parsed_date.isoformat()

def format_date_for_display(date_value: Union[str, datetime, None]) -> str:
    """
    Format a date value for display purposes.
    
    Args:
        date_value: Date value to format
        
    Returns:
        Formatted date string
    """
    parsed_date = parse_date_safe(date_value)
    if parsed_date is None:
        return "Unknown date"
    
    return parsed_date.strftime('%Y-%m-%d %H:%M:%S')

def is_recent_date(date_value: Union[str, datetime, None], days_threshold: int = 7) -> bool:
    """
    Check if a date is recent (within specified days).
    
    Args:
        date_value: Date to check
        days_threshold: Number of days to consider "recent"
        
    Returns:
        True if date is recent, False otherwise
    """
    parsed_date = parse_date_safe(date_value)
    if parsed_date is None:
        return False
    
    days_old = (datetime.now() - parsed_date).days
    return days_old <= days_threshold

def get_days_old(date_value: Union[str, datetime, None]) -> Optional[int]:
    """
    Get the number of days old a date is.
    
    Args:
        date_value: Date to check
        
    Returns:
        Number of days old, or None if parsing fails
    """
    parsed_date = parse_date_safe(date_value)
    if parsed_date is None:
        return None
    
    return (datetime.now() - parsed_date).days

def normalize_date_for_article(date_value: Union[str, datetime, None]) -> datetime:
    """
    Normalize a date value for article creation.
    Always returns a datetime object, defaults to now() if parsing fails.
    
    Args:
        date_value: Date value to normalize
        
    Returns:
        Normalized datetime object
    """
    parsed_date = parse_date_safe(date_value)
    if parsed_date is None:
        return datetime.now()
    
    return parsed_date
