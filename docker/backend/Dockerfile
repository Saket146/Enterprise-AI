FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed for compiling package assets (e.g. psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code files
COPY . .

# Expose FastAPI listening port
EXPOSE 8000

# Start server using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
