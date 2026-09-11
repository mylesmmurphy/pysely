import { readFileSync, readdirSync, statSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { zipSync } from "fflate";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
const output = join(root, "docs/assets/intelligence");
const pyright = join(root, "playground/node_modules/pyright");

function filesUnder(directory, accept = () => true, base = directory) {
  const files = {};
  for (const name of readdirSync(directory)) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) Object.assign(files, filesUnder(path, accept, base));
    else if (accept(path)) files[relative(base, path)] = readFileSync(path);
  }
  return files;
}

function textFiles(directory, prefix) {
  const result = {};
  function visit(path) {
    for (const name of readdirSync(path)) {
      const child = join(path, name);
      if (statSync(child).isDirectory()) visit(child);
      else if (name.endsWith(".py") || name.endsWith(".pyi") || name === "py.typed") {
        result[`${prefix}/${relative(directory, child)}`] = readFileSync(child, "utf8");
      }
    }
  }
  visit(directory);
  return result;
}

mkdirSync(output, { recursive: true });
// Ship stdlib stubs only. The third-party `stubs/` tree is 4,600+ files the
// playground can never import, and inside the worker's in-memory filesystem
// it costs Pyright about 1.2 GB.
const typeshed = filesUnder(
  join(pyright, "packages/pyright-internal/typeshed-fallback"),
  path => !path.includes(`${sep}stubs${sep}`),
);
const typeshedArchive = zipSync(typeshed, {
  level: 9,
  mtime: new Date("1980-01-02T00:00:00Z"),
});
writeFileSync(join(output, "typeshed-fallback.zip"), typeshedArchive);

const userFiles = {
  ...textFiles(join(root, "src/pysely"), "site-packages/pysely"),
  "workspace/database.py": readFileSync(join(root, "docs/assets/examples/database.py"), "utf8"),
  "workspace/playground/__init__.pyi": readFileSync(join(root, "playground/__init__.pyi"), "utf8"),
};
const manifest = {
  pyselyVersion: "0.1.0.dev0",
  pyrightVersion: "1.1.413",
  pythonVersion: "3.11",
  pyodidePythonVersion: "3.14",
  sourceRevision: "71b0cbe75fb8c38b3278ef7c8db16d2f4492f592",
  schemaSha256: createHash("sha256").update(readFileSync(join(root, "docs/assets/examples/schema.py"))).digest("hex"),
  typeshed: {
    bytes: typeshedArchive.byteLength,
    sha256: createHash("sha256").update(typeshedArchive).digest("hex"),
  },
  files: userFiles,
};
writeFileSync(join(output, "manifest.json"), JSON.stringify(manifest));
