# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies including chromaprint
RUN apt-get update && apt-get install -y \
    libchromaprint1 \
    libchromaprint-tools \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FPCALC=/usr/bin/fpcalc

# Run with gunicorn (Railway uses $PORT environment variable)
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 --worker-class gevent app:app
