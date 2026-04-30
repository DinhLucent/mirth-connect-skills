#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const root = process.cwd();

const requiredFiles = [
  "mirth-agent-tools/pyproject.toml",
  "mirth-agent-tools/.env.example",
  "mirth-connect-operator/SKILL.md",
  "mirth-connect-operator/agents/openai.yaml",
  ".claude-plugin/plugin.json",
  "README.md",
  "bin/mirth-connect-skills.js",
  "package.json",
  "scripts/audit-format.js",
  "scripts/local-check.js"
];

for (const file of fs.readdirSync(path.join(root, "mirth-agent-tools", "src", "mirth_agent_tools"))) {
  if (file.endsWith(".py")) {
    requiredFiles.push(path.join("mirth-agent-tools", "src", "mirth_agent_tools", file));
  }
}

for (const file of fs.readdirSync(path.join(root, "mirth-agent-tools", "tests"))) {
  if (file.endsWith(".py")) {
    requiredFiles.push(path.join("mirth-agent-tools", "tests", file));
  }
}

if (fs.existsSync(path.join(root, "tests"))) {
  for (const file of fs.readdirSync(path.join(root, "tests"))) {
    if (file.endsWith(".py") || file.endsWith(".md")) {
      requiredFiles.push(path.join("tests", file));
    }
  }
}

const failures = [];

for (const relativePath of requiredFiles) {
  const fullPath = path.join(root, relativePath);
  if (!fs.existsSync(fullPath)) {
    failures.push(`${relativePath}: missing`);
    continue;
  }

  const text = fs.readFileSync(fullPath, "utf8");
  if (!text.includes("\n")) {
    failures.push(`${relativePath}: no LF newline`);
  }
  if (/\r\n|\r/.test(text)) {
    failures.push(`${relativePath}: contains CRLF/CR`);
  }
}

const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
if (!packageJson.scripts?.check || !packageJson.scripts?.audit || !packageJson.scripts?.test) {
  failures.push("package.json: missing check/audit/test scripts");
}

const readme = fs.readFileSync(path.join(root, "README.md"), "utf8");
const readmeExpectations = [
  ".agents/skills/mirth-connect-operator",
  "~/.agents/skills/mirth-connect-operator",
  "/etc/codex/skills/mirth-connect-operator",
  "--legacy-codex",
  "npm run check"
];
for (const expected of readmeExpectations) {
  if (!readme.includes(expected)) {
    failures.push(`README.md: missing ${expected}`);
  }
}

if (readme.includes(".github/workflows/ci.yml")) {
  failures.push("README.md: still references GitHub Actions workflow");
}

if (fs.existsSync(path.join(root, ".github", "workflows", "ci.yml"))) {
  failures.push(".github/workflows/ci.yml: workflow file should not exist");
}

const openaiYaml = fs.readFileSync(path.join(root, "mirth-connect-operator", "agents", "openai.yaml"), "utf8");
for (const expected of ["interface:", "policy:", "dependencies:", "type: \"mcp\"", "value: \"mirth-agent-tools\""]) {
  if (!openaiYaml.includes(expected)) {
    failures.push(`agents/openai.yaml: missing ${expected}`);
  }
}

const installer = fs.readFileSync(path.join(root, "bin", "mirth-connect-skills.js"), "utf8");
for (const expected of [".agents", "/etc/codex", ".codex", "--legacy-codex"]) {
  if (!installer.includes(expected)) {
    failures.push(`bin/mirth-connect-skills.js: missing ${expected}`);
  }
}

if (failures.length) {
  console.error("Audit failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(`Audit passed: ${requiredFiles.length} required files are LF-only and install paths match README.`);
