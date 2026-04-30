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

  if (command === "full") {
    options.installPython = true;
    options.installMcp = true;
    options.createEnv = true;
    if (!options.global && !options.admin && !options.mirthDir) {
      options.mirthDir = ".mirth";
    }
  } else if (command !== "init") {
    fail(`Unknown command: ${command}`);
  }

  install(options);
}

function parseOptions(argv) {
  const options = {
    target: process.cwd(),
    global: false,
    admin: false,
    force: false,
    skipTools: false,
    legacyCodex: false,
    dryRun: false,
    installPython: false,
    installMcp: false,
    createEnv: false,
    mirthDir: null,
    python: process.env.PYTHON || "python",
    help: false
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--target") {
      options.target = requireValue(argv, ++index, "--target");
    } else if (arg === "--global" || arg === "-g") {
      options.global = true;
    } else if (arg === "--admin") {
      options.admin = true;
    } else if (arg === "--force" || arg === "-f") {
      options.force = true;
    } else if (arg === "--legacy-codex") {
      options.legacyCodex = true;
    } else if (arg === "--skip-tools") {
      options.skipTools = true;
    } else if (arg === "--dry-run") {
      options.dryRun = true;
    } else if (arg === "--install-python") {
      options.installPython = true;
    } else if (arg === "--install-mcp") {
      options.installMcp = true;
    } else if (arg === "--create-env") {
      options.createEnv = true;
    } else if (arg === "--dot-mirth") {
      options.mirthDir = ".mirth";
    } else if (arg === "--mirth-dir") {
      options.mirthDir = normalizeProjectRelativePath(requireValue(argv, ++index, "--mirth-dir"), "--mirth-dir");
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
  if (options.global && options.admin) {
    fail("Choose only one of --global or --admin.");
  }
  if ((options.global || options.admin) && options.mirthDir) {
    fail("--mirth-dir and --dot-mirth are only valid for project installs.");
  }

  const sourceSkill = path.join(packageRoot, skillName);
  const sourceTools = path.join(packageRoot, toolName);
  assertDirectory(sourceSkill);
  assertDirectory(sourceTools);

  const userAgentsHome = path.join(os.homedir(), ".agents");
  const adminCodexHome = "/etc/codex";
  const targetRoot = options.admin ? adminCodexHome : path.resolve(options.global ? userAgentsHome : options.target);
  const skillDest = options.admin
    ? path.posix.join(targetRoot, "skills", skillName)
    : options.global
      ? path.join(targetRoot, "skills", skillName)
      : path.join(targetRoot, ".agents", "skills", skillName);
  const legacySkillDest = options.legacyCodex
    ? options.global
      ? path.join(process.env.CODEX_HOME || path.join(os.homedir(), ".codex"), "skills", skillName)
      : path.join(path.resolve(options.target), ".codex", "skills", skillName)
    : null;
  const toolsDest = options.admin
    ? path.posix.join(targetRoot, toolName)
    : options.global
      ? path.join(targetRoot, "tools", toolName)
      : options.mirthDir
        ? path.join(targetRoot, options.mirthDir, toolName)
        : path.join(targetRoot, toolName);

  copyDirectory(sourceSkill, skillDest, options);
  if (legacySkillDest) {
    copyDirectory(sourceSkill, legacySkillDest, options);
  }
  if (!options.skipTools) {
    copyDirectory(sourceTools, toolsDest, options);
    if (options.mirthDir) {
      createRuntimeGitignore(path.join(targetRoot, options.mirthDir), options);
    }
    if (options.createEnv) {
      createEnvFile(toolsDest, options);
    }
  }

  if (options.installPython && !options.skipTools && !options.dryRun) {
    installPythonPackage(options.python, toolsDest, options.installMcp);
  }

  console.log("");
  console.log("Mirth Connect skill installed.");
  console.log(`Skill: ${skillDest}`);
  if (legacySkillDest) {
    console.log(`Legacy skill: ${legacySkillDest}`);
  }
  if (!options.skipTools) {
    console.log(`Tools: ${toolsDest}`);
  }
  console.log("");
  printNextSteps(options, toolsDest);
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

function installPythonPackage(python, toolsDest, installMcp) {
  const extras = installMcp ? ".[dev,mcp]" : ".[dev]";
  const result = spawnSync(python, ["-m", "pip", "install", "-e", extras], {
    cwd: toolsDest,
    stdio: "inherit",
    shell: false
  });
  if (result.status !== 0) {
    fail(`Python package install failed with exit code ${result.status}.`);
  }
}

function createEnvFile(toolsDest, options) {
  const source = path.join(toolsDest, ".env.example");
  const dest = path.join(toolsDest, ".env");

  if (options.dryRun) {
    console.log(`[dry-run] copy ${source} -> ${dest}`);
    return;
  }

  if (!fs.existsSync(source)) {
    fail(`Cannot create .env because .env.example is missing: ${source}`);
  }

  if (fs.existsSync(dest)) {
    console.log(`Env file already exists, leaving it unchanged: ${dest}`);
    return;
  }

  fs.copyFileSync(source, dest);
  console.log(`Created env file: ${dest}`);
}

function createRuntimeGitignore(runtimeDir, options) {
  const dest = path.join(runtimeDir, ".gitignore");
  const content = [
    "# Generated by mirth-connect-skills.",
    "mirth-agent-tools/.env",
    "mirth-agent-tools/backups/*",
    "!mirth-agent-tools/backups/.gitkeep",
    "mirth-agent-tools/logs/*",
    "!mirth-agent-tools/logs/.gitkeep",
    ""
  ].join("\n");

  if (options.dryRun) {
    console.log(`[dry-run] write ${dest}`);
    return;
  }

  if (fs.existsSync(dest)) {
    console.log(`Runtime gitignore already exists, leaving it unchanged: ${dest}`);
    return;
  }

  fs.mkdirSync(runtimeDir, { recursive: true });
  fs.writeFileSync(dest, content, "utf8");
  console.log(`Created runtime gitignore: ${dest}`);
}

function printNextSteps(options, toolsDest) {
  if (options.skipTools) {
    console.log("Next: configure an MCP/tool server separately for the Mirth REST tools.");
    return;
  }

  console.log("Next steps:");
  console.log(`  cd "${toolsDest}"`);
  if (!options.installPython) {
    console.log('  python -m pip install -e ".[dev]"');
    console.log('  # optional MCP server: python -m pip install -e ".[mcp]"');
  }
  if (!options.createEnv) {
    console.log("  copy .env.example .env");
  } else {
    console.log("  # edit .env with your Mirth URL and credentials");
  }
  console.log("  mirth-agent-tools health_check");
  if (options.global) {
    console.log("");
    console.log("Global skill install used ~/.agents/skills.");
  }
}

function printHelp() {
  console.log(`Mirth Connect Skills

Usage:
  mirth-connect-skills init [options]
  mirth-connect-skills full [options]
  mirth-skills init [options]
  mirth-skills full [options]

Options:
  --target <dir>      Project directory for project install. Default: current directory.
  --global, -g        Install into ~/.agents/skills for the current user.
  --admin             Install skill into /etc/codex/skills.
  --force, -f         Overwrite existing destination directories.
  --legacy-codex      Also copy skill to legacy .codex/skills location.
  --skip-tools        Install only the Codex skill.
  --install-python    Run python -m pip install -e ".[dev]" after copying tools.
  --install-mcp       With --install-python, include the optional MCP extra.
  --create-env        Copy .env.example to .env if .env does not exist.
  --mirth-dir <dir>   Project-local runtime directory. Example: .mirth.
  --dot-mirth         Alias for --mirth-dir .mirth.
  --python <cmd>      Python executable for --install-python. Default: python.
  --dry-run           Print planned copy operations without writing.
  --help, -h          Show this help.

Examples:
  npx github:DinhLucent/mirth-connect-skills init
  npx github:DinhLucent/mirth-connect-skills full
  npx github:DinhLucent/mirth-connect-skills init --mirth-dir .mirth --create-env
  npx github:DinhLucent/mirth-connect-skills init --global
  npx github:DinhLucent/mirth-connect-skills init --install-python --install-mcp --create-env
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

function normalizeProjectRelativePath(value, optionName) {
  if (path.isAbsolute(value)) {
    fail(`${optionName} must be relative to the project directory.`);
  }

  const normalized = path.normalize(value);
  if (!normalized || normalized === "." || normalized === ".." || normalized.startsWith(`..${path.sep}`)) {
    fail(`${optionName} must stay inside the project directory.`);
  }

  return normalized;
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
