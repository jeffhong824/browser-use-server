#!/bin/bash
# Ensure browser-use browser is installed

set -e

echo "🔍 Checking browser installation..."

# Ensure Playwright browsers are installed (required by browser-use)
echo "🌐 Installing Playwright Chromium browser..."
python -m playwright install chromium 2>&1 || {
    echo "⚠️  Playwright browser installation failed, trying install-deps..."
    python -m playwright install-deps chromium 2>&1 || true
}

# Try to install browser via uvx (optional, browser-use can use playwright)
if command -v uvx &> /dev/null; then
    echo "🌐 Installing browser-use browser via uvx..."
    uvx browser-use install 2>&1 || {
        echo "⚠️  Browser installation via uvx failed (this is OK, browser-use will use playwright)"
    }
else
    echo "📦 Installing uv for browser-use..."
    pip install --quiet uv
    echo "🌐 Installing browser-use browser via uvx..."
    uvx browser-use install 2>&1 || {
        echo "⚠️  Browser installation via uvx failed (this is OK, browser-use will use playwright)"
    }
fi

echo "✅ Browser installation check complete"

