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
    <section><h2>SQL <small>compiled</small></h2><div id="playground-sql" class="pysely-editor"><span class="pysely-editor__loading">Loading SQL editor</span></div></section>
  </div>
  <div class="pysely-playground__parameters"><span>Parameters</span><code id="playground-parameters">[]</code></div>
  <pre id="playground-error" role="alert" hidden></pre>
</div>

- Run compiles a query in your browser with the selected dialect. No database
  connection is required.
- `run_query` demonstrates the typed execution result. The playground does not
  invoke it.
- Suggestions, type information, and diagnostics come from Pyright in a browser
  worker.
- The [typing guide](typing.md) covers the generated types used by standard Python
  editors.

<nav class="pysely-page-nav" aria-label="Page navigation" markdown="1">

[← Roadmap](ROADMAP.md){ .md-button }

</nav>
