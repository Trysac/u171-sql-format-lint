# Zero-dependency deterministic SQL tokenizer, clause formatter, and linter

Status: accepted (generated, pending human review)

## Context

SQL in repositories is frequently formatted by hand or with regex-based scripts that mangle string literals, dollar quotes, and quoted identifiers. Furthermore, static analysis tools like sqlfluff carry large dependency graphs and complex configurations.

## Decision

Implement a pure Python standard-library tokenizer, formatter, and 6-rule linter. Formatting operates by inspecting tokens at parenthesis depth 0, preserving all string/identifier contents byte-for-byte, and enforcing idempotency.

## Consequences

Users get instant, zero-dependency formatting and linting. Dialect-specific non-standard syntax outside standard SQL clauses is treated transparently as operators/identifiers without mangling.
