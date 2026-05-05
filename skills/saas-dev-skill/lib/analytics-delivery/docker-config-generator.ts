import type { DeployConfig, HostingTarget } from "./types.js";

// Multi-stage Dockerfile — same for all hosting targets (D-09)
// Stage 1 builds Vite client + esbuild server, Stage 2 runs production artifacts.
// curl installed in runner stage for HEALTHCHECK support (node:20-slim has no curl).
// PORT env var defaults to 5000 for local dev; Railway/Render/Fly.io override at runtime.
const DOCKERFILE = `# Stage 1: Build
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Run
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=5000
COPY package*.json ./
RUN npm ci --omit=dev
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/dist ./dist
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:\${PORT}/health || exit 1
CMD ["node", "dist/index.js"]
`;

// .dockerignore — applied to all targets to keep images lean (addresses Codex review)
const DOCKERIGNORE = `node_modules
dist
.git
.env
.env.*
*.md
.planning
.claude
tests
coverage
.github
`;

// Platform config for Railway — uses DOCKERFILE builder (not NIXPACKS) when Dockerfile is present
const RAILWAY_TOML = `[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "node dist/index.js"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
`;

// Platform config for Render — docker runtime with health check path
const RENDER_YAML = `services:
  - type: web
    name: app
    runtime: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: NODE_ENV
        value: production
      - key: PORT
        value: 5000
    healthCheckPath: /health
`;

// Platform config for Fly.io — internal port, HTTPS enforcement, auto-scaling
const FLY_TOML = `[build]

[http_service]
  internal_port = 5000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
`;

// docker-compose.yml for custom target — no platform config generated
const DOCKER_COMPOSE = `version: "3.8"
services:
  app:
    build: .
    ports:
      - "5000:5000"
    env_file:
      - .env
    restart: unless-stopped
`;

// generateDockerConfig produces a complete DeployConfig for the given hosting target.
// All targets receive the same multi-stage Dockerfile and .dockerignore.
// Platform-specific config differs by target; custom target gets docker-compose instead.
export function generateDockerConfig(target: HostingTarget): DeployConfig {
  switch (target) {
    case "railway":
      return {
        target,
        dockerfile: DOCKERFILE,
        dockerignore: DOCKERIGNORE,
        platformConfig: RAILWAY_TOML,
        platformConfigFilename: "railway.toml",
      };

    case "render":
      return {
        target,
        dockerfile: DOCKERFILE,
        dockerignore: DOCKERIGNORE,
        platformConfig: RENDER_YAML,
        platformConfigFilename: "render.yaml",
      };

    case "fly":
      return {
        target,
        dockerfile: DOCKERFILE,
        dockerignore: DOCKERIGNORE,
        platformConfig: FLY_TOML,
        platformConfigFilename: "fly.toml",
      };

    case "custom":
      return {
        target,
        dockerfile: DOCKERFILE,
        dockerignore: DOCKERIGNORE,
        platformConfig: "",
        platformConfigFilename: "",
        dockerCompose: DOCKER_COMPOSE,
      };
  }
}

// generateHostingMenu returns the interactive hosting options shown to the user (D-07/D-08).
// Each entry includes trade-offs so the user can make an informed choice.
export function generateHostingMenu(): Array<{
  target: HostingTarget;
  name: string;
  pros: string;
  cons: string;
}> {
  return [
    {
      target: "railway",
      name: "Railway",
      pros: "Git push deploy, auto-scaling, generous free tier",
      cons: "Usage-based pricing can spike",
    },
    {
      target: "render",
      name: "Render",
      pros: "Simple dashboard, free tier for web services, auto-deploy from GitHub",
      cons: "Cold starts on free tier, slower builds",
    },
    {
      target: "fly",
      name: "Fly.io",
      pros: "Edge deployment, excellent performance, generous free allowance",
      cons: "More complex setup, CLI-driven",
    },
    {
      target: "custom",
      name: "Custom (Docker only)",
      pros: "Full control, any hosting provider, self-managed",
      cons: "No auto-deploy, manual infrastructure management",
    },
  ];
}
