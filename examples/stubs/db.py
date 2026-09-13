import aiosqlite

from pysely import SqliteDialect

from .dbschema import DatabaseSchema

db = DatabaseSchema.connect(
    dialect=SqliteDialect(database=lambda: aiosqlite.connect("app.sqlite3"))
)
