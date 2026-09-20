from pathlib import Path

from ci_triage.preprocess import MAX_LINES, preprocess_log

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
