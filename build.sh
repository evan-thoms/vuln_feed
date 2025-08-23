#!/bin/bash
# Build script for Render deployment

echo "Starting optimized build process..."

# Upgrade pip first
pip install --upgrade pip

# Install core dependencies first (fastest to install)
echo "Installing core dependencies..."
pip install --no-cache-dir --prefer-binary fastapi uvicorn[standard] websockets pydantic

# Install AI/ML dependencies
echo "Installing AI/ML dependencies..."
pip install --no-cache-dir --prefer-binary openai langchain langchain-openai langchain-core

# Install web scraping dependencies
echo "Installing web scraping dependencies..."
pip install --no-cache-dir --prefer-binary requests beautifulsoup4 feedparser lxml vulners

# Install task queue dependencies
echo "Installing task queue dependencies..."
pip install --no-cache-dir --prefer-binary celery redis

# Install utilities
echo "Installing utilities..."
pip install --no-cache-dir --prefer-binary python-dotenv python-dateutil pytz

# Translation handled by OpenAI (no additional dependencies needed)

echo "Build completed successfully!"
