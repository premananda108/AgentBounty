#!/bin/bash

# AgentBounty Backend - Quick Start Script

echo "🚀 Starting AgentBounty Backend..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Check if dependencies are installed
if [ ! -f ".venv/installed" ]; then
    echo "📥 Installing dependencies..."
    pip install -r requirements.txt
    touch .venv/installed
    echo "✅ Dependencies installed"
    echo ""
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create .env file based on .env.example"
    echo ""
    exit 1
fi

# Create data directory
mkdir -p data

# Run server
echo "🌐 Starting server on http://localhost:8000"
echo "📚 API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Add Node.js binaries to the PATH for the subprocess
export PATH="/usr/local/bin:$PATH"

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
