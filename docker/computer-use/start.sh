#!/bin/bash
set -e

Xvfb :1 -screen 0 ${RESOLUTION} &
sleep 1

fluxbox &
sleep 0.5

x11vnc -display :1 -forever -nopw -rfbport ${VNC_PORT} -shared &
sleep 0.5

websockify --web /usr/share/novnc ${NOVNC_PORT} localhost:${VNC_PORT}
