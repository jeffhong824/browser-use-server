#!/bin/bash
# Quick start script for Browser Use SaaS

set -e

echo "🚀 Browser Use SaaS - Quick Start"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=.*[^your_openai_api_key_here]" .env 2>/dev/null; then
    echo "⚠️  Please set OPENAI_API_KEY in .env file"
    exit 1
fi

# Start services
echo "🐳 Starting Docker services..."
make docker-stop
make docker-run-bg

echo ""
echo "✅ Service started!"
echo "📡 API: http://localhost:${API_PORT:-8000}"
echo "🌐 Web: http://localhost:${API_PORT:-8000}/"
echo ""
echo "View logs: make docker-logs"

