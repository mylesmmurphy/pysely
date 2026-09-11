# Playground intelligence

The documentation playground runs Pyright 1.1.413 in a browser worker. Monaco
sends normal LSP requests to that worker; a separate Pyodide worker executes the
same example against the real Pysely package.

## Generated interface

`workspace/database.py` is what `pysely codegen` writes for the schema editor's
contents. The Pyodide worker regenerates it on every run and pushes it to
Pyright, so a column added in the schema pane is usable in the query pane at
once. The committed `docs/assets/examples/database.py` is only the starting
state; regenerate it with `pysely codegen docs/assets/examples/schema.py
--output docs/assets/examples/database.py`. CI fails when it drifts.

Pyright runs in `standard` mode, its default. `strict` adds unknown-type
follow-on errors across a chain after one failed call.

## Editor parity requirement

The playground must represent the Python editing experience users get in VS Code.
Use the same public schema types and stock language-server results. Do not mock
completions, rewrite diagnostic messages or ranges, group or hide cascading errors,
or add browser-only typing improvements. Investigate improvements in the Python
types or upstream checker and verify them with the stock local language server.
Preserve limitations when no sound portable fix exists. Runtime exceptions belong
in the execution output, not additional editor type-checking markers.

Match checker versions and settings when comparing behavior: Pylance versions and
user settings can differ from the pinned browser Pyright. Browser UI chrome is not
expected to duplicate VS Code, but language intelligence must not promise a better
experience than the public types provide there.

Build the generated assets from the repository root:

```console
npm ci --ignore-scripts --prefix playground
npm run build --prefix playground
uv build --wheel --out-dir docs/wheels
uv run --no-sync zensical build --clean
python scripts/fingerprint_docs_assets.py
```

`scripts/build-assets.mjs` packages the pinned Pyright typeshed's `stdlib`
stubs only and the real `src/pysely` Python sources. The third-party `stubs/`
tree is deliberately left out: the playground can never import those packages,
and inside the worker's in-memory filesystem they cost Pyright about 1.2 GB
(the tab measured ~1.6 GB with them and ~0.4 GB without). The generated manifest records the checker version,
source revision, Python targets, schema hash, and typeshed size/hash.
`scripts/fingerprint_docs_assets.py` gives browser assets content-hashed names in
the generated site so each deployment invalidates changed files automatically.
The install skips the pinned Pyright repository's monorepo bootstrap; all packages
used by the browser worker are declared directly in `package.json`.

To upgrade Pyright, update the version and source revision in `package.json` and
`scripts/build-assets.mjs`, rebuild, then run the stock language-server typing
tests and the playground browser checks. Review `src/worker.ts`, browser
polyfills, bundle size, cold startup, diagnostics, completion, hover, signatures,
navigation, retry, and teardown before committing the generated assets.

The analysis target is Python 3.11. Pyodide currently runs Python 3.14; both are
within Pysely's supported range, and the difference is recorded in the manifest.

The first production measurement on a local Chromium run reached ready Pyright
and compiled SQL in 12.6 seconds with a cold page load. The worker is 4.38 MB
uncompressed and 1.10 MB gzip-compressed. The matching typeshed archive is 4.03
MB. Browser tests cover visible table and join-scoped column suggestions plus
real Pyodide compilation in Chromium, Firefox, and WebKit in documentation CI.
