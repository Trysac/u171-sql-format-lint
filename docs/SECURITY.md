# Security notes

## Threat model

`sql-format-lint` is a pure Python library with no runtime dependencies and no I/O operations inside the formatting or linting functions.

- **Defended**: The package handles potentially hostile input by enforcing strict size (`max_chars`) and nesting depth (`max_depth`) limits. It avoids dangerous operations like `eval` or `exec`.
- **Not defended**: The package does not perform semantic analysis or schema validation; it is a lexical and structural tool. Callers are responsible for the security context of the SQL queries themselves.

## Limits

- `max_chars`: Default limit is 1,000,000 characters. Exceeding this raises `SqlError('input_too_large')`.
- `max_depth`: Default limit is 100 levels of nested parentheses. Exceeding this raises `SqlError('too_deep')`.
