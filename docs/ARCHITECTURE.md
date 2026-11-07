# Architecture

`sql-format-lint` is a deterministic, standard-library-only SQL tokenizer, formatter, and linter.

## Lexing / Tokenizing

Lexing uses a single left-to-right scanning loop without regex backtracking over the whole input.
Tokens preserve verbatim byte content for strings, quoted identifiers, comments, and dollar-quoted blocks (`$$` or `$tag$`).

Input bounds are strictly enforced:
- `max_chars`: raises `SqlError('input_too_large')`
- `max_depth`: raises `SqlError('too_deep')` when parenthesis nesting exceeds the limit

## Formatting

At parenthesis depth 0, clauses (`SELECT`, `FROM`, `WHERE`, `JOIN`, `GROUP BY`, `ORDER BY`, etc.) start a line.
Select lists with multiple items place each item on an indented line. `AND` and `OR` inside `WHERE` or `HAVING` start indented lines.
Formatting is provably token-preserving and idempotent.

## Linting

Six AST/token-level rules run in a single pass:
- `L001`: `select_star`
- `L002`: `update_without_where` / `delete_without_where`
- `L003`: `implicit_cross_join`
- `L004`: `order_by_ordinal`
- `L005`: `not_in_subquery`
- `L006`: `limit_without_order`
