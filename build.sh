#!/bin/bash
# Optimized build script for Render deployment

echo "🚀 Starting optimized build process..."

# Upgrade pip first
pip install --upgrade pip

# Install dependencies in order of stability (most stable first for better caching)
echo "📦 Installing core web framework..."
pip install --no-cache-dir --prefer-binary fastapi==0.104.1 uvicorn[standard]==0.24.0 websockets==12.0 pydantic==2.11.7

echo "🧠 Installing AI/ML dependencies..."
pip install --no-cache-dir --prefer-binary "openai>=1.40.0" langchain==0.3.26 langchain-openai==0.2.0 langchain-core==0.3.68

echo "🌐 Installing web scraping..."
pip install --no-cache-dir --prefer-binary requests==2.31.0 beautifulsoup4==4.9.3 feedparser==6.0.11 lxml==6.0.0 vulners==1.4.0

echo "🗄️ Installing database..."
pip install --no-cache-dir --prefer-binary "psycopg2-binary>=2.9.5"

echo "⚙️ Installing task queue..."
pip install --no-cache-dir --prefer-binary celery==5.3.4 redis==4.4.4

echo "🔧 Installing utilities..."
pip install --no-cache-dir --prefer-binary python-dotenv==1.1.1 python-dateutil==2.9.0.post0 pytz==2025.2

echo "✅ Build completed successfully!"
