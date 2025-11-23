FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Docker commands
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Set appropriate permissions
RUN chmod -R 755 /app/data

EXPOSE 3001

# Use volume mount point for persistent database storage
VOLUME ["/app/data"]

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "3001"]