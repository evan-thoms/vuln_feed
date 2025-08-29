#!/usr/bin/env python3
"""
Test script to diagnose startup issues
"""

import os
import sys
import traceback

def test_imports():
    """Test if all imports work"""
    print("🧪 Testing imports...")
    
    try:
        import requests
        print("✅ requests")
    except Exception as e:
        print(f"❌ requests: {e}")
    
    try:
        import feedparser
        print("✅ feedparser")
    except Exception as e:
        print(f"❌ feedparser: {e}")
    
    try:
        import psycopg2
        print("✅ psycopg2")
    except Exception as e:
        print(f"❌ psycopg2: {e}")
    
    try:
        from langchain_openai import ChatOpenAI
        print("✅ langchain_openai")
    except Exception as e:
        print(f"❌ langchain_openai: {e}")
    
    try:
        from langchain_core.prompts import ChatPromptTemplate
        print("✅ langchain_core.prompts")
    except Exception as e:
        print(f"❌ langchain_core.prompts: {e}")

def test_environment():
    """Test environment variables"""
    print("\n🧪 Testing environment variables...")
    
    critical_vars = [
        'OPENAI_API_KEY',
        'DATABASE_URL',
        'SENTINEL_NOTIFICATION_EMAIL',
        'SMTP_SERVER',
        'SMTP_USERNAME',
        'SMTP_PASSWORD'
    ]
    
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Not set")

def test_database_connection():
    """Test database connection"""
    print("\n🧪 Testing database connection...")
    
    try:
        from db import get_connection
        conn = get_connection()
        print("✅ Database connection successful")
        conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        traceback.print_exc()

def test_agent_initialization():
    """Test agent initialization"""
    print("\n🧪 Testing agent initialization...")
    
    try:
        from agent import IntelligentCyberAgent
        agent = IntelligentCyberAgent()
        print("✅ Agent initialization successful")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        traceback.print_exc()

def test_main_imports():
    """Test main application imports"""
    print("\n🧪 Testing main application imports...")
    
    try:
        from main import app
        print("✅ FastAPI app import successful")
    except Exception as e:
        print(f"❌ FastAPI app import failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting startup diagnostics...")
    print("=" * 50)
    
    test_imports()
    test_environment()
    test_database_connection()
    test_agent_initialization()
    test_main_imports()
    
    print("\n" + "=" * 50)
    print("✅ Startup diagnostics complete")
