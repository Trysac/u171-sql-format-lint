"""Comprehensive test suite for sql_format_lint."""

from __future__ import annotations

from pathlib import Path

import pytest

from sql_format_lint import (
    Finding,
    SqlError,
    format_sql,
    lint,
    main,
    tokenize,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_acceptance_1() -> None:
    sql = "select a,b from t where x=1 and y=2"
    expected = "SELECT\n  a,\n  b\nFROM t\nWHERE x = 1\n  AND y = 2\n"
    assert format_sql(sql) == expected


def test_acceptance_2() -> None:
    sql1 = "select 'it''s' as s, \"Mixed Col\" from t"
    expected1 = "SELECT\n  'it''s' AS s,\n  \"Mixed Col\"\nFROM t\n"
    assert format_sql(sql1) == expected1

    sql2 = "select * from a left join b on a.id=b.id"
    expected2 = "SELECT *\nFROM a\nLEFT JOIN b ON a.id = b.id\n"
    assert format_sql(sql2) == expected2


def test_acceptance_3() -> None:
    assert format_sql("select 1 -- one\n") == "SELECT 1 -- one\n"
    assert format_sql("select 1; select 2") == "SELECT 1;\n\nSELECT 2\n"
    dollar_sql = "select $$a;b$$"
    formatted = format_sql(dollar_sql)
    assert "$$a;b$$" in formatted
    assert format_sql(formatted) == formatted


def test_acceptance_4_fixtures_idempotent() -> None:
    fixture_files = sorted(FIXTURES_DIR.glob("*.sql"))
    assert len(fixture_files) >= 8

    for fpath in fixture_files:
        content = fpath.read_text(encoding="utf-8")
        formatted_once = format_sql(content)
        formatted_twice = format_sql(formatted_once)
        assert formatted_twice == formatted_once, f"Idempotence failed on {fpath.name}"

        # Verify significant tokens are preserved
        orig_tokens = [t for t in tokenize(content) if t.kind not in ("whitespace", "comment")]
        out_tokens = [
            t for t in tokenize(formatted_once) if t.kind not in ("whitespace", "comment")
        ]

        assert len(orig_tokens) == len(out_tokens), f"Token count mismatch on {fpath.name}"
        for ot, nt in zip(orig_tokens, out_tokens, strict=True):
            assert ot.kind == nt.kind
            if ot.kind == "word":
                assert ot.text.upper() == nt.text.upper()
            else:
                assert ot.text == nt.text


def test_acceptance_5_lint() -> None:
    assert lint("SELECT * FROM t") == [Finding("L001", 1, 8, "select_star: avoid SELECT *")]
    assert lint("SELECT count(*) FROM t") == []

    findings_del = lint("DELETE FROM t")
    assert len(findings_del) == 1
    assert findings_del[0].rule == "L002"
    assert findings_del[0].line == 1
    assert findings_del[0].col == 1
    assert "delete_without_where:" in findings_del[0].message

    assert lint("UPDATE t SET a = 1 WHERE id = 2") == []


def test_acceptance_6_lint_rules() -> None:
    l3 = lint("SELECT a FROM t, u")
    assert any(f.rule == "L003" for f in l3)

    l4 = lint("SELECT a FROM t ORDER BY 1")
    assert any(f.rule == "L004" for f in l4)

    l5 = lint("SELECT a FROM t WHERE id NOT IN (SELECT id FROM u)")
    assert any(f.rule == "L005" for f in l5)

    l6 = lint("SELECT a FROM t LIMIT 10")
    assert any(f.rule == "L006" for f in l6)


def test_acceptance_7_sql_error() -> None:
    with pytest.raises(SqlError) as exc_info:
        tokenize("select 'abc")
    err = exc_info.value
    assert err.code == "unterminated_string"
    assert err.line == 1
    assert err.col == 8

    with pytest.raises(SqlError) as exc_info2:
        tokenize("/* x")
    assert exc_info2.value.code == "unterminated_comment"

    with pytest.raises(SqlError) as exc_info3:
        tokenize("a" * 1_000_001)
    assert exc_info3.value.code == "input_too_large"

    with pytest.raises(SqlError) as exc_info4:
        format_sql("(" * 101)
    assert exc_info4.value.code == "too_deep"


def test_acceptance_8_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    q_path = tmp_path / "q.sql"
    unformatted = "select * from t"
    q_path.write_text(unformatted, encoding="utf-8")

    # check unformatted returns 1
    assert main(["check", str(q_path)]) == 1

    # lint prints finding and returns 1
    ret = main(["lint", str(q_path)])
    captured = capsys.readouterr()
    assert ret == 1
    assert f"{q_path}:1:8: L001 select_star: avoid SELECT *\n" == captured.out

    # with a relative path the output is exactly the documented line
    monkeypatch.chdir(tmp_path)
    assert main(["lint", "q.sql"]) == 1
    assert capsys.readouterr().out == "q.sql:1:8: L001 select_star: avoid SELECT *\n"

    # format prints formatted SQL
    capsys.readouterr()
    ret_fmt = main(["format", str(q_path)])
    captured_fmt = capsys.readouterr()
    assert ret_fmt == 0
    assert captured_fmt.out == "SELECT *\nFROM t\n"

    # format the file on disk
    q_path.write_text(captured_fmt.out, encoding="utf-8")
    assert main(["check", str(q_path)]) == 0

    # missing file returns 2
    capsys.readouterr()
    assert main(["check", str(tmp_path / "missing.sql")]) == 2


def test_additional_tokenizer_branches() -> None:
    # unterminated quoted ident
    with pytest.raises(SqlError) as exc:
        tokenize('select "unfinished')
    assert exc.value.code == "unterminated_quoted_ident"

    # unterminated dollar
    with pytest.raises(SqlError) as exc:
        tokenize("select $tag$body")
    assert exc.value.code == "unterminated_dollar"

    # dollar with invalid tag
    tokens = tokenize("$123$")
    assert tokens[0].kind == "operator"

    # numbers: floats and scientific notation
    toks = tokenize("123 45.67 1e10 2.5E-3 100.")
    numbers = [t.text for t in toks if t.kind == "number"]
    assert "123" in numbers
    assert "45.67" in numbers
    assert "1e10" in numbers
    assert "2.5E-3" in numbers

    # Operators
    op_toks = tokenize("a::text <> b <= c >= d != e || f")
    ops = [t.text for t in op_toks if t.kind == "operator"]
    assert "::" in ops
    assert "<>" in ops
    assert "<=" in ops
    assert ">=" in ops
    assert "!=" in ops
    assert "||" in ops

    # Unary minus and negative numbers
    assert format_sql("SELECT -1") == "SELECT - 1\n"  # unary only after an operator or "("
    assert format_sql("SELECT x * -1") == "SELECT x * -1\n"
    assert format_sql("SELECT (-1)") == "SELECT (-1)\n"


def test_additional_lint_cases() -> None:
    # update without where
    findings = lint("UPDATE users SET name = 'Alice'")
    assert any(f.rule == "L002" and "update_without_where" in f.message for f in findings)

    # select star after comma
    findings = lint("SELECT id, * FROM users")
    assert any(f.rule == "L001" for f in findings)

    # order by ordinal after comma
    findings = lint("SELECT id, name FROM users ORDER BY name, 2")
    assert any(f.rule == "L004" for f in findings)

    # limit with order by is fine
    findings = lint("SELECT id FROM users ORDER BY id LIMIT 5")
    assert not any(f.rule == "L006" for f in findings)


def test_empty_sql_and_whitespace() -> None:
    assert format_sql("") == ""
    assert format_sql("   \n  ") == ""
    assert lint("") == []


def test_cli_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # insufficient args
    assert main([]) == 2
    # unknown command
    assert main(["unknown", "file.sql"]) == 2

    # sql error during format
    bad_sql = tmp_path / "bad.sql"
    bad_sql.write_text("select 'unterminated", encoding="utf-8")
    assert main(["format", str(bad_sql)]) == 2
