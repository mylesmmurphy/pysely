# Editor diagnostics

Pysely forwards standard language-server diagnostics unchanged in the playground.
With equivalent versions and settings, the same public types produce the same
language intelligence in VS Code with Pylance.

Invalid literal columns in ordinary query methods receive argument-level
diagnostics. Some failed overloads and missing arguments can cause the language
server to highlight a larger fluent expression and report follow-on unknown types.
This is a current limitation of portable Python typing.

Fluent query chains remain the intended API. Pysely does not add browser-only
diagnostic filtering or use a custom editor plugin to hide this behavior.
