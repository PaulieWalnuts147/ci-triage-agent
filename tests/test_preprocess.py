from pathlib import Path

from ci_triage.preprocess import MAX_CHARS, MAX_LINES, preprocess_log

FIXTURES = Path(__file__).parent / "fixtures"


def _read_log(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_flake_log_keeps_timeout_signal() -> None:
    out = preprocess_log(_read_log("flake.log"))
    assert "socket hang up" in out
    assert "Timeout - Async callback" in out
    assert "Set up job" not in out


def test_error_above_the_last_lines_is_still_kept() -> None:
    out = preprocess_log(_read_log("error_above_last_lines.log"))
    assert "ERROR boom at the start" in out
    assert len(out.splitlines()) <= MAX_LINES


def test_exception_is_recognised() -> None:
    out = preprocess_log(_read_log("exception.log"))
    assert "SOME EXCEPTION, CAUSED THIS PIPELINE TO FAIL" in out
    assert len(out.splitlines()) <= MAX_LINES


def test_excerpt_never_exceeds_char_cap() -> None:
    out = preprocess_log(_read_log("over_char_cap.log"))
    assert len(out) <= MAX_CHARS
    assert "FAIL boom at the end" in out
    assert out.startswith("[truncated]")


def test_pytest_assertion_keeps_failing_line() -> None:
    out = preprocess_log(_read_log("pytest_assert.log"))
    assert "AssertionError: assert Decimal('11.00')" in out
    assert "tests/test_cart.py:41" in out
    assert "Successfully installed pytest" not in out


def test_npm_503_keeps_registry_error() -> None:
    out = preprocess_log(_read_log("npm_503.log"))
    assert "503" in out
    assert "registry.npmjs.org" in out
    assert "Set up job" not in out


def test_oom_keeps_killed_and_137() -> None:
    out = preprocess_log(_read_log("oom.log"))
    assert "Killed" in out
    assert "exit code 137" in out
    assert "eslint passed" not in out
