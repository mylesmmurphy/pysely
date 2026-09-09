# Playground

Build a Pysely query and inspect its SQL without connecting to a database. The
code runs locally in your browser.

<div class="pysely-playground">
  <div class="pysely-playground__toolbar">
    <label for="playground-dialect">Dialect</label>
    <select id="playground-dialect">
      <option value="postgres">PostgreSQL</option>
      <option value="mysql">MySQL</option>
      <option value="sqlite">SQLite</option>
    </select>
    <button id="playground-run" type="button">Run</button>
    <span id="playground-status">Ready</span>
  </div>
  <textarea id="playground-code" spellcheck="false" aria-label="Python code">from pysely import Column, PostgresDialect, MysqlDialect, Pysely, SqliteDialect, Table


class UsersColumns:
    def __init__(self, source: str) -> None:
        self.id = Column("id", source, writable=False)
        self.email = Column("email", source)


users = Table(
    name="users",
    columns=UsersColumns("users"),
    columns_factory=UsersColumns,
)

dialects = {
    "postgres": PostgresDialect(),
    "mysql": MysqlDialect(),
    "sqlite": SqliteDialect(),
}
db = Pysely[object](dialect=dialects[playground_dialect])

compiled = (
    db.select_from(users)
    .select(users.c.id, users.c.email)
    .where(users.c.email.eq("ada@example.com"))
    .compile()
)

{"sql": compiled.sql, "parameters": list(compiled.parameters)}</textarea>
  <pre class="pysely-playground__output"><code id="playground-output">Click Run to compile the query.</code></pre>
</div>

The playground is compile-only. It does not send code or database credentials
to a server and does not execute SQL against a database.
