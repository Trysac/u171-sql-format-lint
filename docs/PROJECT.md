# Project record

## Objective

Format SQL deterministically with a quote-aware tokenizer, one clause per line and uppercase keywords, and lint queries for six common mistakes with line and column.

## Scope

- **In scope**: deterministic tokenization, idempotent formatting that preserves tokens exactly, and six specific lint rules: select_star, update/delete without WHERE, implicit cross joins, order by ordinal, NOT IN with subquery, and LIMIT without ORDER BY.
- **Out-of-scope**: dialect-specific syntax, nested comment blocks, subquery and CASE multi-line layout, configurable styles, autofix of lint findings, or DDL safety checks.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 2223771 / 22432 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.4019 |

## Factory run u171 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4659 | 13625 | 0 | 0 | 0.0273 |
| fix-1 | gemini-3.8-flash | no | 56024 | 2086 | 0 | 324071 | 0.0741 |
| fix-2 | gemini-3.8-flash | no | 74335 | 2827 | 0 | 577495 | 0.1097 |
| fix-3 | gemini-3.8-flash | no | 23494 | 894 | 0 | 51112 | 0.0248 |
| fix-4 | gemini-3.8-flash | no | 18480 | 569 | 0 | 23200 | 0.0177 |
| audit | gemini-3.1-flash-lite | no | 85871 | 476 | 0 | 424455 | 0.0328 |
| fix-1 | gemini-3.8-flash | no | 72339 | 693 | 0 | 373118 | 0.0848 |
| docs | gemini-3.1-flash-lite | no | 115118 | 1262 | 0 | 0 | 0.0307 |

Total: $0.4019. Prices: Anthropic list prices.
