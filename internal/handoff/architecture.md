# Pysely: Production Architecture and Codex Agent Handoff

**Audience:** a new Codex 5.6 Sol agent implementing the project.  
**Owner:** Pysely contributors.
**Prepared:** September 9, 2026.  
**Deliverable status:** architecture and implementation instructions, not an implemented library.  
**Product:** Pysely, a Python SQL query builder inspired by Kysely, with generated schemas and precise static typing.

## 1. Mission and standing instructions

Build the production project now. The goal is broad Kysely feature and behavioral parity adapted to Python, not a demonstration, prototype product, or permanently reduced MVP. Implement in dependency order, but retain the complete target and release gates throughout. Early vertical slices are construction milestones, not the deliverable.

Use Kysely's module boundaries, API concepts, documentation organization, and behavioral test cases wherever they make sense in Python. Prefer snake_case names, context managers, Python exceptions, uv packaging, and Python-native database drivers over literal TypeScript syntax translation.

The owner has selected **Pysely**. Package-name availability has not been established; keep the local project name and check availability before any release. Do not change branding without discussing a concrete conflict.

Proceed with repository setup, implementation, tests, and documentation. Make routine engineering choices autonomously and record material decisions in ADRs. Do not stop after writing another plan. Do not claim production readiness from passing SQLite tests or from a large test count. If an environment cannot run a required database or checker, report the missing verification and keep its gate open.

Public publication, deployment, and sending messages are separate actions from building the repository. This handoff does not instruct the agent to publish a package or contact maintainers.

## 2. Reference baseline and evidence

The preparation agent cloned and inspected the upstream repository. Use this reproducible baseline:

| Item | Value |
| --- | --- |
| Repository | https://github.com/kysely-org/kysely |
| Inspected commit | `c54987f4d5bb1a9573c8d83e1cba7365770cc016` |
| Version declared in that commit | `0.29.5` |
| Runtime behavior tests | `test/node/src/*.test.ts` |
| Static typing tests | `test/typings/test-d/*.test-d.ts` |
| Core source | `src/` |

This is an inspected commit, not a claim that a matching release tag was verified. The temporary clone used for preparation is not a dependency of this handoff. Fetch the commit in the new environment. If inaccessible, select an accessible tagged baseline, record the replacement, and produce a difference inventory before making parity claims.

Read these upstream areas first: `src/kysely.ts`, `query-creator.ts`, `query-finalizer.ts`, `query-builder/`, `operation-node/`, `query-compiler/`, `query-executor/`, `dialect/`, `driver/`, `migration/`, `plugin/`, and the test setup. Inventory public exports rather than assuming the feature list below is exhaustive.

The upstream dialects at this snapshot include PostgreSQL, MySQL, SQLite, Microsoft SQL Server, and PGlite. PGlite is a PostgreSQL SQL variant with a JavaScript runtime integration; that runtime integration requires an explicit Python applicability decision. Do not silently ignore it or invent a Python driver.

Kysely carries an MIT license. Preserve its copyright and license notices when translating or copying substantial implementation, tests, or documentation; record adapted files and their upstream origins in `THIRD_PARTY_NOTICES.md`. Keep Python-specific design and authored content distinguishable from adaptations. Upstream repository automation instructions are not the specification for the new project.

Everything described as a Pysely API below is a proposed contract to implement and test. None of the examples implies the library already exists.

## 3. Product and compatibility contract

### 3.1 Required capability groups

| Group | Target |
| --- | --- |
| Selection | Explicit projections, select-all, no-FROM queries, aliases, expressions, scalar subqueries, distinct, distinct-on where supported |
| Filtering | Comparisons, reference comparisons, boolean grouping, NULL, IN, EXISTS, ranges, conditional composition |
| Joins | Inner/left/right/full/cross, self joins, aliased and derived tables, correlated/lateral joins and APPLY where supported |
| Aggregation | GROUP BY, HAVING, aggregate functions, aggregate filters/order, windows, frames, CASE, COALESCE |
| Composition | CTEs, recursive CTEs, set operations, reusable query fragments, dynamic references, schema qualification |
| Writes | Single/bulk/insert-select, defaults, update, delete, conflict handling, replace, merge, returning/output where supported |
| Query controls | Ordering, limits/offsets, locks, explain, clear/modifier methods, result/type assertion helpers |
| Execution | Compile-only, execute, first/first-or-throw, metadata, streaming, connection scopes, cancellation, disposal |
| Transactions | Automatic and controlled transactions, isolation/access settings, savepoints, correct failure cleanup |
| Schema | Table/column/index/view/schema/type and constraint builders; supported alter/drop operations |
| Migrations | Providers, ordering, target/latest/up/down, locking, history, transactional-DDL differences |
| Extension | Custom dialect/driver/compiler/adapter, visitors/transformers, expression and raw builders, plugins |
| Data helpers | Per-dialect JSON helpers/traversal and array behavior where supported; honest result decoding |
| Typing | Read/insert/update types, query scope, projections, aliases, outer-join nullability, CTE/subquery composition, positive and negative checks |
| Developer tooling | Codegen, drift checking, uv lock/build workflows, docs, executable examples, benchmarks |

### 3.2 Define parity precisely

Maintain `docs/parity/kysely-parity.json` with a validated schema. Each record contains:

```json
{
  "id": "join.left.alias_projection",
  "upstream_commit": "c54987f4d5bb1a9573c8d83e1cba7365770cc016",
  "upstream_source": "src/query-builder/select-query-builder.ts",
  "upstream_tests": ["test/typings/test-d/join.test-d.ts"],
  "pysely_api": "SelectQueryBuilder.left_join",
  "dialect_support": {},
  "runtime_status": "planned",
  "mypy_status": "planned",
  "portable_typing_status": "planned",
  "tests": [],
  "difference": null
}
```

Use `planned`, `implemented_unverified`, `verified`, `blocked`, `not_applicable`, and `intentional_difference`. Populate dialect support per engine/version. A placeholder empty mapping is not a completed record. Every non-parity classification needs a reason and a test or applicability explanation. Track case-level mappings, not only one row per upstream file. Keep a separate public-export inventory so untested upstream APIs are still accounted for.

