# sql-format-lint

[![PyPI version](https://img.shields.io/pypi/v/trysac-sql-format-lint)](https://pypi.org/project/trysac-sql-format-lint/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-sql-format-lint)](LICENSE)
[![CI](https://github.com/Trysac/u171-sql-format-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u171-sql-format-lint/actions/workflows/ci.yml)

Format SQL deterministically with a quote-aware tokenizer, one clause per line and uppercase keywords, and lint queries for six common mistakes with line and column

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-sql-format-lint
# or
uv add trysac-sql-format-lint
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import sql_format_lint

# normalize() trims surrounding whitespace and lower-cases the text.
print(sql_format_lint.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    sql_format_lint.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
