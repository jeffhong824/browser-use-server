FROM python:3.12-slim

# Set pip timeout environment variable
ENV PIP_DEFAULT_TIMEOUT=300

# Install system dependencies for Chromium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with increased timeout
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt

# Install Playwright browsers (Chromium) - required by browser-use
RUN playwright install chromium || \
    (echo "Playwright browser installation failed, will try on first run" && \
     playwright install-deps chromium || true)

# Install uv for browser-use browser installation (with timeout and retry)
# Note: uv is optional, browser-use can work without it
RUN pip install --no-cache-dir --default-timeout=300 uv || \
    (echo "⚠️  uv installation failed (non-critical), browser-use will install browser on first run" && \
     mkdir -p /root/.local/share/browser-use)

# Try to install browser-use browser (as fallback)
RUN uvx browser-use install 2>&1 || \
    (echo "Browser installation via uvx failed, browser-use will install on first run" && \
     mkdir -p /root/.local/share/browser-use)

# Copy application code
COPY src/ ./src/
COPY .env.example .env.example

# Create necessary directories
RUN mkdir -p /app/recordings /app/screenshots /app/data /app/outputs

# Copy scripts
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh 2>/dev/null || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run browser installation check and then start application
CMD ["/bin/bash", "-c", "./scripts/ensure_browser.sh && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]

