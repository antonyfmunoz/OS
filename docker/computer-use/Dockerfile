FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV VNC_PORT=5901
ENV NOVNC_PORT=6080
ENV RESOLUTION=1280x800x24

RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    fluxbox \
    xdotool \
    scrot \
    xclip \
    python3 \
    python3-pip \
    chromium-browser \
    dbus-x11 \
    xterm \
    curl \
    wget \
    ca-certificates \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/.fluxbox && \
    echo "[begin] (Fluxbox)" > /root/.fluxbox/menu && \
    echo "[exec] (Terminal) {xterm}" >> /root/.fluxbox/menu && \
    echo "[exec] (Chromium) {chromium-browser --no-sandbox}" >> /root/.fluxbox/menu && \
    echo "[end]" >> /root/.fluxbox/menu

COPY start.sh /start.sh
RUN sed -i 's/\r$//' /start.sh && chmod +x /start.sh

EXPOSE 6080

CMD ["/start.sh"]
