import type { HostingTarget } from "./types.js";

// Shared setup steps for both CI and CD jobs — checkout, Node 20 with npm cache, npm ci
function setupSteps(): string {
  return `      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
      - run: npm ci`;
}

// generateCIWorkflow produces .github/workflows/ci.yml content (D-12).
// Runs type-check + test + build on every PR push (not on main pushes).
export function generateCIWorkflow(): string {
  return `name: CI
on:
  push:
    branches-ignore: [main]
  pull_request:

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
${setupSteps()}
      - run: npm run check
      - run: npm test
      - run: npm run build
`;
}

// Platform-specific deploy steps for staging and production jobs
function deployStep(target: HostingTarget, env: "staging" | "production"): string {
  const envSuffix = env === "staging" ? "STAGING" : "PRODUCTION";

  switch (target) {
    case "railway":
      return `      - name: Deploy to Railway (${env})
        run: |
          npm install -g @railway/cli
          railway up --service \${{ secrets.RAILWAY_SERVICE_NAME_${envSuffix} }}
        env:
          RAILWAY_TOKEN: \${{ secrets.RAILWAY_TOKEN_${envSuffix} }}`;

    case "render":
      return `      - name: Deploy to Render (${env})
        # Render can auto-deploy from GitHub (recommended), or trigger via deploy hook below
        run: |
          curl -X POST \${{ secrets.RENDER_DEPLOY_HOOK_URL_${envSuffix} }}`;

    case "fly":
      return `      - name: Deploy to Fly.io (${env})
        run: |
          curl -L https://fly.io/install.sh | sh
          export PATH="\$HOME/.fly/bin:\$PATH"
          flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: \${{ secrets.FLY_API_TOKEN_${envSuffix} }}`;

    case "custom":
      return `      - name: Deploy (${env})
        run: |
          # Add your custom deploy command here
          # Example: docker build -t app . && docker push registry/app
          echo "Configure your custom deploy step"`;
  }
}

// generateCDWorkflow produces .github/workflows/cd.yml content (D-13/D-14).
// Triggers on push to main. Two jobs: deploy-staging (auto) then deploy-production
// (manual gate via GitHub environment protection rules — requires reviewers configured
// in repo Settings > Environments > production).
export function generateCDWorkflow(target: HostingTarget): string {
  return `name: CD
on:
  push:
    branches: [main]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
${setupSteps()}
      - run: npm run build
${deployStep(target, "staging")}

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
${setupSteps()}
      - run: npm run build
${deployStep(target, "production")}
`;
}
