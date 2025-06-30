# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install ffmpeg and yt-dlp dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Flask custom port
EXPOSE 5020

# Run the Flask app
CMD ["python", "app.py"]