Parity means matching behavior on applicable engines, with documented Python naming/result/driver adaptations. It does not mean byte-identical placeholders across JavaScript and Python drivers. It also does not mean that every SQL engine supports every SQL feature. No silent emulation that changes transaction or query semantics.

JavaScript platform harnesses for Node/Bun/Deno/browser/Workers become Python packaging, platform, import, event-loop, and driver tests. Community adapters are not implicitly first-party targets. PGlite's SQL semantics should map to PostgreSQL coverage; record its runtime adapter as a separately assessed applicability item.

## 4. Repository structure and packaging

Use one distributable `pysely` package initially, matching Kysely's cohesive core. Codegen and the mypy integration live in the same repository under isolated modules and optional extras. A uv workspace is useful only if separately versioned distributions become necessary; do not split packages merely to create a monorepo.

Use Python **3.11+** as the initial compatibility floor, conventional `TypeVar`/`Generic` syntax when needed, and `typing_extensions` for required backports. Test supported stable Python versions at implementation time; do not promise support for unreleased interpreters. Pin development Python and uv versions for reproducibility.

| Path | Responsibility / upstream counterpart |
| --- | --- |
| `src/pysely/__init__.py` | Curated public exports; `src/index.ts` |
| `src/pysely/pysely.py` | Root client, connection/transaction contexts; `kysely.ts` |
| `src/pysely/query_creator.py` | Entry points for query construction |
| `src/pysely/query_finalizer.py` | Finalization of schema and other root operations |
| `src/pysely/operation_node/` | Immutable AST nodes, visitor, transformer |
| `src/pysely/parser/` | Normalize Python arguments into nodes |
| `src/pysely/expression/` | Typed expressions, expression/function builders |
| `src/pysely/query_builder/` | Select/insert/update/delete/merge/join/CTE builders |
| `src/pysely/raw_builder/` | Explicit SQL fragments and bound values |
| `src/pysely/query_compiler/` | Compiled query and default SQL visitor |
| `src/pysely/query_executor/` | Plugins, compilation, connection provision, execution |
| `src/pysely/driver/` | Driver/connection protocols, lifecycle and providers |
| `src/pysely/dialect/{postgres,mysql,sqlite,mssql}/` | Compiler, adapter, introspector, driver per engine |
| `src/pysely/schema/` | DDL builders, matching Kysely's meaning of schema |
| `src/pysely/migration/` | Migrator, providers, migration records and locks |
| `src/pysely/plugin/` | Built-in plugins and public plugin protocols |
| `src/pysely/helpers/` | Dialect-specific JSON and related helpers |
| `src/pysely/dynamic/`, `readonly/`, `util/` | Relevant upstream counterparts |
| `src/pysely/catalog/` | Python addition: schema metadata, typed tables, codecs |
| `src/pysely/codegen/` | Python addition: introspection normalization and rendering |
| `src/pysely/typing_plugin/` | Optional mypy integration; no runtime import of mypy |
| `src/pysely/py.typed` | Packaged typing marker |
| `test/runtime/`, `test/typings/` | Python counterparts of runtime/typing suites |
| `test/compiler/`, `test/codegen/`, `test/packaging/` | Focused additional suites |
| `test/property/`, `test/benchmarks/` | Generated invariants and performance |
| `test/fixtures/`, `test/conftest.py` | Schemas, shared records, dialect parametrization |
| `docs/`, `example/`, `scripts/`, `.github/workflows/` | Documentation, runnable examples, tooling, CI |
| `docs/adr/`, `docs/parity/`, `internal/handoff/` | Decisions, parity evidence, continuation state |

Retain Kysely's singular `test/` and `example/` where convenient. Replace hyphenated TypeScript filenames with snake_case. Group tiny related AST definitions if Python import costs justify it; preserve recognizable concepts and source mappings.

### 4.1 uv and dependencies

Use `pyproject.toml`, commit `uv.lock`, and use `uv sync --locked` in CI. Use a conventional build backend such as Hatchling, with a verified bounded build requirement. Let uv resolve actual current package versions, commit the lock, and avoid fabricated version numbers in setup instructions.

Core should stay small: stdlib plus `typing_extensions` only when needed. No dependency on SQLAlchemy or a TypeScript runtime for execution. Driver packages are optional extras, with lazy imports and useful missing-extra errors. Codegen uses stdlib `ast`, `argparse`, and Python source rendering, so it needs no extra. JSON/runtime validation helpers remain optional.

Proposed extras: `postgres`, `mysql`, `sqlite`, `mssql`. Proposed development groups: `dev`, `docs`, `bench`. Development includes pytest, pytest-asyncio, pytest-cov, Hypothesis, Ruff, mypy, Pyright, and packaging validation tools. Codegen ships in the core package and has no runtime dependency.

Bootstrap with `uv init --lib --build-backend hatchling pysely` only if there is no existing project. Configure the package and groups before using the following intended repository commands:

```bash
uv sync --locked --all-extras --group dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src/pysely
uv run pyright src/pysely
uv run python scripts/check_typing.py --engine all
uv run pytest test/compiler test/codegen test/property test/packaging
uv run pytest test/runtime --dialect postgres
uv run python scripts/check_parity.py --release
uv build --no-sources
```

Implement `check_typing.py`, `check_parity.py`, and pytest's `--dialect` option; they are proposed project tools, not built-in commands. Give each CI job only its required extras. Native SQL Server requirements may prevent installing every extra on every platform; the all-extras command is for a provisioned development environment.

## 5. Runtime architecture and invariants

### 5.1 Query construction and compilation

A builder stores an immutable root operation node, executor reference, and query identity. Method calls create new builders with structurally shared nodes. Compilation transforms the root through query plugins, validates supported operations, and visits the tree to produce SQL and parameters. Execution uses the compiled result and a connection provider, then applies result plugins.

Use frozen dataclasses with slots and tuples for structural AST fields. Do not store mutable builder-owned lists or dictionaries inside otherwise frozen nodes. Define whether caller-provided mutable parameter payloads are copied; default to retaining opaque values with documented no-mutation-during-execution semantics rather than deep-copying arbitrary user objects.

Separate nodes for identifiers, references, values, operators, aliases, and raw fragments. Every node must be traversable by the base visitor and transformer. Nodes must not acquire connections, contain checker objects, or depend on a driver.

