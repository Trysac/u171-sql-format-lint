# sql-format-lint

SQL in repositories is often formatted by hand, leading to noisy diffs and missed query anti-patterns. Existing formatters often rely on regexes that break string literals, quoted identifiers, or dollar-quoted bodies.

`sql-format-lint` provides a deterministic, quote-aware SQL tokenizer, an idempotent formatter that preserves tokens, and a linter for six common anti-patterns.

## Installation

```bash
pip install trysac-sql-format-lint
```

## Usage

```python
import sql_format_lint as sql

query = "select a,b from t where x=1 and y=2"
formatted = sql.format_sql(query)
findings = sql.lint(formatted)
assert len(findings) == 0
```

## CLI

```bash
# Format a query file
python -m sql_format_lint format query.sql

# Check if a file is formatted
python -m sql_format_lint check query.sql

# Lint query file for anti-patterns
python -m sql_format_lint lint query.sql
```

## API Summary

- `tokenize(sql, *, max_chars=1_000_000) -> list[Token]`: Tokenizes SQL. Raises `SqlError` for `input_too_large`, `unterminated_string`, `unterminated_comment`, `unterminated_quoted_ident`, `unterminated_dollar`, or `too_deep`.
- `format_sql(sql, *, indent=2) -> str`: Returns deterministically formatted SQL. Clause-aware, token-preserving, and idempotent.
- `lint(sql) -> list[Finding]`: Returns a list of violations for six rules.
- `main(argv=None) -> int`: CLI entry point for `format`, `check`, and `lint` commands.

## Why not sqlparse or sqlfluff?

`sql-format-lint` has zero dependencies and is a provably token-preserving, idempotent formatter, whereas alternatives rely on complex parser logic that may not guarantee token stability.

For more details, see [docs/SECURITY.md](docs/SECURITY.md).
