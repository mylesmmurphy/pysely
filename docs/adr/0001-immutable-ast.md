# ADR 0001: Immutable operation tree

Status: accepted.

## Decision

Query builders hold frozen, slotted dataclasses with tuple children.
Each builder call returns a new builder and shares unchanged nodes.

## Caller responsibility

Bound values remain references to caller-owned objects.
Do not mutate them during execution.
