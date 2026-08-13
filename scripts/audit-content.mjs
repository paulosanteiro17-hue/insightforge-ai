import { readdir, readFile } from "node:fs/promises";
import { extname, relative, resolve } from "node:path";
import process from "node:process";

const repositoryRoot = resolve(import.meta.dirname, "..");
const scanRoots = [
  "README.md",
  "CONTRIBUTING.md",
  ".env.example",
  "apps/web/src",
  "apps/web/e2e",
  "apps/api/src",
  "apps/api/tests",
  "data",
  "docs",
];
const textExtensions = new Set([
  ".csv",
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
const ignoredDirectories = new Set([
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

const languagePatterns = [
  {
    label: "Portuguese product copy",
    expression:
      /\b(?:adicionar|atualizar|cancelar|carregando|cliente|clientes|cobrança|configurações|dados|entrar|equipe|excluir|falha|faturamento|nenhum|pedido|pedidos|produto|produtos|receita|relatório|relatórios|salvar|senha|sair|segurança|usuário|usuários)\b/iu,
  },
  {
    label: "Invalid or mojibake text encoding",
    expression: /(?:\uFFFD|Â|Ã|â€)/u,
  },
];
const productPlaceholderPattern = /\b(?:TODO|Coming soon|Lorem ipsum)\b/iu;

async function collectFiles(target) {
  const absoluteTarget = resolve(repositoryRoot, target);
  const entries = await readdir(absoluteTarget, { withFileTypes: true }).catch(
    () => null,
  );
  if (entries === null) return [absoluteTarget];

  const files = [];
  for (const entry of entries) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
    const child = resolve(absoluteTarget, entry.name);
    if (entry.isDirectory())
      files.push(...(await collectFiles(relative(repositoryRoot, child))));
    else files.push(child);
  }
  return files;
}

function shouldRead(file) {
  if (file.endsWith(".env.example")) return true;
  return textExtensions.has(extname(file).toLowerCase());
}

const findings = [];
const files = (await Promise.all(scanRoots.map(collectFiles)))
  .flat()
  .filter(shouldRead)
  .sort();

for (const file of files) {
  const content = await readFile(file, "utf8");
  const displayPath = relative(repositoryRoot, file).replaceAll("\\", "/");
  const isProductSource =
    displayPath.startsWith("apps/") || displayPath.startsWith("data/");

  for (const [index, line] of content.split(/\r?\n/u).entries()) {
    for (const pattern of languagePatterns) {
      if (pattern.expression.test(line)) {
        findings.push(`${displayPath}:${index + 1}: ${pattern.label}`);
      }
    }
    if (isProductSource && productPlaceholderPattern.test(line)) {
      findings.push(`${displayPath}:${index + 1}: Unfinished placeholder copy`);
    }
  }
}

if (findings.length > 0) {
  process.stderr.write(
    `Content audit failed with ${findings.length} finding(s):\n${findings.join("\n")}\n`,
  );
  process.exitCode = 1;
} else {
  process.stdout.write(
    `Content audit passed for ${files.length} English UTF-8 text files.\n`,
  );
}
