# Use official Python runtime as base image
FROM python:3.13-slim

# Set working directory in container
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies (minimal for security)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file (we'll create this next)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI server application
COPY fastapi_server.py .

# Expose port 6000
EXPOSE 6000

# Health check to verify server is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:6000/health')" || exit 1

# Run the FastAPI server with uvicorn
# Note: Render uses port 10000 by default, override with PORT env var if needed
CMD ["sh", "-c", "python -m uvicorn fastapi_server:app --host 0.0.0.0 --port ${PORT:-10000}"]
