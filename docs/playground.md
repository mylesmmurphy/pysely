---
hide:
  - navigation
  - toc
---

<div id="playground-workbench" class="pysely-playground">
  <div class="pysely-playground__toolbar">
    <label for="playground-dialect">Dialect</label>
    <select id="playground-dialect">
      <option value="postgres">PostgreSQL</option>
      <option value="mysql">MySQL</option>
      <option value="sqlite">SQLite</option>
    </select>
    <button id="playground-run" type="button" disabled>Run</button>
    <button id="playground-stop" type="button" disabled>Stop</button>
    <button id="playground-reset" type="button">Reset example</button>
    <span id="playground-intelligence-status" role="status" aria-busy="true">Loading Python suggestions</span>
    <button id="playground-intelligence-retry" type="button" hidden>Retry suggestions</button>
    <span id="playground-status" role="status" aria-busy="true">Loading editors</span>
  </div>
  <div class="pysely-playground__panes">
    <section><h2>Tables <small>schema.py</small></h2><div id="playground-schema" class="pysely-editor"><span class="pysely-editor__loading">Loading tables editor</span></div></section>
    <section><h2>Query <small>query.py</small></h2><div id="playground-query" class="pysely-editor"><span class="pysely-editor__loading">Loading query editor</span></div></section>
    <section>
      <h2 class="pysely-playground__tabs" role="tablist" aria-label="output">
        <button type="button" role="tab" id="playground-tab-sql" class="pysely-tab" aria-selected="true" aria-controls="playground-sql">SQL <small>compiled</small></button>
        <button type="button" role="tab" id="playground-tab-generated" class="pysely-tab" aria-selected="false" aria-controls="playground-generated">schema.pyi <small>types only</small></button>
      </h2>
      <div id="playground-sql" class="pysely-editor pysely-editor--view" role="tabpanel" aria-labelledby="playground-tab-sql"><span class="pysely-editor__loading">Loading SQL view</span></div>
      <div id="playground-generated" class="pysely-editor pysely-editor--view" role="tabpanel" aria-labelledby="playground-tab-generated" hidden><pre id="playground-generated-code" class="monaco-editor pysely-code" aria-label="generated schema.pyi"></pre></div>
    </section>
  </div>
  <div class="pysely-playground__parameters">
    <span>Parameters</span><code id="playground-parameters">[]</code>
    <span class="pysely-playground__divider" aria-hidden="true"></span>
    <span class="pysely-playground__pipeline"><code>schema.py</code> → <code>pysely typgen</code> → <code>schema.pyi</code> → <code>query.py</code></span>
  </div>
  <pre id="playground-error" role="alert" hidden></pre>
</div>

## Try it

1. Edit a table or column in **Tables**.
2. Write a query in **Query** and use the editor's suggestions.
3. Choose a dialect and press **Run** to inspect SQL and bound parameters.
4. Open **schema.pyi** to see the generated types.

Run compiles SQL; it does not send queries to a database.
The example's `run_query` function demonstrates result typing but is not executed.

## What happens when you edit?

- Schema edits regenerate the adjacent `.pyi` stub with `pysely typgen`.
- Pyright reads the stub for completion and type errors.
- Python executes handwritten `schema.py`, never the stub.

There is no generated runtime module. Diagnostics come from stock Pyright in
`standard` mode; Pysely does not hide or rewrite them.

[Set up the same workflow locally →](typgen.md)

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Roadmap](ROADMAP.md){ .md-button }

</nav>
