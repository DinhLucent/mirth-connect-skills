#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import path from "node:path";

const root = process.cwd();

const checks = [
  {
    name: "format/install-path audit",
    command: "node",
    args: ["scripts/audit-format.js"],
    cwd: root
  },
  {
    name: "python compileall",
    command: "python",
    args: ["-m", "compileall", "mirth-agent-tools/src"],
    cwd: root
  },
  {
    name: "editable install with dev,mcp",
    command: "python",
    args: ["-m", "pip", "install", "-e", ".[dev,mcp]"],
    cwd: path.join(root, "mirth-agent-tools")
  },
  {
    name: "pytest",
    command: "python",
    args: ["-m", "pytest"],
    cwd: path.join(root, "mirth-agent-tools")
  },
  {
    name: "skill tool effectiveness evaluation",
    command: "python",
    args: ["tests/run_tool_evaluation.py", "--iterations", "5"],
    cwd: root
  },
  {
    name: "npx installer dry-run",
    command: "node",
    args: ["bin/mirth-connect-skills.js", "init", "--target", ".npx-smoke", "--dry-run"],
    cwd: root
  },
  {
    name: "npm pack dry-run",
    command: "npm",
    args: ["pack", "--dry-run"],
    cwd: root
  }
];

for (const check of checks) {
  console.log(`\n==> ${check.name}`);
  const invocation = resolveInvocation(check.command, check.args);
  const result = spawnSync(invocation.command, invocation.args, {
    cwd: check.cwd,
    stdio: "inherit"
  });

  if (result.status !== 0) {
    console.error(`\nCheck failed: ${check.name}`);
    process.exit(result.status || 1);
  }
}

console.log("\nAll local checks passed.");

function resolveInvocation(command, args) {
  if (process.platform === "win32" && command === "npm") {
    return {
      command: "cmd.exe",
      args: ["/d", "/s", "/c", "npm", ...args]
    };
  }

  return { command, args };
}
