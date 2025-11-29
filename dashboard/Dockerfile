# Dockerfile for Admin Dashboard component
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy dashboard code
WORKDIR /app
COPY server.py ./
COPY requirements.txt ./
COPY static/ ./static/

# Install dependencies
RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir --timeout=60 -r requirements.txt

# Expose dashboard port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run dashboard server
CMD ["python3", "server.py"]

