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
    <section><h2>Database <small>schema.py</small></h2><div id="playground-schema" class="pysely-editor"><span class="pysely-editor__loading">Loading schema editor</span></div></section>
    <section><h2>Query <small>query.py</small></h2><div id="playground-query" class="pysely-editor"><span class="pysely-editor__loading">Loading query editor</span></div></section>
    <section>
      <h2 class="pysely-playground__tabs" role="tablist" aria-label="output">
        <button type="button" role="tab" id="playground-tab-sql" class="pysely-tab" aria-selected="true" aria-controls="playground-sql">SQL <small>compiled</small></button>
        <button type="button" role="tab" id="playground-tab-generated" class="pysely-tab" aria-selected="false" aria-controls="playground-generated">database.py <small>generated</small></button>
      </h2>
      <div id="playground-sql" class="pysely-editor pysely-editor--view" role="tabpanel" aria-labelledby="playground-tab-sql"><span class="pysely-editor__loading">Loading SQL view</span></div>
      <div id="playground-generated" class="pysely-editor pysely-editor--view" role="tabpanel" aria-labelledby="playground-tab-generated" hidden><pre id="playground-generated-code" class="monaco-editor pysely-code" aria-label="generated database.py"></pre></div>
    </section>
  </div>
  <div class="pysely-playground__parameters">
    <span>Parameters</span><code id="playground-parameters">[]</code>
    <span class="pysely-playground__divider" aria-hidden="true"></span>
    <span class="pysely-playground__pipeline"><code>schema.py</code> → <code>pysely codegen</code> → <code>database.py</code> → <code>query.py</code></span>
  </div>
  <pre id="playground-error" role="alert" hidden></pre>
</div>

- Run compiles a query in your browser with the selected dialect. No database
  connection is required.
- Every schema edit reruns `pysely codegen` in the browser. The generated
  `database.py` is what Pyright checks `query.py` against; the **database.py**
  tab shows it.
- Suggestions and diagnostics come from stock Pyright (`standard` mode) in a
  browser worker.
- `run_query` shows the typed result; the playground does not execute it.
- See [Code generation](codegen.md) for the same flow outside the browser.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Roadmap](ROADMAP.md){ .md-button }

</nav>
