# ADR 0001: Immutable operation tree

Status: accepted

Query builders hold frozen, slotted dataclasses and tuple children. Each builder
method returns a new builder and structurally shares unchanged nodes. Values remain
opaque references and callers must not mutate them during execution.