Require `Expression.__bool__` to raise an actionable error so Python `and`, `or`, and accidental truth tests cannot silently produce wrong SQL. Prefer `.eq()`, `.and_()`, `.or_()`, `.is_null()`, etc.; optionally add operator overloads only with precedence tests and clear documentation. Normalize `None` comparisons explicitly and preserve SQL three-valued logic.

Empty IN lists need an explicit policy, including upstream plugin behavior. Do not casually translate NULL-sensitive operations or empty lists into semantically different expressions.

### 5.2 CompiledQuery and binding

`CompiledQuery[Row]` contains SQL, ordered bind values, root node or relevant metadata, query identity, and binding-profile information. Keep query identity independent of SQL text and parameter content; follow pinned upstream identity semantics or record a Python deviation.

The same SQL dialect can have multiple driver placeholder conventions. Choose a compiler binding strategy from the configured driver profile. PostgreSQL with asyncpg can use `$1`; a psycopg profile would require its supported binding convention. MySQL Python drivers may need `%s` rather than the JavaScript driver's `?`. Never convert placeholders by string replacement: literals, quoted identifiers, comments, JSON operators, and raw fragments make that unsafe.

`compile()` works offline when supplied an explicit dialect/capability profile. Executing a compiled query under an incompatible profile must fail. Support compile-only/dummy drivers. Avoid global compilation caches initially; any later cache must include dialect, capabilities, plugins, and bind layout, and must not retain sensitive parameter values.

### 5.3 Dialect boundaries

Follow the four factories in Kysely's dialect contract: `create_driver`, `create_query_compiler`, `create_adapter`, `create_introspector`. The adapter owns capabilities and migration locking outside the driver/compiler. The introspector uses a client with user query/result plugins disabled.

| Target | Initial driver candidate to verify | Required work |
| --- | --- | --- |
| PostgreSQL | asyncpg | Pool integration, codecs, cursors, cancellation, schema metadata |
| MySQL | asyncmy | Binding, pool reset, affected/changed rows, implicit DDL commits |
| SQLite | aiosqlite | Connection-scoped in-memory databases, transactions, version capabilities |
| SQL Server | aioodbc over pyodbc | ODBC installation, output, types, thread-backed I/O and cancellation behavior |

These are architecture defaults, not claims that every required capability is already verified. Validate driver maintenance, licensing, supported Python versions, OS requirements, streaming, and cancellation APIs before finalizing pins. Substitute a driver through the same protocol and an ADR if necessary; do not remove the dialect target.

Capabilities must distinguish engine version and driver behavior: returning/output, merge, lateral/APPLY, transactional DDL, savepoint operations, JSON features, conflict syntax, server-side cancellation, and streaming. Unsupported features raise `UnsupportedFeatureError` naming the dialect and capability before side effects when determinable. Do not catch a database error and retry with different SQL automatically.

### 5.4 Execution, results, and lifecycle

Use an async-first execution API, matching Kysely's asynchronous contract. Building and compiling are synchronous. A synchronous public facade is a separately documented future Python enhancement, not a hidden `asyncio.run()` wrapper. Never block the event loop with an unadapted driver.

Driver/connection protocols cover init, acquisition, release/discard, execute, stream, begin/commit/rollback, savepoints, and shutdown. Dialects receive database resources or lazy resource factories instead of connection settings, and client destruction closes initialized resources. Concurrent initialization and repeated shutdown need deterministic behavior.

Use dictionary rows by default. Low-level `QueryResult[Row]` holds rows plus optional affected rows, changed rows, and insert ID. Missing metadata is `None`, not invented zero. High-level read and returning builders produce `list[Row]`; non-returning writes mirror Kysely's operation-result semantics with Python result dataclasses. Verify first/first-or-throw and row-count semantics against the baseline.

Duplicate projection names require a deliberate mapping policy. Default to rejecting known collisions and runtime duplicate column labels with an actionable alias error; if implementing a compatibility overwrite mode, document its ordering and return a sound type. Never silently claim two same-named selected values are both present in a dictionary. Record this as a deliberate upstream behavior difference where applicable.

Streaming must hold its connection until completion or explicit closure, propagate backpressure, and avoid buffering the entire result. Provide an async context-managed stream so breaking iteration closes deterministically; do not rely on async-generator garbage collection. Test server-side versus driver-buffered behavior and describe limitations per driver.

### 5.5 Transactions, cancellation, and errors

Automatic transaction contexts pin one connection, commit on successful exit, and roll back on errors including cancellation. Controlled transactions expose a guarded state machine: active, committed, rolled_back, failed/closed. Reject operations after termination. Savepoints are explicit and capability-aware; release is not universally supported.

Do not let queries launched through the root client inside a transaction pretend to share its connection. Require the transaction client. Enforce or document transaction concurrency restrictions rather than allowing concurrent cursor use on one connection.

Cancellation must cover acquisition, begin, execution, streaming, plugin processing, and cleanup. An interrupted coroutine does not prove the database stopped the query. A connection with in-flight work must be awaited to a safe state or discarded before reuse. Preserve cancellation propagation, bound cleanup, and use driver-specific cancellation only where verified. Commit transport failure may have an unknown outcome; never report a guaranteed rollback or retry a write automatically.

Provide typed library exceptions for invalid query, unsupported feature, no result, closed transaction/client, codegen failure, and migration failure. Preserve driver exceptions as causes and make structured driver metadata accessible without fragile message parsing. Logs include operation/duration/dialect/query ID; parameter logging is opt-in and redacted. No connection secrets in generated files or errors.

## 6. Type architecture: two explicitly tested contracts

Direction update: generated schema-specific interfaces and ordinary Python typing
are the developer experience. `pysely codegen` writes them from the annotated
schema classes, and the mypy plugin has been removed (ADR 0006). Custom editor
services remain paused.

### 6.1 Portable typing

Ordinary Python types provide generated table/column attributes, expression value types, explicit row/write TypedDicts, generics, overloads, and known full-row results. These must work with both mypy without the plugin and Pyright. Package `py.typed` and test installed-wheel behavior.

