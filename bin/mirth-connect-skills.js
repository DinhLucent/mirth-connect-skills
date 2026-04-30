#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skillName = "mirth-connect-operator";
const toolName = "mirth-agent-tools";

const args = process.argv.slice(2);

main(args);

function main(argv) {
  const hasCommand = Boolean(argv[0] && !argv[0].startsWith("-"));
  const command = hasCommand ? argv[0] : "init";
  const options = parseOptions(hasCommand ? argv.slice(1) : argv);

  if (options.help || command === "help") {
    printHelp();
    return;
  }

  if (command !== "init") {
    fail(`Unknown command: ${command}`);
  }

  install(options);
}

function parseOptions(argv) {
  const options = {
    target: process.cwd(),
    global: false,
    force: false,
    skipTools: false,
    dryRun: false,
    installPython: false,
    python: process.env.PYTHON || "python",
    help: false
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--target") {
      options.target = requireValue(argv, ++index, "--target");
    } else if (arg === "--global" || arg === "-g") {
      options.global = true;
    } else if (arg === "--force" || arg === "-f") {
      options.force = true;
    } else if (arg === "--skip-tools") {
      options.skipTools = true;
    } else if (arg === "--dry-run") {
      options.dryRun = true;
    } else if (arg === "--install-python") {
      options.installPython = true;
    } else if (arg === "--python") {
      options.python = requireValue(argv, ++index, "--python");
    } else if (arg === "--help" || arg === "-h") {
      options.help = true;
    } else {
      fail(`Unknown option: ${arg}`);
    }
  }

  return options;
}

function install(options) {
  const sourceSkill = path.join(packageRoot, skillName);
  const sourceTools = path.join(packageRoot, toolName);
  assertDirectory(sourceSkill);
  assertDirectory(sourceTools);

  const codexHome = process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
  const targetRoot = path.resolve(options.global ? codexHome : options.target);
  const skillDest = options.global
    ? path.join(targetRoot, "skills", skillName)
    : path.join(targetRoot, ".codex", "skills", skillName);
  const toolsDest = options.global
    ? path.join(targetRoot, toolName)
    : path.join(targetRoot, toolName);

  copyDirectory(sourceSkill, skillDest, options);
  if (!options.skipTools) {
    copyDirectory(sourceTools, toolsDest, options);
  }

  if (options.installPython && !options.skipTools && !options.dryRun) {
    installPythonPackage(options.python, toolsDest);
  }

  console.log("");
  console.log("Mirth Connect skill installed.");
  console.log(`Skill: ${skillDest}`);
  if (!options.skipTools) {
    console.log(`Tools: ${toolsDest}`);
  }
  console.log("");
  printNextSteps(options.global, toolsDest, options.skipTools);
}

function copyDirectory(source, dest, options) {
  if (options.dryRun) {
    console.log(`[dry-run] copy ${source} -> ${dest}`);
    return;
  }

  if (fs.existsSync(dest)) {
    if (!options.force) {
      fail(`Destination already exists: ${dest}\nUse --force to overwrite it.`);
    }
    fs.rmSync(dest, { recursive: true, force: true });
  }

  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.cpSync(source, dest, {
    recursive: true,
    filter: (item) => {
      const basename = path.basename(item);
      return basename !== "__pycache__" && basename !== ".pytest_cache";
    }
  });
}

function installPythonPackage(python, toolsDest) {
  const result = spawnSync(python, ["-m", "pip", "install", "-e", ".[dev]"], {
    cwd: toolsDest,
    stdio: "inherit",
    shell: false
  });
  if (result.status !== 0) {
    fail(`Python package install failed with exit code ${result.status}.`);
  }
}

function printNextSteps(isGlobal, toolsDest, skipTools) {
  if (skipTools) {
    console.log("Next: configure an MCP/tool server separately for the Mirth REST tools.");
    return;
  }

  console.log("Next steps:");
  console.log(`  cd "${toolsDest}"`);
  console.log('  python -m pip install -e ".[dev]"');
  console.log("  copy .env.example .env");
  console.log("  mirth-agent-tools health_check");
  if (isGlobal) {
    console.log("");
    console.log("Global install used CODEX_HOME when set, otherwise ~/.codex.");
  }
}

function printHelp() {
  console.log(`Mirth Connect Skills

Usage:
  mirth-connect-skills init [options]
  mirth-skills init [options]

Options:
  --target <dir>      Project directory for project install. Default: current directory.
  --global, -g        Install into CODEX_HOME or ~/.codex.
  --force, -f         Overwrite existing destination directories.
  --skip-tools        Install only the Codex skill.
  --install-python    Run python -m pip install -e ".[dev]" after copying tools.
  --python <cmd>      Python executable for --install-python. Default: python.
  --dry-run           Print planned copy operations without writing.
  --help, -h          Show this help.

Examples:
  npx github:DinhLucent/mirth-connect-skills init
  npx github:DinhLucent/mirth-connect-skills init --global
  npm install -g github:DinhLucent/mirth-connect-skills
  mirth-connect-skills init --target ./my-project
`);
}

function requireValue(argv, index, optionName) {
  const value = argv[index];
  if (!value || value.startsWith("-")) {
    fail(`${optionName} requires a value.`);
  }
  return value;
}

function assertDirectory(dir) {
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
    fail(`Required package directory is missing: ${dir}`);
  }
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
