"""Deterministic SQL formatter and linter with zero dependencies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "Finding",
    "SqlError",
    "Token",
    "__version__",
    "format_sql",
    "lint",
    "main",
    "tokenize",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

TokenKind = Literal[
    "whitespace",
    "comment",
    "string",
    "quoted_ident",
    "dollar",
    "number",
    "word",
    "operator",
    "punct",
]

ErrorCode = Literal[
    "unterminated_string",
    "unterminated_comment",
    "unterminated_quoted_ident",
    "unterminated_dollar",
    "input_too_large",
    "too_deep",
]


class SqlError(Exception):
    """Base exception raised on syntax errors, size violations, or depth limits."""

    def __init__(self, code: ErrorCode, line: int, col: int, message: str | None = None) -> None:
        self.code: ErrorCode = code
        self.line: int = line
        self.col: int = col
        msg = message or f"{code} at line {line}, column {col}"
        if len(msg) > 200:
            msg = msg[:197] + "..."
        super().__init__(msg)


@dataclass(frozen=True)
class Token:
    """Lexical token in SQL text."""

    kind: TokenKind
    text: str
    line: int
    col: int


@dataclass(frozen=True)
class Finding:
    """A lint rule violation with source coordinates."""

    rule: str
    line: int
    col: int
    message: str


KEYWORDS: frozenset[str] = frozenset(
    {
        "SELECT",
        "DISTINCT",
        "FROM",
        "WHERE",
        "AND",
        "OR",
        "NOT",
        "IN",
        "IS",
        "NULL",
        "AS",
        "ON",
        "JOIN",
        "LEFT",
        "RIGHT",
        "FULL",
        "INNER",
        "OUTER",
        "CROSS",
        "GROUP",
        "BY",
        "HAVING",
        "ORDER",
        "ASC",
        "DESC",
        "LIMIT",
        "OFFSET",
        "UNION",
        "ALL",
        "INSERT",
        "INTO",
        "VALUES",
        "UPDATE",
        "SET",
        "DELETE",
        "WITH",
        "CASE",
        "WHEN",
        "THEN",
        "ELSE",
        "END",
        "EXISTS",
        "BETWEEN",
        "LIKE",
        "COUNT",
    }
)

MULTI_OPERATORS: tuple[str, ...] = (
    "::",
    "<>",
    "<=",
    ">=",
    "!=",
    "||",
)

SINGLE_OPERATORS: frozenset[str] = frozenset({"=", "<", ">", "+", "-", "*", "/", "%"})
PUNCTUATION: frozenset[str] = frozenset({"(", ")", ",", ";", "."})


def tokenize(sql: str, *, max_chars: int = 1_000_000) -> list[Token]:
    """Tokenize SQL text into structured tokens in a single left-to-right pass.

    Raises:
        SqlError: when the input exceeds max_chars or contains unterminated tokens.
    """
    if len(sql) > max_chars:
        raise SqlError("input_too_large", 1, 1, "input length exceeds max_chars limit")

    tokens: list[Token] = []
    n = len(sql)
    pos = 0
    line = 1
    col = 1

    while pos < n:
        c = sql[pos]
        tok_line = line
        tok_col = col

        # Whitespace
        if c.isspace():
            start = pos
            while pos < n and sql[pos].isspace():
                if sql[pos] == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                pos += 1
            tokens.append(Token("whitespace", sql[start:pos], tok_line, tok_col))
            continue

        # Line comment: --
        if c == "-" and pos + 1 < n and sql[pos + 1] == "-":
            start = pos
            while pos < n and sql[pos] != "\n":
                pos += 1
                col += 1
            tokens.append(Token("comment", sql[start:pos], tok_line, tok_col))
            continue

        # Block comment: /* ... */
        if c == "/" and pos + 1 < n and sql[pos + 1] == "*":
            start = pos
            pos += 2
            col += 2
            closed = False
            while pos + 1 < n:
                if sql[pos] == "*" and sql[pos + 1] == "/":
                    pos += 2
                    col += 2
                    closed = True
                    break
                if sql[pos] == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                pos += 1
            if not closed:
                raise SqlError("unterminated_comment", tok_line, tok_col)
            tokens.append(Token("comment", sql[start:pos], tok_line, tok_col))
            continue

        # Single-quoted string literal
        if c == "'":
            start = pos
            pos += 1
            col += 1
            closed = False
            while pos < n:
                ch = sql[pos]
                if ch == "'":
                    if pos + 1 < n and sql[pos + 1] == "'":
                        pos += 2
                        col += 2
                        continue
                    pos += 1
                    col += 1
                    closed = True
                    break
                if ch == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                pos += 1
            if not closed:
                raise SqlError("unterminated_string", tok_line, tok_col)
            tokens.append(Token("string", sql[start:pos], tok_line, tok_col))
            continue

        # Double-quoted identifier
        if c == '"':
            start = pos
            pos += 1
            col += 1
            closed = False
            while pos < n:
                ch = sql[pos]
                if ch == '"':
                    if pos + 1 < n and sql[pos + 1] == '"':
                        pos += 2
                        col += 2
                        continue
                    pos += 1
                    col += 1
                    closed = True
                    break
                if ch == "\n":
                    line += 1
                    col = 1
                else:
                    col += 1
                pos += 1
            if not closed:
                raise SqlError("unterminated_quoted_ident", tok_line, tok_col)
            tokens.append(Token("quoted_ident", sql[start:pos], tok_line, tok_col))
            continue

        # Dollar quote: $tag$...$tag$
        if c == "$":
            idx = pos + 1
            valid_tag = True
            while idx < n and sql[idx] != "$":
                ch_t = sql[idx]
                if idx == pos + 1:
                    if not (ch_t.isalpha() or ch_t == "_"):
                        valid_tag = False
                        break
                else:
                    if not (ch_t.isalnum() or ch_t == "_"):
                        valid_tag = False
                        break
                idx += 1
            if valid_tag and idx < n and sql[idx] == "$":
                tag_end = idx + 1
                tag = sql[pos:tag_end]
                body_start = tag_end
                closing_idx = sql.find(tag, body_start)
                if closing_idx == -1:
                    raise SqlError("unterminated_dollar", tok_line, tok_col)
                end_pos = closing_idx + len(tag)
                # calculate newlines across tag and body
                for p in range(pos, end_pos):
                    if sql[p] == "\n":
                        line += 1
                        col = 1
                    else:
                        col += 1
                tokens.append(Token("dollar", sql[pos:end_pos], tok_line, tok_col))
                pos = end_pos
                continue

        # Numbers: digits with optional decimals and scientific notation
        if c.isdigit():
            start = pos
            while pos < n and sql[pos].isdigit():
                pos += 1
                col += 1
            if pos < n and sql[pos] == "." and pos + 1 < n and sql[pos + 1].isdigit():
                pos += 1
                col += 1
                while pos < n and sql[pos].isdigit():
                    pos += 1
                    col += 1
            if pos < n and sql[pos] in ("e", "E"):
                peek = pos + 1
                if peek < n and sql[peek] in ("+", "-"):
                    peek += 1
                if peek < n and sql[peek].isdigit():
                    col += peek - pos
                    pos = peek
                    while pos < n and sql[pos].isdigit():
                        pos += 1
                        col += 1
            tokens.append(Token("number", sql[start:pos], tok_line, tok_col))
            continue

        # Words: [A-Za-z_][A-Za-z0-9_$]*
        if c.isalpha() or c == "_":
            start = pos
            while pos < n and (sql[pos].isalnum() or sql[pos] in ("_", "$")):
                pos += 1
                col += 1
            tokens.append(Token("word", sql[start:pos], tok_line, tok_col))
            continue

        # Multi-char operators
        matched_op = None
        for op in MULTI_OPERATORS:
            if sql.startswith(op, pos):
                matched_op = op
                break
        if matched_op:
            tokens.append(Token("operator", matched_op, tok_line, tok_col))
            pos += len(matched_op)
            col += len(matched_op)
            continue

        # Single-char operators
        if c in SINGLE_OPERATORS:
            tokens.append(Token("operator", c, tok_line, tok_col))
            pos += 1
            col += 1
            continue

        # Punctuation
        if c in PUNCTUATION:
            tokens.append(Token("punct", c, tok_line, tok_col))
            pos += 1
            col += 1
            continue

        # Anything else is a one-character operator token
        tokens.append(Token("operator", c, tok_line, tok_col))
        pos += 1
        col += 1

    return tokens


def _split_statements(tokens: list[Token]) -> list[list[Token]]:
    """Split a sequence of tokens into statements separated by top-level semicolons."""
    statements: list[list[Token]] = []
    current: list[Token] = []
    depth = 0
    for tok in tokens:
        if tok.kind == "punct" and tok.text == "(":
            depth += 1
        elif tok.kind == "punct" and tok.text == ")" and depth > 0:
            depth -= 1
        current.append(tok)
        if depth == 0 and tok.kind == "punct" and tok.text == ";":
            statements.append(current)
            current = []
    if current and any(t.kind != "whitespace" for t in current):
        statements.append(current)
    return statements


def _check_depth(tokens: list[Token], max_depth: int = 100) -> None:
    """Ensure parenthesis nesting does not exceed max_depth."""
    depth = 0
    for tok in tokens:
        if tok.kind == "punct" and tok.text == "(":
            depth += 1
            if depth > max_depth:
                raise SqlError("too_deep", tok.line, tok.col, "nested parenthesis limit exceeded")
        elif tok.kind == "punct" and tok.text == ")" and depth > 0:
            depth -= 1


_JOIN_WORDS = {"JOIN", "LEFT", "RIGHT", "FULL", "INNER", "CROSS", "OUTER"}


def _match_clause_at(tokens: list[Token], index: int) -> tuple[str, int] | None:
    """Match a depth-0 clause heading starting at tokens[index].

    Returns (canonical_clause_str, num_tokens_consumed) or None.
    """
    # Helper to peek up to N non-whitespace tokens
    n = len(tokens)
    t0 = tokens[index]
    if t0.kind != "word":
        return None

    w0 = t0.text.upper()

    def next_word(start: int) -> tuple[str, int] | None:
        i = start
        while i < n:
            tok = tokens[i]
            if tok.kind == "whitespace":
                i += 1
                continue
            if tok.kind == "word":
                return tok.text.upper(), i
            return None
        return None

    if w0 in (
        "WITH",
        "SELECT",
        "FROM",
        "WHERE",
        "HAVING",
        "LIMIT",
        "OFFSET",
        "VALUES",
        "UPDATE",
        "SET",
    ):
        return w0, 1

    if w0 == "GROUP":
        nw = next_word(index + 1)
        if nw and nw[0] == "BY":
            return "GROUP BY", (nw[1] - index + 1)
        return None

    if w0 == "ORDER":
        nw = next_word(index + 1)
        if nw and nw[0] == "BY":
            return "ORDER BY", (nw[1] - index + 1)
        return None

    if w0 == "UNION":
        nw = next_word(index + 1)
        if nw and nw[0] == "ALL":
            return "UNION ALL", (nw[1] - index + 1)
        return "UNION", 1

    if w0 == "INSERT":
        nw = next_word(index + 1)
        if nw and nw[0] == "INTO":
            return "INSERT INTO", (nw[1] - index + 1)
        return None

    if w0 == "DELETE":
        nw = next_word(index + 1)
        if nw and nw[0] == "FROM":
            return "DELETE FROM", (nw[1] - index + 1)
        return "DELETE", 1

    # Joins: [LEFT|RIGHT|FULL|INNER|CROSS] [OUTER] JOIN or JOIN
    if w0 in _JOIN_WORDS:
        # Check if this sequence leads to JOIN
        curr = index
        matched: list[str] = [w0]
        last_idx = index
        while curr < n:
            nw = next_word(curr + 1)
            if not nw:
                break
            word, widx = nw
            if word in _JOIN_WORDS:
                matched.append(word)
                curr = widx
                last_idx = widx
            else:
                break
        if "JOIN" in matched:
            return " ".join(matched), (last_idx - index + 1)

    return None


def format_sql(sql: str, *, indent: int = 2) -> str:
    """Deterministically format SQL text.

    Clause-aware, token-preserving, idempotent formatting at depth 0.
    """
    raw_tokens = tokenize(sql)
    _check_depth(raw_tokens)

    if not raw_tokens or all(t.kind == "whitespace" for t in raw_tokens):
        return ""

    statements = _split_statements(raw_tokens)
    formatted_stmts: list[str] = []

    for stmt_tokens in statements:
        res = _format_single_statement(stmt_tokens, indent=indent)
        if res:
            formatted_stmts.append(res)

    if not formatted_stmts:
        return ""

    # Statements separated by ';' are joined by a blank line; output ends with one newline.
    out = "\n\n".join(formatted_stmts)
    if not out.endswith("\n"):
        out += "\n"
    return out


def _format_single_statement(tokens: list[Token], *, indent: int) -> str:
    # Separate into logical lines / items.
    # Depth 0 clauses start on their own line:
    # WITH, SELECT, FROM, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET, UNION [ALL],
    # INSERT INTO, VALUES, UPDATE, SET, DELETE FROM, and joins.
    #
    # A SELECT list with more than 1 item puts each item on its own line indented by indent spaces,
    # a comma ending each but the last.
    #
    # AND and OR inside WHERE or HAVING start a new indented line.
    #
    # Content inside parentheses stays on one line.
    #
    # Comments are kept; a line comment ends its line.
    #
    # Spacing rules: single space between tokens, none before , ) . ; or after ( and .
    # None between non-keyword word (or COUNT) and its '(', while others keep space (IN (...)).
    # Operators get one space on each side, except :: and unary minus after operator or '('.

    # First, let's analyze non-whitespace tokens, noting where comments are.
    # Notice: we should normalize keywords to uppercase if they are 'word' kind and match KEYWORDS.
    processed_tokens: list[Token] = []
    for t in tokens:
        if t.kind == "word" and t.text.upper() in KEYWORDS:
            processed_tokens.append(Token(t.kind, t.text.upper(), t.line, t.col))
        else:
            processed_tokens.append(t)

    # Output lines sequence:
    # Inspect select item count at depth 0 to see if SELECT has >1 items.
    # To do that, find the depth-0 SELECT clause and count top-level commas before the next clause.
    select_item_counts: dict[int, int] = {}
    depth = 0
    i = 0
    while i < len(processed_tokens):
        tok = processed_tokens[i]
        if tok.kind == "punct" and tok.text == "(":
            depth += 1
        elif tok.kind == "punct" and tok.text == ")" and depth > 0:
            depth -= 1
        elif depth == 0:
            clause_info = _match_clause_at(processed_tokens, i)
            if clause_info and clause_info[0] == "SELECT":
                sel_idx = i
                # Count items
                j = i + clause_info[1]
                commas = 0
                inner_depth = 0
                has_item = False
                while j < len(processed_tokens):
                    tj = processed_tokens[j]
                    if tj.kind == "punct" and tj.text == "(":
                        inner_depth += 1
                    elif tj.kind == "punct" and tj.text == ")" and inner_depth > 0:
                        inner_depth -= 1
                    elif inner_depth == 0:
                        cinfo = _match_clause_at(processed_tokens, j)
                        if cinfo:
                            break
                        if tj.kind == "punct" and tj.text == ";":
                            break
                        if tj.kind == "punct" and tj.text == ",":
                            commas += 1
                        elif (
                            tj.kind not in ("whitespace", "comment")
                            and tj.text.upper() != "DISTINCT"
                        ):
                            has_item = True
                    j += 1
                items = (commas + 1) if (has_item or commas > 0) else 0
                select_item_counts[sel_idx] = items
        i += 1

    lines: list[str] = []
    current_line = ""
    current_clause = ""
    depth = 0
    multi_line_select = False
    select_depth_clause_count = 0
    prev_token: Token | None = None
    prev_sig_token: Token | None = None
    unary_pending = False  # the token after a unary minus attaches to it

    i = 0
    n = len(processed_tokens)

    def flush_line() -> None:
        nonlocal current_line
        if current_line.rstrip():
            lines.append(current_line.rstrip())
        current_line = ""

    while i < n:
        tok = processed_tokens[i]

        if tok.kind == "whitespace":
            i += 1
            continue

        # Check parenthesis depth changes
        if tok.kind == "punct" and tok.text == "(":
            depth += 1
        elif tok.kind == "punct" and tok.text == ")" and depth > 0:
            depth -= 1

        # Check if depth-0 clause matches at this position
        clause_info = None
        if depth == 0:
            clause_info = _match_clause_at(processed_tokens, i)

        if clause_info:
            clause_name, consumed = clause_info
            flush_line()
            current_clause = clause_name
            multi_line_select = current_clause == "SELECT" and select_item_counts.get(i, 0) > 1
            select_depth_clause_count = 0

            # Emit clause words
            clause_words = clause_name.split()
            current_line = " ".join(clause_words)
            # advance i by consumed
            prev_token = processed_tokens[i + consumed - 1]
            prev_sig_token = prev_token
            i += consumed
            continue

        # Check if we are inside multi-line SELECT at depth 0 and see distinct / first item / comma
        if depth == 0 and current_clause == "SELECT" and multi_line_select:
            if tok.kind == "word" and tok.text == "DISTINCT":
                current_line += " DISTINCT"
                prev_token = tok
                prev_sig_token = tok
                i += 1
                continue
            if select_depth_clause_count == 0:
                # First item starts on a new indented line
                flush_line()
                current_line = " " * indent
                select_depth_clause_count = 1
            elif tok.kind == "punct" and tok.text == ",":
                # Comma ends current item line; next item starts on new line indented
                current_line += ","
                flush_line()
                current_line = " " * indent
                prev_token = tok
                prev_sig_token = tok
                i += 1
                continue

        # AND / OR inside WHERE or HAVING at depth 0 start a new indented line
        if (
            depth == 0
            and current_clause in ("WHERE", "HAVING")
            and tok.kind == "word"
            and tok.text in ("AND", "OR")
        ):
            flush_line()
            current_line = " " * indent + tok.text
            prev_token = tok
            prev_sig_token = tok
            i += 1
            continue

        # Comment handling
        if tok.kind == "comment":
            if tok.text.startswith("--"):
                if current_line:
                    current_line += " " + tok.text
                else:
                    current_line = tok.text
                flush_line()
            else:
                # Block comment
                if current_line and not current_line.endswith((" ", "(")):
                    current_line += " " + tok.text
                else:
                    current_line += tok.text
            prev_token = tok
            i += 1
            continue

        # Normal token spacing
        tok_text = tok.text
        space_needed = True
        if (
            not current_line
            or current_line.endswith(("\n", " "))
            or current_line.endswith((" ", "("))
            or (tok.kind == "punct" and tok.text in (",", ")", ";", "."))
            or (
                prev_sig_token
                and prev_sig_token.kind == "punct"
                and prev_sig_token.text in ("(", ".")
            )
            or (tok.kind == "operator" and tok.text == "::")
            or (
                prev_sig_token and prev_sig_token.kind == "operator" and prev_sig_token.text == "::"
            )
        ):
            space_needed = False
        elif (
            tok.kind == "punct"
            and tok.text == "("
            and prev_sig_token
            and prev_sig_token.kind == "word"
        ):
            # None between non-keyword word (or COUNT) and its '(', while others keep space
            is_kw = prev_sig_token.text in KEYWORDS
            space_needed = is_kw and prev_sig_token.text != "COUNT"

        if unary_pending:  # the operand after a unary minus attaches to it
            space_needed = False
            unary_pending = False
        # Unary minus after an operator or '(': the operand attaches to '-' (L38)
        unary_pending = bool(
            tok.kind == "operator"
            and tok.text == "-"
            and prev_sig_token
            and (
                prev_sig_token.kind == "operator"
                or (prev_sig_token.kind == "punct" and prev_sig_token.text == "(")
            )
        )

        if space_needed:
            current_line += " " + tok_text
        else:
            current_line += tok_text

        prev_token = tok
        prev_sig_token = tok
        i += 1

    flush_line()
    return "\n".join(lines)


def lint(sql: str) -> list[Finding]:
    """Lint SQL text for six common anti-patterns.

    L001 select_star: a '*' directly after SELECT or ',' in a select list at depth 0
    L002 update or delete without WHERE at depth 0 of that statement
    L003 implicit_cross_join (a ',' at depth 0 within a FROM clause)
    L004 order_by_ordinal (a number token directly after ORDER BY or a ',' in that clause)
    L005 not_in_subquery (NOT IN followed by '(' SELECT)
    L006 limit_without_order (LIMIT in a statement with no ORDER BY at depth 0)
    """
    tokens = tokenize(sql)
    _check_depth(tokens)

    findings: list[Finding] = []
    statements = _split_statements(tokens)

    for stmt in statements:
        findings.extend(_lint_statement(stmt))

    # Sort findings by line, col, rule
    findings.sort(key=lambda f: (f.line, f.col, f.rule))
    return findings


def _lint_statement(tokens: list[Token]) -> list[Finding]:
    findings: list[Finding] = []

    # Filter to non-whitespace tokens for parsing
    sig_tokens: list[Token] = [t for t in tokens if t.kind != "whitespace"]
    if not sig_tokens:
        return findings

    depth = 0
    current_clause: str | None = None
    has_where_at_depth_0 = False
    has_order_by_at_depth_0 = False
    stmt_type: tuple[str, Token] | None = None  # ('UPDATE'|'DELETE', token)
    limit_token: Token | None = None

    n = len(sig_tokens)
    i = 0
    while i < n:
        tok = sig_tokens[i]

        if tok.kind == "punct" and tok.text == "(":
            depth += 1
            i += 1
            continue
        if tok.kind == "punct" and tok.text == ")":
            if depth > 0:
                depth -= 1
            i += 1
            continue

        if depth == 0:
            clause_info = _match_clause_at(sig_tokens, i)
            if clause_info:
                cname, consumed = clause_info
                current_clause = cname
                if cname == "WHERE":
                    has_where_at_depth_0 = True
                elif cname == "ORDER BY":
                    has_order_by_at_depth_0 = True
                elif cname in ("UPDATE", "DELETE", "DELETE FROM"):
                    if stmt_type is None:
                        stmt_type = ("UPDATE" if cname == "UPDATE" else "DELETE", tok)
                elif cname == "LIMIT" and limit_token is None:
                    limit_token = tok
                i += consumed
                continue

            # L001 select_star: a '*' directly after SELECT or after ',' in a select list at depth 0
            if current_clause == "SELECT" and tok.kind == "operator" and tok.text == "*":
                # check previous sig token in clause
                prev_tok = sig_tokens[i - 1] if i > 0 else None
                if prev_tok and (
                    (prev_tok.kind == "word" and prev_tok.text.upper() in ("SELECT", "DISTINCT"))
                    or (prev_tok.kind == "punct" and prev_tok.text == ",")
                ):
                    findings.append(
                        Finding("L001", tok.line, tok.col, "select_star: avoid SELECT *")
                    )

            # L003 implicit_cross_join: a ',' at depth 0 within a FROM clause
            if current_clause == "FROM" and tok.kind == "punct" and tok.text == ",":
                findings.append(
                    Finding(
                        "L003",
                        tok.line,
                        tok.col,
                        "implicit_cross_join: use explicit JOIN instead of comma",
                    )
                )

            # L004 order_by_ordinal: a number token directly after ORDER BY or a ',' in that clause
            if current_clause == "ORDER BY" and tok.kind == "number":
                prev_tok = sig_tokens[i - 1] if i > 0 else None
                if prev_tok and (
                    (prev_tok.kind == "word" and prev_tok.text.upper() == "BY")
                    or (prev_tok.kind == "punct" and prev_tok.text == ",")
                ):
                    findings.append(
                        Finding(
                            "L004",
                            tok.line,
                            tok.col,
                            "order_by_ordinal: order by column name instead of ordinal number",
                        )
                    )

        # L005 not_in_subquery: NOT IN followed by '(' SELECT (can be at any depth)
        if tok.kind == "word" and tok.text.upper() == "NOT" and i + 3 < n:
            t_in = sig_tokens[i + 1]
            t_paren = sig_tokens[i + 2]
            t_sel = sig_tokens[i + 3]
            if (
                t_in.kind == "word"
                and t_in.text.upper() == "IN"
                and t_paren.kind == "punct"
                and t_paren.text == "("
                and t_sel.kind == "word"
                and t_sel.text.upper() == "SELECT"
            ):
                findings.append(
                    Finding(
                        "L005",
                        tok.line,
                        tok.col,
                        "not_in_subquery: avoid NOT IN with subquery (null handling risk)",
                    )
                )

        i += 1

    # L002 update or delete without WHERE at depth 0
    if stmt_type is not None and not has_where_at_depth_0:
        kind_str, tok = stmt_type
        msg_prefix = "update_without_where" if kind_str == "UPDATE" else "delete_without_where"
        findings.append(Finding("L002", tok.line, tok.col, f"{msg_prefix}: require a WHERE clause"))

    # L006 limit_without_order: LIMIT in a statement with no ORDER BY at depth 0
    if limit_token is not None and not has_order_by_at_depth_0:
        findings.append(
            Finding(
                "L006",
                limit_token.line,
                limit_token.col,
                "limit_without_order: LIMIT without ORDER BY gives non-deterministic results",
            )
        )

    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for format, check, and lint commands."""
    import sys

    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        sys.stderr.write("Usage: sql-format-lint <format|check|lint> <file>\n")
        return 2

    cmd = args[0]
    path = args[1]

    if cmd not in ("format", "check", "lint"):
        sys.stderr.write(f"Unknown command: {cmd}\n")
        return 2

    try:
        with open(path, encoding="utf-8") as file_obj:
            content = file_obj.read()
    except OSError as e:
        sys.stderr.write(f"Error reading {path}: {e}\n")
        return 2

    try:
        if cmd == "format":
            formatted = format_sql(content)
            sys.stdout.write(formatted)
            return 0
        elif cmd == "check":
            formatted = format_sql(content)
            return 0 if formatted == content else 1
        elif cmd == "lint":
            findings = lint(content)
            for finding in findings:
                sys.stdout.write(
                    f"{path}:{finding.line}:{finding.col}: {finding.rule} {finding.message}\n"
                )
            return 1 if findings else 0
    except SqlError as err:
        sys.stderr.write(f"{path}:{err.line}:{err.col}: {err.code}: {err}\n")
        return 2

    return 0
