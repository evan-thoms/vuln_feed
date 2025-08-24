#!/bin/bash
# Build script for Render deployment

echo "Starting build process..."

# Upgrade pip first
pip install --upgrade pip

# Install all dependencies from requirements.txt
echo "Installing dependencies..."
pip install --no-cache-dir --prefer-binary -r requirements.txt

echo "Build completed successfully!"
