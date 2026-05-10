FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl gcc python3-dev ffmpeg espeak tmux && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install openai-whisper yt-dlp
RUN npm install -g @anthropic-ai/claude-code
RUN playwright install chromium --with-deps

# Patch py-cord voice_client.py to guard poll_voice_ws against _MissingSentinel.
# py-cord swallows the exception internally before asyncio/on_error handlers can
# catch it, so we patch the source directly at build time.
COPY infra/docker/patch_pycord.py .
RUN python3 patch_pycord.py

COPY . .
