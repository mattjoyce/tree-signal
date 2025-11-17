FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY client/ ./client/

# Install uv for faster dependency management
RUN pip install uv

# Install dependencies
RUN uv pip install --system -e .

# Create non-root user
RUN useradd -m -u 1000 treesignal && chown -R treesignal:treesignal /app
USER treesignal

# Expose ports
# 8013 for API server
# 8014 for static client files
EXPOSE 8013 8014

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8013/healthz || exit 1

# Start both servers using a simple script
COPY docker-entrypoint.sh /app/
USER root
RUN chmod +x /app/docker-entrypoint.sh
USER treesignal

CMD ["/app/docker-entrypoint.sh"]