Exact arbitrary named projections, scope-sensitive aliases, and outer-join shape transformations are not promised from ordinary annotations alone. Portable fallback results must be conservative, such as `dict[str, object]`, rather than an incorrectly precise `UserRow`. Tuple APIs may use overloads where sound, but must not ignore join-induced nullability. Typed values alone do not prove a column belongs to the current query scope.

### 6.2 Generated interfaces instead of a checker plugin

`pysely codegen` parses the schema module with `ast` and writes the literal column types, per-column overloads, and selected-row shapes that both checkers read as ordinary source. It never imports the schema, executes application code, or connects to a database. Because Pyright has no plugin interface and Pylance is the primary editor target, generation is the only mechanism that serves both checkers from one implementation; the previous `pysely.mypy` plugin duplicated these rules for mypy alone and was removed.

Generated output is committed so editors need no build step. `pysely codegen --check` gates drift in CI and in the published pre-commit hook.

Model internal query type state as conceptually `Query[Database, Scope, Projection, Mode]`. Scope records source identity, alias, accessible columns, correlation rules, and null extension. Projection records output name, value type, source provenance, and conditional presence. These states must survive helper functions, module imports, builder reassignment, and mypy incremental caches. The precise serializable representation is an initial implementation decision to prove with tests.

Use supported method/signature/attribute hooks and metadata mechanisms. Keep mypy-specific type construction behind an adapter. Share declarative operation semantics and schema identities with runtime code where useful, but never couple runtime execution to mypy internals.

Core inference rules:

1. `select_from` establishes scope; aliases hide or replace the original binding as SQL requires.
2. `select` extends projection; `clear_select` removes it; aliasing changes output keys without losing provenance.
3. Left joins null-extend the joined source; right joins null-extend prior scope; full joins extend both. Recompute projections when a later join changes the nullability of an already-selected source.
4. Arbitrary WHERE predicates do not automatically narrow NULL away. Explicit, verified narrowing helpers have their own rules.
5. Scalar subqueries consider zero-row nullability and cardinality; CTE/derived-table columns come from their projection, not base tables.
6. CASE and COALESCE combine types and nullability according to expression semantics. Aggregate empty-set behavior and window context require distinct tests.
7. Union/set operations check compatible projections and compute conservative output types; SQL output-name rules matter.
8. Conditional selection distinguishes an absent key from a present nullable value. Dynamic strings lose guarantees unless statically resolvable.
9. Insert/update checking respects omission/defaultability separately from NULL acceptance and supports typed SQL expressions as values.
10. Returning/output results use projection rules and dialect semantics. Read-only clients restrict writes at the appropriate API boundary.

Generated source serves mypy and Pyright alike; a checker plugin would have served only mypy. Publish a checker capability table. Do not market exact named result inference in all editors until executable editor/checker tests establish it. If broader editor inference becomes mandatory, specify a separate language-server or generated-query-artifact project; do not disguise it as a routine schema-codegen feature.

Keep a documented explicit `assert_type`/cast escape hatch, matching the purpose of Kysely's helpers, and distinguish static assertions from runtime validation. Never use casts or `Any` internally just to make expected-error fixtures pass. Unknown database types default to `object` with diagnostics or a required override.

### 6.3 Earliest typing proof, without reducing the project

Before freezing public generics, implement permanent fixtures for generated schema imports, two-column projection, aliased self join, selection before a right join, nullable joined expression, CTE, scalar subquery, helper-returned builder, conditional projection, and invalid writes. Run cold and incremental mypy, plus portable Pyright tests. If the proposed representation fails, fix the type architecture and update the ADR; continue building the full project.

## 7. Schema introspection and generated artifacts

### 7.1 Separate three representations

1. **Database metadata:** normalized catalog information including exact SQL names, type identifiers, schemas, defaults, identity/generated modes, nullability, constraints, and view status.
2. **Python schema source:** importable typed table references and read/insert/update shapes, usable without a database connection.
3. **Query inference state:** transient static information derived from query calls. Codegen does not enumerate all possible projections.

Support handwritten schema declarations through the same public contracts. Codegen is recommended convenience, not a runtime requirement. Keep DDL builders under `schema/`; put data-model metadata under `catalog/` to avoid conflating the two.

### 7.2 Proposed workflow

```bash
uv run pysely codegen --dialect postgres --url-env DATABASE_URL --out app/db/generated
uv run pysely codegen --dialect postgres --url-env DATABASE_URL --out app/db/generated --check
```

The first command writes deterministic generated modules and a versioned metadata manifest. The second reads metadata and reports drift with a nonzero exit code, without rewriting files. Regenerate after migrations against a representative development or CI database. Check generated source into the application repository.

Introspection is read-only. Obtain the most consistent snapshot available for the dialect, detect obvious concurrent DDL changes, and explain consistency limitations. Exclude internal migration tables by default with an override. Support schema/table include/exclude filters, deterministic name normalization, and custom type/codec mappings.

Render to temporary paths, format and syntax-check all output, validate the manifest, then replace generated files atomically. Delete obsolete files only if recorded as generator-owned in the prior manifest. Never overwrite hand-written sibling modules. Output includes generator version, schema format version, and a canonical fingerprint, but no URL, credentials, or changing timestamps that create meaningless diffs.

### 7.3 Concrete generated shape

Example input semantics: `users.id` is an always-generated identity, `email` is required text, `nickname` is nullable text, and `created_at` is a non-null timestamp with a server default. A default allows omission on insert but does not necessarily forbid later updates.

Illustrative generated source, using the proposed core contracts:

