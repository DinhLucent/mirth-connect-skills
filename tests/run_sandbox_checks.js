#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { performance } from "node:perf_hooks";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const installer = path.join(root, "bin", "mirth-connect-skills.js");
const sandboxRoot = path.join(root, "tests", ".sandboxes");
const reportsDir = path.join(root, "tests", "reports");
const keepSandboxes = process.argv.includes("--keep");

const results = [];

main();

function main() {
  removeInsideWorkspace(sandboxRoot);
  fs.mkdirSync(sandboxRoot, { recursive: true });
  fs.mkdirSync(reportsDir, { recursive: true });

  runScenario("project init installs skill and root tools", () => {
    const target = path.join(sandboxRoot, "project-init");
    runInstaller(["init", "--target", target, "--force"]);
    assertFile(path.join(target, ".agents", "skills", "mirth-connect-operator", "SKILL.md"));
    assertFile(path.join(target, "mirth-agent-tools", "pyproject.toml"));
    assertFile(path.join(target, "mirth-agent-tools", "src", "mirth_agent_tools", "tools.py"));
    assertMissing(path.join(target, "mirth-agent-tools", ".env"));
    assertMissing(path.join(target, ".mirth"));
  });

  runScenario("project init supports hidden .mirth runtime", () => {
    const target = path.join(sandboxRoot, "dot-mirth-init");
    runInstaller(["init", "--target", target, "--mirth-dir", ".mirth", "--create-env", "--force"]);
    assertFile(path.join(target, ".agents", "skills", "mirth-connect-operator", "SKILL.md"));
    assertFile(path.join(target, ".mirth", "mirth-agent-tools", "pyproject.toml"));
    assertFile(path.join(target, ".mirth", "mirth-agent-tools", ".env"));
    assertFile(path.join(target, ".mirth", ".gitignore"));
    assertMissing(path.join(target, "mirth-agent-tools"));
    assertTextIncludes(path.join(target, ".mirth", ".gitignore"), "mirth-agent-tools/.env");
    run("python", ["-m", "compileall", "src"], {
      cwd: path.join(target, ".mirth", "mirth-agent-tools"),
      quiet: true
    });
  });

  runScenario("full command defaults tools to .mirth in dry-run", () => {
    const target = path.join(sandboxRoot, "full-dry-run");
    const output = runInstaller(["full", "--target", target, "--dry-run"], { capture: true });
    const normalized = output.replaceAll("\\", "/");
    assertIncludes(normalized, "/.mirth/mirth-agent-tools");
    assertIncludes(normalized, "/.agents/skills/mirth-connect-operator");
    assertMissing(target);
  });

  runScenario("legacy skill-only install writes .agents and .codex", () => {
    const target = path.join(sandboxRoot, "legacy-skill-only");
    runInstaller(["init", "--target", target, "--legacy-codex", "--skip-tools", "--force"]);
    assertFile(path.join(target, ".agents", "skills", "mirth-connect-operator", "SKILL.md"));
    assertFile(path.join(target, ".codex", "skills", "mirth-connect-operator", "SKILL.md"));
    assertMissing(path.join(target, "mirth-agent-tools"));
  });

  runScenario("installer is force-safe and rejects accidental overwrite", () => {
    const target = path.join(sandboxRoot, "idempotency");
    runInstaller(["init", "--target", target]);
    const output = runInstaller(["init", "--target", target], {
      capture: true,
      expectStatus: 1
    });
    assertIncludes(output, "Use --force to overwrite it.");
    runInstaller(["init", "--target", target, "--force"]);
    assertFile(path.join(target, ".agents", "skills", "mirth-connect-operator", "SKILL.md"));
  });

  runScenario("npm package includes runtime files and excludes artifacts", () => {
    const output = runNpm(["pack", "--dry-run", "--json"], { capture: true });
    const packResult = JSON.parse(output)[0];
    const files = packResult.files.map((file) => file.path.replaceAll("\\", "/"));
    assertIncludes(files.join("\n"), ".claude-plugin/plugin.json");
    assertIncludes(files.join("\n"), "tests/run_sandbox_checks.js");
    assertIncludes(files.join("\n"), "mirth-agent-tools/src/mirth_agent_tools/tools.py");
    assertExcludesExact(files, "mirth-agent-tools/.env");
    assertExcludes(files, "tests/.sandboxes/");
    assertExcludes(files, "tests/reports/latest-");
    assertExcludes(files, "__pycache__");
  });

  runScenario("invalid .mirth path is rejected", () => {
    const output = runInstaller(["init", "--target", path.join(sandboxRoot, "invalid"), "--mirth-dir", ".."], {
      capture: true,
      expectStatus: 1
    });
    assertIncludes(output, "--mirth-dir must stay inside the project directory");
  });

  runScenario("global install rejects project-local .mirth runtime", () => {
    const output = runInstaller(["init", "--global", "--mirth-dir", ".mirth"], {
      capture: true,
      expectStatus: 1
    });
    assertIncludes(output, "--mirth-dir and --dot-mirth are only valid for project installs");
  });

  if (!keepSandboxes) {
    removeInsideWorkspace(sandboxRoot);
  }

  const failed = results.filter((result) => !result.ok);
  const report = {
    generated_at: new Date().toISOString(),
    total: results.length,
    passed: results.length - failed.length,
    failed: failed.length,
    results
  };
  const reportPath = path.join(reportsDir, "latest-sandbox-check.json");
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");

  console.log(JSON.stringify({
    failed: report.failed,
    passed: report.passed,
    total: report.total,
    report: reportPath
  }, null, 2));

  if (failed.length) {
    process.exit(1);
  }
}

