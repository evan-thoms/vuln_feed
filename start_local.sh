#!/bin/bash

echo "🚀 Starting Vuln Feed Locally..."
echo "================================"

# Function to start backend
start_backend() {
    echo "🔧 Starting Backend (FastAPI + Uvicorn)..."
    cd backend
    source ../venv/bin/activate
    python main.py &
    BACKEND_PID=$!
    echo "✅ Backend started with Uvicorn (PID: $BACKEND_PID)"
    echo "📍 Backend URL: http://localhost:8000"
    echo "📊 API Docs: http://localhost:8000/docs"
    echo ""
}

# Function to start frontend
start_frontend() {
    echo "🎨 Starting Frontend (Next.js)..."
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    echo "✅ Frontend started (PID: $FRONTEND_PID)"
    echo "📍 Frontend URL: http://localhost:3000"
    echo ""
}

# Start both services
start_backend
start_frontend

echo "🎉 Both services are running!"
echo "================================"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend:  http://localhost:8000"
echo "📊 Backend API: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services"

# Wait for user to stop
wait