```python
from datetime import datetime
from typing import Literal, Never, NotRequired, TypedDict
from pysely.catalog import Column, Table

class UserRow(TypedDict):
    id: int
    email: str
    nickname: str | None
    created_at: datetime

class UserInsert(TypedDict):
    email: str
    nickname: NotRequired[str | None]
    created_at: NotRequired[datetime]

class UserUpdate(TypedDict, total=False):
    email: str
    nickname: str | None
    created_at: datetime

class UsersColumns:
    # Column[Read, Insert, Update, SQLName, SourceIdentity]
    id: Column[int, Never, Never, Literal["id"], Literal["public.users"]]
    email: Column[str, str, str, Literal["email"], Literal["public.users"]]
    nickname: Column[
        str | None, str | None, str | None,
        Literal["nickname"], Literal["public.users"]
    ]
    created_at: Column[
        datetime, datetime, datetime,
        Literal["created_at"], Literal["public.users"]
    ]

    def __init__(self) -> None:
        self.id = Column("id", source="public.users", writable=False)
        self.email = Column("email", source="public.users")
        self.nickname = Column("nickname", source="public.users", nullable=True)
        self.created_at = Column("created_at", source="public.users", has_default=True)

class Users(Table[UserRow, UserInsert, UserUpdate, UsersColumns]):
    def __init__(self) -> None:
        super().__init__(name="users", schema="public", columns=UsersColumns())

users = Users()

class Database(TypedDict):
    users: Users
```

The metadata manifest supplies complete SQL/default/identity/type information; the snippet abbreviates constructor metadata. Implement typed constructors so generated assignments check without unchecked casts. `Table` exposes `c: Columns` and immutable metadata. The generator may produce frozen columns containers instead of the illustrative initializer, while retaining explicit static declarations and runtime bindings.

Using `.c` avoids collisions between database column names such as `name`, `schema`, or `alias` and table methods. Sanitize Python keywords and invalid identifiers deterministically while retaining original SQL names; provide explicit-name access for pathological names.

Generated schema-specific clients expose literal table overloads and accumulate
available column-name literals through standard generic types. They wrap the shared
runtime builder rather than generating SQL behavior. The database registry remains
the runtime source for string validation.

### 7.4 Read/write rules and decoding

| Database condition | Read shape | Insert shape | Update shape |
| --- | --- | --- | --- |
| Required, no default | Non-null value | Required key | Optional key, non-null value |
| Nullable | Value or None | Omissible where SQL permits; explicit None allowed | Optional key, value or None |
| Server default | Declared value/nullability | Omissible; explicit values if permitted | Writable unless independently restricted |
| Identity BY DEFAULT | Generated value | Omissible, explicit value allowed | Per database rules |
| Identity ALWAYS/computed | Generated value | Omitted in normal API | Omitted where writes are forbidden |
| Read-only view | Declared read shape | No normal insert contract | No normal update contract |

Expose explicit dialect-specific override mechanisms for legal exceptional identity writes. `Never` means forbidden, while `NotRequired` means omission is legal; neither means nullable. Do not model every server-default column as unwritable.

Use Python `int` for database integers, `Decimal` for exact numeric values, appropriate datetime/date/time/UUID/bytes types, literal unions or enums for verified enums, and recursive JSON value types only when the driver/codec actually decodes JSON. SQLite's dynamic storage and declared affinities need conservative rules or explicit strict decoding. Arrays, domains, ranges, unsigned integers, custom types, and SQL Server-specific values require per-dialect mappings and tests.

Generated annotations must match actual driver output. Align codecs and schema generation through a declared type-mapping profile; custom overrides carry a decoder/encoder contract or an explicit user assertion. Do not claim timezone awareness from a bare `datetime` annotation. Introspection cannot infer a JSON business schema from a generic JSON column.

Generate literal-value write TypedDicts for application inputs; builder `.values()`/`.set()` additionally support expression-valued writes through defined typed contracts/plugin rules. Test both rather than forcing SQL expressions into the simple value TypedDict.

## 8. Proposed public API examples

The preferred API uses Kysely-style string references backed by a generated typed
client. The earlier `.c` object API remains a compatibility path, not the primary
developer experience.

```python
from app.db.generated import users
from pysely import Pysely, PostgresDialect

async with Pysely(dialect=PostgresDialect(pool=pool)) as db:
    rows = await (
        db.select_from(users)
        .select(users.c.id, users.c.email)
        .where(users.c.email.eq("myles@example.com"))
        .execute()
    )
    # Enhanced mypy target: list[TypedDict with id: int, email: str]
    # Portable target: conservative projection result unless explicitly typed.

    async with db.transaction() as tx:
        inserted = await (
            tx.insert_into(users)
            .values({"email": "another@example.com"})
            .returning(users.c.id)
            .execute_take_first_or_throw()
        )
```

Table `.as_("u")` returns an aliased reference with rebound source identity and typed columns. Aliasing an expression changes its result key. Alias objects must not mutate the original table; self joins must remain distinct even when types match.

Raw SQL must distinguish bound values from identifiers and trusted fragments. Proposed safe composition:

```python
fragment = sql.join([
    sql.raw("lower("),
    sql.ref(users.c.email),
    sql.raw(") = "),
    sql.val(email.lower()),
], separator="")
```

`sql.raw` is explicitly trusted SQL, `sql.val` always binds, and identifiers are escaped as identifiers. Python f-strings are not parameterization. Additional ergonomic formatting can be designed with parsing and adversarial tests; never infer safety from an already-interpolated string. Raw result typing is a user assertion unless a decoder validates it.

## 9. Plugins, DDL, migrations, and documentation

### 9.1 Plugins

Implement the pinned upstream plugin contract: query transforms retain the root node kind; result transforms operate after execution. At the inspected snapshot both loops apply plugins in registration order; preserve that and test composition rather than assuming reverse result order.

Cover with-schema, camel-case conversion, JSON result parsing, deduplicated joins, empty-IN handling, safe NULL comparison, immediate values, and no-op transformation where applicable. Immediate-value SQL is an explicit opt-in escape hatch with dialect-correct literals, not default binding behavior. Runtime name transformations must agree with generated output names and static result contracts.

Plugins must not leak per-query state when a query is only compiled, fails, is cancelled, or streams. Use bounded/scoped state or weak references and test cleanup. Plugins changing result shapes must declare how typing changes; arbitrary transformations cannot preserve false guarantees.

### 9.2 DDL and migration behavior

Mirror Kysely DDL builders and migrator semantics where applicable. Test identifier escaping, constraints, composite keys, foreign keys, indexes, schemas, views, supported types, alteration, and dialect-specific limits. DDL literals and identifiers need different handling from DML binds.

Migration providers load ordered Python migration modules with explicit `up` and optional `down` coroutines. File-provider paths and import errors are deterministic. Treat migrations as application code, not safe data. Provide latest/target/up/down execution and structured per-migration status.

