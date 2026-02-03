FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for data
RUN mkdir -p /app/data

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5003

# Health check (longer start period for ML model loading)
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:5003/api/health || exit 1

# Run with gunicorn (1 worker to save memory for ML model, preload to load model once)
CMD ["gunicorn", "--bind", "0.0.0.0:5003", "--workers", "1", "--threads", "4", "--timeout", "300", "--preload", "main:app"]
