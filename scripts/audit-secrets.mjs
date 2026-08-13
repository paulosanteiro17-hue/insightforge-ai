import { readdir, readFile } from "node:fs/promises";
import { extname, relative, resolve } from "node:path";
import process from "node:process";

const repositoryRoot = resolve(import.meta.dirname, "..");
const ignoredDirectories = new Set([
  ".git",
  ".mypy_cache",
  ".next",
  ".pytest_cache",
  ".ruff_cache",
  ".venv",
  "__pycache__",
  "coverage",
  "dist",
  "node_modules",
  "playwright-report",
  "test-results",
]);
const ignoredFiles = new Set(["package-lock.json", "uv.lock"]);
const textExtensions = new Set([
  ".csv",
  ".env",
  ".example",
  ".json",
  ".md",
  ".mjs",
  ".py",
  ".toml",
  ".ts",
  ".tsx",
  ".txt",
  ".yaml",
  ".yml",
]);

const credentialPatterns = [
  ["private key", /-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----/u],
  ["OpenAI API key", /\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b/u],
  ["GitHub token", /\bgh[pousr]_[A-Za-z0-9]{20,}\b/u],
  ["AWS access key", /\b(?:AKIA|ASIA)[A-Z0-9]{16}\b/u],
  ["Google API key", /\bAIza[A-Za-z0-9_-]{30,}\b/u],
  ["Slack token", /\bxox[baprs]-[A-Za-z0-9-]{20,}\b/u],
  ["Stripe live key", /\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b/u],
  [
    "encoded JWT",
    /\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b/u,
  ],
];

function shouldRead(file) {
  const name = file.split(/[\\/]/u).at(-1) ?? "";
  if (ignoredFiles.has(name)) return false;
  if (name === ".env" || name.startsWith(".env.")) return true;
  return textExtensions.has(extname(file).toLowerCase());
}

async function collectFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
    const child = resolve(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await collectFiles(child)));
    else if (shouldRead(child)) files.push(child);
  }
  return files;
}

const findings = [];
const files = (await collectFiles(repositoryRoot)).sort();

for (const file of files) {
  const content = await readFile(file, "utf8");
  const displayPath = relative(repositoryRoot, file).replaceAll("\\", "/");
  for (const [lineIndex, line] of content.split(/\r?\n/u).entries()) {
    for (const [label, expression] of credentialPatterns) {
      if (expression.test(line)) {
        findings.push(`${displayPath}:${lineIndex + 1}: possible ${label}`);
      }
    }
  }
}

if (findings.length > 0) {
  process.stderr.write(
    `Secret audit failed with ${findings.length} finding(s). Values are intentionally redacted:\n${findings.join("\n")}\n`,
  );
  process.exitCode = 1;
} else {
  process.stdout.write(
    `Secret audit passed for ${files.length} repository text files.\n`,
  );
}