Acquire migration locks with dialect-appropriate semantics on the correct session/transaction. Test two processes racing, first-run history-table creation, interrupted runs, missing files, altered ordering, failed up/down, and history consistency. Never promise all-or-nothing DDL rollback on engines that implicitly commit. Checksum tracking may be a documented Python extension, but must not silently redefine upstream ordering/history behavior.

### 9.3 Documentation structure

Create installation, getting-started, schema generation, query examples grouped by SQL operation, recipes, dialect/driver setup, typing/checker support, transactions/cancellation, migrations, plugins, API reference, and Kysely-to-Pysely migration pages. Use docstrings as API reference input, preserving Kysely's hover-documentation emphasis.

Keep examples executable and test them against an installed package. Include explicit mapping for camelCase to snake_case, `as` to `as_`, reserved-word methods, raw SQL syntax, result metadata, nullable values, and runtime platform differences. Document supported engine and driver versions with actual CI evidence.

## 10. Test strategy and upstream-suite adaptation

### 10.1 Port behavior, not just file names

Use the pinned Kysely tests as a behavioral checklist and source of cases. Inspect each test's setup, SQL expectations, result assertions, errors, and dialect exclusions. Translate TypeScript fixtures to Python and retain upstream file plus full test title in metadata. Do not copy JavaScript number/string driver artifacts when Python's declared decoder contract differs; record adaptations.

Recreate the shared `person`, `pet`, and `toy` fixtures and schema-qualified variants from upstream. Keep data deterministic and restore state between tests. Parameterize dialects with stable IDs; use separate schemas/databases per worker. Transaction rollback is not sufficient isolation for tests of DDL or commits.

Each relevant case should assert both compilation and live behavior. A query that produces plausible SQL but wrong rows is not verified. A query that runs but interpolates parameters incorrectly is also not verified.

### 10.2 Required suites

| Suite | Required evidence |
| --- | --- |
| AST/builders | Immutability, branch reuse, recursive visitor/transformer completeness, valid nesting |
| Compiler | Exact SQL/binds per engine and driver profile; precedence, identifiers, nesting, unsupported capability errors |
| Runtime | Live reads/writes/joins/CTEs/windows/DDL and result metadata on all supported engines |
| Transactions | Isolation/settings, commit/rollback, savepoints, invalid states, connection pinning and failure outcomes |
| Resource handling | Acquisition exhaustion, init/shutdown races, disconnects, ownership, cancellation, leak detection |
| Streaming | Bounded buffering, early exit, explicit close, cancellation, backpressure, plugin behavior |
| Typing positive | Exact types through projection, joins, aliases, writes, CTEs, helpers, generics |
| Typing negative | Unknown/out-of-scope columns, wrong value types, missing insert keys, forbidden writes, nullable misuse |
| Codegen | Golden output, real introspection, syntax/import/type checks, deterministic rerun, drift, custom types, pathological names |
| Plugins | Order, invariants, interactions, compile-only and cancellation cleanup, shape changes |
| Migrations | Live lock races, ordering, failure recovery, engine DDL behavior, providers |
| Security/correctness | Malicious bound strings and identifiers, raw fragment boundaries, secrets in logs, identifier edge cases |
| Packaging | Wheel/sdist, clean installs, public exports, optional dependencies absent, py.typed, generated imports |
| Property tests | Parameter ordering, quoting, AST branch independence, no-op transforms, generated schema invariants |
| Performance | Build/compile complexity, memory, driver overhead, stream memory, checker and codegen scaling |

Use pytest parametrization and Hypothesis. SQL snapshot tests must store expected parameters separately, and snapshots must be reviewed. Never normalize away parentheses, parameter order, or other meaningful SQL differences. No-op-transformer runs should cover every node family, as upstream's transformer test mode does.

### 10.3 Type-test harness details

Use isolated fixture projects and subprocess checker invocations. Positive cases use `assert_type` when a named expected type is expressible and normalized reveal diagnostics for anonymous results. Negative fixtures declare expected error locations and diagnostic categories. Verify an expected error is actually reported and that unrelated errors are absent; a global nonzero checker exit is insufficient.

Run mypy with and without the plugin, and Pyright against the portable contract. Pin checker versions and test the plugin's lowest/highest supported versions in CI. Include incremental/daemon runs, two modules with same table names, aliased imports, editable versus wheel installs, and cache invalidation after schema regeneration. Add large-schema and long-chain cases inspired by upstream `huge-db` and typing benchmarks.

Exercise deliberate `Any`, dynamic identifiers, and explicit casts as documented escape hatches, with tests showing precisely which checks are forfeited. Test that `.eq()` and related generics reject incompatible operands rather than inferring an overly broad union or `object` to accept everything.

### 10.4 Differential testing

Build a small development-only TypeScript harness against the pinned Kysely version for shared query specifications. Compare structural SQL and bind order using token-aware placeholder normalization, then compare normalized database results where practical. Node and pnpm are test-reference dependencies only; users installing Pysely must not need them.

Use driver-aware normalization for JSON, integer metadata, decimals, timestamps, and duplicate-name policy. Keep those differences explicit and minimal. Do not treat upstream behavior as infallible: a suspected upstream bug gets a regression test and recorded intentional difference, not blind reproduction.

### 10.5 Skips, xfails, and coverage

Local missing-service tests may skip with explicit reasons. Release CI jobs configured for a required dialect must fail when it is unavailable. Every skip/xfail belongs to a capability or tracked gap; a test that never ran is not verified. Use strict xfail and detect unexpected passes.

Target at least 90% branch coverage in the core package, with explicit exception/failure cases for transactions, binding, cancellation, and migration locks. This is a proposed engineering gate, not a guarantee of correctness. Require both parity-ledger completion and semantic coverage. Do not inflate coverage with implementation-mirroring tests or weaken assertions to clear a gate.

## 11. CI, release, and production acceptance

