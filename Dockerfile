# Multi-stage build for production
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies including ODBC drivers for SQL Server
# Check Debian version (for debugging)
RUN cat /etc/os-release || true

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    gnupg \
    ca-certificates \
    apt-transport-https \
    unixodbc \
    unixodbc-dev

# Add Microsoft repository using keyring (not deprecated apt-key)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg

# Use Debian 12 (bookworm) - adjust if base image is Debian 11
RUN echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
    https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/microsoft-prod.list

# Install Microsoft ODBC Driver 18
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="$PATH:/opt/mssql-tools18/bin"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install ODBC drivers for SQL Server (needed for pyodbc)
# Add Microsoft repository using keyring (not deprecated apt-key)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    apt-transport-https \
    unixodbc

# Add Microsoft GPG key to keyring
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor > /usr/share/keyrings/microsoft-prod.gpg

# Use Debian 12 (bookworm) - adjust if base image is Debian 11
RUN echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
    https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/microsoft-prod.list

# Install Microsoft ODBC Driver 18
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="$PATH:/opt/mssql-tools18/bin"

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Set PATH to include user's local bin
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Default to development mode (temporarily)
ENV ENVIRONMENT=development

# Run the application - use Gunicorn in production, uvicorn in development
CMD if [ "$ENVIRONMENT" = "production" ] ; then \
    exec gunicorn main:app -c gunicorn.conf.py ; \
    else \
    exec python main.py ; \
    fi
