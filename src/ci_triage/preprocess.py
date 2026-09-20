"""Truncate GitHub Actions logs before they reach the model.
Prefer the failed step, keep the last 150 lines and error/FAIL hits,
then hard-cap at MAX_CHARS so a raw MB log cannot be sent to Haiku.
"""
from __future__ import annotations
import re

#Constants
MAX_CHARS = 24_000
MAX_LINES = 150
TRUNCATION_MARK = "[truncated]\n"

#Regex to capture relevant parts of git error log
_ERROR_LINE = re.compile(
    r"(error|fail|exception|traceback|killed|oom|##\[error\])",
    re.IGNORECASE,
)
_GROUP_OPEN = re.compile(r"##\[group\]")
_GROUP_CLOSE = re.compile(r"##\[endgroup\]")
_FAILED_STEP_HINT = re.compile(
    r"(##\[error\]|Process completed with exit code [1-9]\d*|exit code 137)",
    re.IGNORECASE,
)

def preprocess_log(raw: str) -> str:
    """Return a failed-step excerpt: last 150 lines, error/FAIL grep, ≤24k chars."""
    step = _failed_step(raw)
    excerpt = _last_lines_with_errors(step)
    return _cap(excerpt, MAX_CHARS)

def _failed_step(raw: str) -> str:
    groups = _github_groups(raw)
    if not groups:
        return raw
    failed = [g for g in groups if _FAILED_STEP_HINT.search(g) or _ERROR_LINE.search(g)]
    return failed[-1] if failed else groups[-1]

def _github_groups(raw: str) -> list[str]:
    if not _GROUP_OPEN.search(raw):
        return []
    parts = _GROUP_OPEN.split(raw)
    groups: list[str] = []
    for part in parts[1:]:
        body = _GROUP_CLOSE.split(part, maxsplit=1)[0] if _GROUP_CLOSE.search(part) else part
        groups.append(body)
    return groups

def _last_lines_with_errors(text: str) -> str:
    lines = text.splitlines()
    last = lines[-MAX_LINES:]
    if not any(_ERROR_LINE.search(line) for line in last):
        extra = [line for line in lines if _ERROR_LINE.search(line)][-50:]
        room = MAX_LINES - len(extra)
        last = extra + last[-room:] if room > 0 else extra[-MAX_LINES:]
    return "\n".join(last)

def _cap(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    keep = max_chars - len(TRUNCATION_MARK)
    if keep <= 0:
        return TRUNCATION_MARK[:max_chars]
    return TRUNCATION_MARK + text[-keep:]