| Job | Gate |
| --- | --- |
| Formatting/static | Ruff, mypy, Pyright; no broad suppression regressions |
| Unit/compiler/property | Every supported Python version; deterministic core suites |
| Live engines | PostgreSQL/MySQL/SQLite/SQL Server at pinned supported versions |
| Checker compatibility | Portable and enhanced contracts, installed package, incremental cache |
| Packaging/platform | Wheel + sdist clean installs; Linux/macOS/Windows where drivers support them |
| Documentation/examples | Strict docs build and executable examples |
| Parity audit | All baseline exports/cases classified; no unexplained missing targets |
| Extended/nightly | Engine-version edges, disconnect/cancellation races, stress, differential, benchmarks |

Use service health checks rather than arbitrary startup sleeps. Pin container versions and then digests for repeatability. Declare SQL Server runner architecture and ODBC dependencies explicitly. Do not use one mutable `latest` image as the support policy.

Keep unit tests fast enough for each change and run all relevant dialect suites for compiler/driver modifications. Benchmark on stable runners, store baselines, and investigate meaningful regressions instead of using flaky absolute timing thresholds.

Production release acceptance requires all of the following:

1. Every applicable core feature from the baseline has a ledger entry and verified implementation or an explicitly accepted, documented Python difference. Remaining unimplemented SQL features block a broad parity claim.
2. PostgreSQL, MySQL, SQLite, and SQL Server pass live release suites. PGlite/platform applicability is explicitly recorded.
3. The enhanced typing target passes scope/projection/nullability/write/CTE/subquery tests; checker limitations are published, not hidden.
4. Codegen round-trips live schemas into importable, checked modules with deterministic drift checks and driver-consistent data types.
5. Transactions, streaming, cancellation, shutdown, migration locks, and unknown commit outcomes have failure-path tests.
6. The built wheel/sdist includes required exports, typing metadata, and third-party notices and works without undeclared extras.
7. Documentation and examples reflect actual shipped behavior; no placeholder public implementations or broad xfails remain.
8. Support versions, changelog, deprecation policy, security-reporting instructions, and release procedure exist.

Prepare publishing automation with trusted publishing where available, but keep actual release invocation separate from building/testing. Check name availability before registry setup. Do not call an unreleased repository production-ready merely because the architecture targets production.

## 12. Construction sequence and acceptance by stage

These stages are the route to the full project. Do not redefine stage 1 or 2 as the requested final scope.

| Stage | Implement | Exit evidence |
| --- | --- | --- |
| 0. Baseline and tooling | Repo, uv, exports/case inventory, ADRs, CI skeleton, fixture schemas | Locked install; baseline recorded; executable ledger checker |
| 1. Type and AST foundations | Catalog generics, nodes/visitors, mypy state representation, generated sample | Difficult typing fixtures pass; immutable AST tests; portable contracts honest |
| 2. Execution spine | Compiler profiles, executor, plugins protocol, drivers/providers, transactions | Real query per engine; binds correct; lifecycle/failure tests |
| 3. Complete SQL surface | All query families, expressions, helpers, DDL, capability checks | Runtime/compiler/type mappings for every applicable case |
| 4. Schema and lifecycle tooling | Full introspection/codegen, migrations, built-in plugins, advanced streaming/cancellation | Golden/live generation, concurrent migrations, resource/race suites |
| 5. Parity and release hardening | Differential checks, full checker matrix, packaging/docs/performance | All production acceptance gates evidenced |

Typing and runtime tests accompany every feature rather than being postponed to stage 5. Schema generation starts with the permanent sample in stage 1 and expands in stage 4. Cancellation and transactions are part of the execution design before advanced queries are added.

### 12.1 First agent session: concrete tasks

1. Inspect the destination repository and applicable local instructions. Preserve existing work. Create the project if absent and copy this handoff into `internal/handoff/architecture.md`.
2. Fetch the pinned Kysely snapshot into a reference-only location. Record its hash/version in `docs/parity/upstream.json`; do not ship its checkout in the Python wheel.
3. Inventory all public exports and runtime/type cases, including nested test names and dialect exclusions. Use parsing or careful manual verification; regex title counts alone are not a complete inventory.
4. Set up uv, pyproject, lockfile, Ruff, pytest, mypy/Pyright, docs, and CI service definitions. Add real package import/build tests.
5. Write ADRs for portable versus enhanced typing, source/alias provenance, result shape, driver/binding profiles, async lifecycle, and duplicate-name policy.
6. Implement a permanent generated-schema fixture, typed table/column primitives, immutable selection/reference/value nodes, visitor/compiler, and minimal executor contracts.
7. Implement the hard typing fixtures from section 6.3 in tandem with those primitives. Add real SQL execution through one provisioned driver while wiring the other dialect jobs. Continue into the next stage when foundations are sound.
8. Commit logical increments when the destination workflow permits. Maintain a precise handoff with completed work, outstanding ledger IDs, test commands/results, blockers, and next actions. Do not end the session with only scaffolding if implementation can continue.

### 12.2 Decisions already made versus delegated

| Fixed direction | Agent implementation choice |
| --- | --- |
| Pysely name; production parity target | Resolve a demonstrated package-name conflict with owner |
| Kysely-oriented module structure and test lineage | Python file granularity and internal helper layout |
| uv, Python package, optional driver/checker dependencies | Exact tested dependency ranges and lock versions |
| Immutable SQL AST and parameterized execution | Efficient node representation and visitor dispatch |
| Generated read/insert/update schemas and typed references | Final serializable metadata format and code renderer |
| Portable typing plus enhanced mypy inference | Plugin state implementation, documented inference fallbacks |
| Four conventional SQL engines in target | Driver selection after concrete compatibility checks |
| Comprehensive real-engine and type tests | CI topology and worker isolation details |

Escalate only material scope changes or evidence that the typing goals cannot be achieved under the stated contract. Do not repeatedly ask permission for ordinary implementation decisions.

## 13. Known risks and prohibited shortcuts

- **Type-checker portability:** codegen plus mypy does not automatically reproduce editor behavior everywhere. Keep separate verified contracts.
- **Scope provenance:** a bare `Column[int]` is insufficient for aliases and null-extending joins. Preserve identity and dependencies.
- **Type/runtime mismatch:** do not infer Decimal/UUID/JSON results while returning driver strings without a declared mapping.
- **String API ergonomics:** plugin support can validate literals, but does not guarantee string completion in other editors.
- **Driver adaptation:** placeholders, row counts, cursor behavior, and cancellation differ across drivers of the same engine.
- **Migrations:** local mutexes do not protect two processes, and rollback cannot undo all DDL on every engine.
- **Resource safety:** never release an in-flight connection to the pool after cancelling only the Python task.
- **False completion:** no broad `Any`, unchecked casts, giant placeholder modules, silent skips, fake drivers standing in for integration tests, or automatic snapshot acceptance to manufacture a green build.
- **Scope drift:** do not spend the initial implementation on a website, logo, application ORM, or synchronous facade while core parity remains unfinished.

