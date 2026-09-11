# Editor diagnostics

Pysely forwards standard language-server diagnostics unchanged in the playground.
With equivalent versions and settings, the same public types produce the same
language intelligence in VS Code with Pylance.

Invalid literal columns receive argument-level diagnostics. The failing call
also receives a call-level diagnostic spanning the fluent chain that is its
receiver.

Pyright's `strict` mode additionally reports "type of X is unknown" for every
later call in the chain. The playground runs Pyright's default `standard` mode,
which does not, so the argument-level diagnostic stays visible. This is a
settings choice, not filtering; Pylance offers the same mode.

Fluent query chains remain the intended API. Pysely does not add browser-only
diagnostic filtering or use a custom editor plugin to hide this behavior.
