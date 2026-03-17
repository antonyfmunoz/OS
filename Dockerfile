FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
COPY 13_Scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install openai-whisper yt-dlp
RUN playwright install chromium --with-deps
COPY . .
