FROM python:3.11-slim

# Install system dependencies with retry logic
RUN apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    --no-install-recommends \
    -o Dpkg::Options::="--force-confdef" \
    -o Dpkg::Options::="--force-confold" \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    libpq-dev \
    pkg-config \
    || (echo "Retrying apt-get after 5 seconds..." && sleep 5 && \
        apt-get update -qq && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y \
        --no-install-recommends \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        gcc \
        g++ \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
        libpq-dev \
        pkg-config) \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with piwheels for ARM optimization
RUN pip install --no-cache-dir \
    --extra-index-url https://www.piwheels.org/simple \
    -r requirements.txt

# Copy application code
COPY . .

# Expose port for Dash app
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8003/health')"

# Run the application
CMD ["python", "app.py"]