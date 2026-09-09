# ADR 0003: Portable and enhanced typing

Status: accepted

Runtime catalog generics expose precise column read, insert, and update types without
a checker plugin. Arbitrary projection shapes remain conservative in portable typing.
An optional mypy plugin will add scope and named-projection inference without becoming
a runtime dependency.

