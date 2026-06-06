FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY . .

ARG VITE_CLERK_PUBLISHABLE_KEY
ARG VITE_API_URL=/api/umh
ARG VITE_AI_NAME=DEX
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_AI_NAME=$VITE_AI_NAME

RUN npx vite build --config vite.web.config.ts

FROM nginx:alpine
RUN apk add --no-cache tailscale socat

COPY --from=build /app/dist-web /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8080
CMD ["/start.sh"]
