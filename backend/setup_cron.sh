#!/bin/bash

# Setup script for Sentinel Intelligence Gathering Cron Jobs
# This script sets up automated intelligence gathering via cron

set -e

echo "🔧 Setting up Sentinel Intelligence Gathering cron jobs..."

# Get the current directory (backend)
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH="$(which python3)"

if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Python3 not found. Please install Python 3.7+"
    exit 1
fi

echo "📁 Backend directory: $BACKEND_DIR"
echo "🐍 Python path: $PYTHON_PATH"

# Create the cron job commands
# Testing schedule: Every 30 minutes
TESTING_CRON="*/30 * * * * cd $BACKEND_DIR && $PYTHON_PATH cron_scheduler.py 2>&1 | logger -t sentinel-testing"

# Production schedule: Every 6 hours (at 00:00, 06:00, 12:00, 18:00)
PRODUCTION_CRON="0 */6 * * * cd $BACKEND_DIR && $PYTHON_PATH cron_scheduler.py 2>&1 | logger -t sentinel-production"

echo "📅 Creating cron jobs..."

# Create temporary crontab file
TEMP_CRON=$(mktemp)

# Add existing crontab entries (if any)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# Add our cron jobs
echo "# Sentinel Intelligence Gathering - Testing Schedule (30 min)" >> "$TEMP_CRON"
echo "$TESTING_CRON" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

echo "# Sentinel Intelligence Gathering - Production Schedule (6 hours)" >> "$TEMP_CRON"
echo "$PRODUCTION_CRON" >> "$TEMP_CRON"
echo "" >> "$TEMP_CRON"

# Install the cron jobs
crontab "$TEMP_CRON"

# Clean up
rm "$TEMP_CRON"

echo "✅ Cron jobs installed successfully!"
echo ""
echo "📋 Installed cron jobs:"
echo "  - Testing: Every 30 minutes"
echo "  - Production: Every 6 hours"
echo ""
echo "🔍 To view cron jobs: crontab -l"
echo "🗑️  To remove cron jobs: crontab -r"
echo ""
echo "📊 Logs will be saved to:"
echo "  - cron_scheduler.log"
echo "  - scheduled_intelligence_testing.log"
echo "  - scheduled_intelligence_production.log"
echo ""
echo "🚀 Next scheduled runs:"
echo "  - Testing: Every 30 minutes"
echo "  - Production: Every 6 hours (00:00, 06:00, 12:00, 18:00)"