function runScenario(name, fn) {
  const start = performance.now();
  try {
    fn();
    results.push({
      name,
      ok: true,
      duration_ms: round(performance.now() - start)
    });
  } catch (error) {
    results.push({
      name,
      ok: false,
      duration_ms: round(performance.now() - start),
      error: error instanceof Error ? error.message : String(error)
    });
  }
}

function runInstaller(args, options = {}) {
  return run("node", [installer, ...args], options);
}

function runNpm(args, options = {}) {
  if (process.platform === "win32") {
    return run("cmd.exe", ["/d", "/s", "/c", "npm", ...args], options);
  }
  return run("npm", args, options);
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || root,
    encoding: "utf8",
    stdio: options.capture || options.quiet ? "pipe" : "inherit"
  });
  const output = `${result.stdout || ""}${result.stderr || ""}`;
  const expectedStatus = options.expectStatus ?? 0;
  if (result.status !== expectedStatus) {
    throw new Error([
      `Expected ${command} ${args.join(" ")} to exit ${expectedStatus}, got ${result.status}.`,
      output.trim()
    ].filter(Boolean).join("\n"));
  }
  return output;
}

function assertFile(filePath) {
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    throw new Error(`Expected file to exist: ${filePath}`);
  }
}

function assertMissing(filePath) {
  if (fs.existsSync(filePath)) {
    throw new Error(`Expected path to be absent: ${filePath}`);
  }
}

function assertTextIncludes(filePath, expected) {
  assertIncludes(fs.readFileSync(filePath, "utf8"), expected);
}

function assertIncludes(text, expected) {
  if (!text.includes(expected)) {
    throw new Error(`Expected text to include ${expected}`);
  }
}

function assertExcludes(values, unexpected) {
  const found = values.find((value) => value.includes(unexpected));
  if (found) {
    throw new Error(`Expected package files to exclude ${unexpected}, found ${found}`);
  }
}

function assertExcludesExact(values, unexpected) {
  if (values.includes(unexpected)) {
    throw new Error(`Expected package files to exclude ${unexpected}`);
  }
}

function removeInsideWorkspace(target) {
  if (!fs.existsSync(target)) {
    return;
  }
  const resolvedRoot = root.toLowerCase();
  const resolvedTarget = path.resolve(target).toLowerCase();
  if (!resolvedTarget.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error(`Refusing to remove outside workspace: ${target}`);
  }
  fs.rmSync(target, { recursive: true, force: true });
}

function round(value) {
  return Math.round(value * 1000) / 1000;
}
