import { execSync, type ExecSyncOptions, type ExecSyncOptionsWithStringEncoding } from "child_process";
import type { HostingTarget, DeployRunnerResult, DeployOutcome, PreflightResult } from "./types.js";

// ─── CLI metadata per target ──────────────────────────────────────────────────

const CLI_COMMANDS: Record<HostingTarget, string> = {
  railway: "railway up",
  render: "curl -X POST $RENDER_DEPLOY_HOOK_URL",
  fly: "flyctl deploy --remote-only",
  custom: "", // user provides custom script
};

const CLI_INSTALL_INSTRUCTIONS: Record<HostingTarget, string> = {
  railway: "Install Railway CLI: npm install -g @railway/cli && railway login",
  render: "Render uses deploy hooks — no CLI install required. Set RENDER_DEPLOY_HOOK_URL in .env",
  fly: "Install Fly CLI: curl -L https://fly.io/install.sh | sh && fly auth login",
  custom: "No CLI required for custom deployment",
};

const CLI_BINARIES: Record<HostingTarget, string> = {
  railway: "railway",
  render: "curl",   // curl is always available on Linux/macOS
  fly: "flyctl",
  custom: "",       // no check needed
};

// Required secrets per platform — validates credentials before any deploy attempt
const REQUIRED_SECRETS: Record<HostingTarget, string[]> = {
  railway: ["RAILWAY_TOKEN"],
  render: ["RENDER_DEPLOY_HOOK_URL"],
  fly: ["FLY_API_TOKEN"],
  custom: [],
};

// ─── checkCLIAvailable ────────────────────────────────────────────────────────

// Check whether the platform CLI binary is accessible in PATH.
// Uses injectable execFn for test isolation (same pattern as migration-runner).
export function checkCLIAvailable(
  target: HostingTarget,
  execFn: typeof execSync = execSync,
): boolean {
  // Custom deployments have no dedicated CLI to check
  if (target === "custom") return true;

  const binary = CLI_BINARIES[target];
  if (!binary) return true;

  // Windows uses `where`, Unix uses `which`
  const whichCmd = process.platform === "win32" ? `where ${binary}` : `which ${binary}`;

  try {
    execFn(whichCmd, { stdio: "ignore" } satisfies ExecSyncOptions);
    return true;
  } catch {
    return false;
  }
}

// ─── preflightDeploy ──────────────────────────────────────────────────────────

// Validate secrets and CLI availability before any deploy attempt.
// Addresses review concern: credential/config validation must occur before execution.
export function preflightDeploy(
  target: HostingTarget,
  env: Record<string, string | undefined>,
  execFn: typeof execSync = execSync,
): PreflightResult {
  const missingSecrets: string[] = [];
  const missingCLI: string[] = [];
  const warnings: string[] = [];

  // Check required secrets for this platform
  for (const secret of REQUIRED_SECRETS[target]) {
    if (!env[secret]) {
      missingSecrets.push(secret);
    }
  }

  // Check CLI availability for non-custom targets
  if (target !== "custom") {
    const cliAvailable = checkCLIAvailable(target, execFn);
    if (!cliAvailable) {
      missingCLI.push(CLI_BINARIES[target]);
      warnings.push(CLI_INSTALL_INSTRUCTIONS[target]);
    }
  }

  const ready = missingSecrets.length === 0 && missingCLI.length === 0;

  return { ready, missingSecrets, missingCLI, warnings };
}

// ─── runDeploy ────────────────────────────────────────────────────────────────

// Execute deployment with preflight validation and explicit confirmation gate.
// Returns structured DeployOutcome: skipped | deployed | failed-preflight | failed-runtime
// Per D-14 (dual gate) and D-17 (full execution). Addresses review: structured outcomes.
export function runDeploy(
  target: HostingTarget,
  confirmed: boolean,
  options?: {
    customScript?: string;
    cwd?: string;
    env?: Record<string, string | undefined>;
  },
  execFn: typeof execSync = execSync,
): DeployRunnerResult {
  // Gate 1: explicit user confirmation required before any execution
  if (!confirmed) {
    return { target, outcome: "skipped", confirmed: false, executed: false };
  }

  const deployEnv = options?.env ?? process.env;

  // Gate 2: preflight validation — secrets and CLI must be ready
  const preflight = preflightDeploy(target, deployEnv, execFn);
  if (!preflight.ready) {
    const errorParts: string[] = [
      ...preflight.missingSecrets.map(s => `Missing secret: ${s}`),
      ...preflight.missingCLI.map(c => `Missing CLI: ${c}. ${CLI_INSTALL_INSTRUCTIONS[target]}`),
    ];
    return {
      target,
      outcome: "failed-preflight",
      confirmed: true,
      executed: false,
      error: "Preflight failed: " + errorParts.join("; "),
    };
  }

  // Determine command to execute
  let command: string;
  if (target === "custom") {
    command = options?.customScript ?? "echo 'No custom script provided'";
  } else {
    command = CLI_COMMANDS[target];
  }

  // Resolve render deploy hook URL from environment
  if (target === "render") {
    const hookUrl = (deployEnv as Record<string, string | undefined>)["RENDER_DEPLOY_HOOK_URL"] ?? "";
    command = command.replace("$RENDER_DEPLOY_HOOK_URL", hookUrl);
  }

  // Execute the deploy command
  try {
    const execOpts: ExecSyncOptionsWithStringEncoding = {
      cwd: options?.cwd,
      env: { ...process.env, ...options?.env } as NodeJS.ProcessEnv,
      stdio: "pipe",
      encoding: "utf-8",
    };
    const output = execFn(command, execOpts).toString();

    return { target, outcome: "deployed", confirmed: true, executed: true, output };
  } catch (error) {
    return {
      target,
      outcome: "failed-runtime",
      confirmed: true,
      executed: false,
      error: (error as Error).message,
    };
  }
}
