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

Queries compile in your browser; no database connection is required. Editor
suggestions, type information, and diagnostics come from upstream Pyright running
locally in a browser worker. The [typing guide](typing.md) explains the generated
types shared with standard Python editors.
