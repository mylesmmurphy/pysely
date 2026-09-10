# Playground intelligence

The documentation playground runs Pyright 1.1.413 in a browser worker. Monaco
sends normal LSP requests to that worker; a separate Pyodide worker executes the
same example against the real Pysely package.

Build the generated assets from the repository root:

```console
npm ci --prefix playground
npm run build --prefix playground
uv build --wheel --out-dir docs/wheels
uv run --no-sync zensical build --clean
```

`scripts/build-assets.mjs` packages the pinned Pyright typeshed and the real
`src/pysely` Python sources. The generated manifest records the checker version,
source revision, Python targets, schema hash, and typeshed size/hash.

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