## 14. Continuation record template

Keep `internal/handoff/STATUS.md` current with:

```markdown
# Pysely implementation status
Baseline commit:
Current project commit:
Current stage:

## Implemented and verified
- Feature/ledger ID, behavior, relevant tests.

## Implemented but unverified
- Exact missing environment/check and impact.

## Remaining parity gaps
- Ledger IDs, dependencies, next concrete implementation steps.

## Validation
- Command, environment, result, skips/xfails, artifact location.

## Decisions and blockers
- ADR links, unresolved evidence, any required owner decision.

## Next session
- Ordered actions that continue the implementation directly.
```

## 15. Primary references

- [Kysely source at the inspected commit](https://github.com/kysely-org/kysely/tree/c54987f4d5bb1a9573c8d83e1cba7365770cc016): architecture, exports, license, and implementation baseline.
- [Kysely runtime tests at the baseline](https://github.com/kysely-org/kysely/tree/c54987f4d5bb1a9573c8d83e1cba7365770cc016/test/node/src): SQL expectations and live behavior.
- [Kysely typing tests at the baseline](https://github.com/kysely-org/kysely/tree/c54987f4d5bb1a9573c8d83e1cba7365770cc016/test/typings/test-d): positive/negative inference behavior.
- [Dialect interface](https://kysely-org.github.io/kysely-apidoc/interfaces/Dialect.html): four-part dialect boundary; live docs can differ from the pinned source.
- [kysely-codegen](https://github.com/RobinBlomberg/kysely-codegen): database-to-schema generation model; separate project from Kysely core.
- [Python typing](https://docs.python.org/3/library/typing.html): standard typing primitives and their runtime/static distinction.
- [Extending mypy](https://mypy.readthedocs.io/en/stable/extending_mypy.html): plugin hooks and compatibility constraints.
- [uv dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/), [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/), [uv package builds](https://docs.astral.sh/uv/guides/package/): project workflow references.
- [pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html) and [Hypothesis](https://hypothesis.readthedocs.io/en/latest/): test infrastructure.

The architecture choices and release gates in this document are proposed Pysely requirements. They are not claims that the upstream projects require these Python-specific choices or that feasibility has already been demonstrated by an implementation.


## Appendix A. Inspected upstream test-file inventory

The pinned snapshot contains **51 runtime test files** in `test/node/src` and **30 typing test files** in `test/typings/test-d`. These are file counts, not case counts or a claim of complete upstream test coverage. Inventory other test directories and public exports during stage 0.

Each runtime file below should map to `test/runtime/test_<snake_case_topic>.py`, with compilation cases also represented in `test/compiler/`. Each typing file should map to positive/negative fixtures under `test/typings/`. Split large files by behavior as needed while retaining upstream lineage.

### Runtime files

- `aggregate-function.test.ts`
- `array.test.ts`
- `async-dispose.test.ts`
- `camel-case.test.ts`
- `cancellation.test.ts`
- `case.test.ts`
- `clear.test.ts`
- `coalesce.test.ts`
- `controlled-transaction.test.ts`
- `deduplicate-joins.test.ts`
- `delete.test.ts`
- `disconnects.test.ts`
- `error-stack.test.ts`
- `execute.test.ts`
- `explain.test.ts`
- `expression.test.ts`
- `file-migration-provider.test.ts`
- `group-by.test.ts`
- `handle-empty-in-lists-plugin.test.ts`
- `having.test.ts`
- `immediate-value-plugin.test.ts`
- `insert.test.ts`
- `introspect.test.ts`
- `join.test.ts`
- `json-traversal.test.ts`
- `json.test.ts`
- `log-once.test.ts`
- `logging.test.ts`
- `merge.test.ts`
- `migration.test.ts`
- `object-util.test.ts`
- `order-by.test.ts`
- `parse-json-results-plugin.test.ts`
- `performance.test.ts`
- `plugin-composition.test.ts`
- `query-id.test.ts`
- `raw-query.test.ts`
- `raw-sql.test.ts`
- `replace.test.ts`
- `safe-null-comparison-plugin.test.ts`
- `sanitize-identifiers.test.ts`
- `schema.test.ts`
- `select.test.ts`
- `set-operation.test.ts`
- `sql-injection.test.ts`
- `stream.test.ts`
- `transaction.test.ts`
- `update.test.ts`
- `where.test.ts`
- `with-schema.test.ts`
- `with.test.ts`

### Typing files

- `aggregate-function.test-d.ts`
- `alter-table.test-d.ts`
- `alter-type.test-d.ts`
- `assert-type.test-d.ts`
- `case.test-d.ts`
- `clear.test-d.ts`
- `coalesce.test-d.ts`
- `create-table.test-d.ts`
- `delete-query-builder.test-d.ts`
- `expression.test-d.ts`
- `generic-pre-5.4.test-d.ts`
- `generic.test-d.ts`
- `huge-db.test-d.ts`
- `if.test-d.ts`
- `index.test-d.ts`
- `infer-result.test-d.ts`
- `insert.test-d.ts`
- `join.test-d.ts`
- `json-traversal.test-d.ts`
- `kysely-any.test-d.ts`
- `merge.test-d.ts`
- `postgres-json.test-d.ts`
- `readonly.test-d.ts`
- `select-from.test-d.ts`
- `select-no-from.test-d.ts`
- `select.test-d.ts`
- `set-operation.test-d.ts`
- `update.test-d.ts`
- `where.test-d.ts`
- `with.test-d.ts`

JavaScript-specific files such as async disposal, stack traces, compiler-version compatibility, and module exports need Python-equivalent semantics rather than superficial syntax translation. File-level inventory is the starting point; the case ledger remains the completion authority.
