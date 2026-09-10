---
hide:
  - navigation
  - toc
---

# Playground

Define your database, write a query, and inspect the SQL. Table and column
suggestions update from your schema. Press **Ctrl+Space** inside a string to explore.

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
    <span id="playground-status" role="status">Loading editors…</span>
  </div>
  <div class="pysely-playground__panes">
    <section><h2>Database <small>schema.py</small></h2><div id="playground-schema" class="pysely-editor"><span class="pysely-editor__loading">Loading schema editor…</span></div></section>
    <section><h2>Query <small>query.py</small></h2><div id="playground-query" class="pysely-editor"><span class="pysely-editor__loading">Loading query editor…</span></div></section>
    <section><h2>SQL <small>compiled</small></h2><div id="playground-sql" class="pysely-editor"><span class="pysely-editor__loading">Loading SQL editor…</span></div></section>
  </div>
  <div class="pysely-playground__parameters"><span>Parameters</span><code id="playground-parameters">[]</code></div>
  <pre id="playground-error" role="alert" hidden></pre>
</div>

Queries compile in your browser; no database connection is required. The editors
provide Python/SQL highlighting and schema-aware query suggestions. For Python
project type checking and inferred result fields, enable [the mypy plugin](typing.md).
