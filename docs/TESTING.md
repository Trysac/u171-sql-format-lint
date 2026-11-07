# Testing

## Running

```sh
uv run pytest --cov=sql_format_lint   # tests with coverage report
uv run python scripts/check.py      # every gate
```

## Coverage

Tests cover the following areas:
- `test_sql_format_lint.py`: exercises the public API (`tokenize`, `format_sql`, `lint`) with varied input, including comments, string literals, and nested structures to assert correct tokenization and formatting.
- The test suite asserts every observable effect, including return values and raised `SqlError` exceptions with specific codes (e.g., `unterminated_string`, `too_deep`).
