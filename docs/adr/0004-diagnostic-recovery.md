# Editor diagnostics

## Decision

Forward stock language-server diagnostics unchanged in the playground.
Use equivalent versions and settings when comparing with Pylance.

## What users see

- An invalid literal column produces an argument-level error.
- The failing call can also produce an error spanning the query chain.
- In `strict` mode, later calls may report unknown types.

## Playground setting

The playground uses Pyright `standard` mode to avoid the additional strict-mode
unknown-type messages. This is a setting, not diagnostic filtering.

Chained queries remain the intended API. No custom editor plugin is required.
