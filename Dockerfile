# Use a single stage build for simplicity
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for cookies
RUN mkdir -p /app/cookies

# Copy cookies file to the container
COPY youtube_cookies_firefox.txt /app/cookies/

# Copy .env file
COPY .env .

# Copy application code
COPY . .

# Set environment variables
ENV PORT=8080
ENV COOKIES_PATH=/app/cookies/youtube_cookies_firefox.txt

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"] 

