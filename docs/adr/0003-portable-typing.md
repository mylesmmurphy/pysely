# ADR 0003: Portable and enhanced typing

Status: accepted

Runtime catalog generics expose precise column read, insert, and update types without
a checker plugin. Arbitrary projection shapes remain conservative in portable typing.
The optional `pysely.mypy` plugin adds scope and named-projection inference for
literal string read queries without becoming a runtime dependency. Annotated
table classes and a database registry supply schema information; normal string
reads do not require catalog objects or `.c` access.

Mypy hooks do not provide completion support to Pylance. The Monaco playground
uses a schema-aware completion provider. External editor completion integration
is a separate remaining requirement.
