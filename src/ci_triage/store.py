"""Local stand-in for GitHub: resolve a run_id to a folder of fixture files.

Week 2 tools and the local CLI read runs from disk (e.g. tests/fixtures/runs/<id>/)
so tests never hit the network. This class is the adapter, not the product.

When Lambda talks to the real GitHub API, replace FixtureStore with a live
client. Keep get_workflow_run / get_failed_job_log / etc.; delete or stop
using this module in production.
"""

from __future__ import annotations

import re
from pathlib import Path

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_-]+$")


class FixtureStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
    
    def run_dir(self, run_id: str) -> Path:
        if not _SAFE_RUN_ID.fullmatch(run_id):
            raise ValueError(f"invalid run_id: {run_id!r}")
        path = (self.root / run_id).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"invalid run_id: {run_id!r}")
        if not path.is_dir():
            raise FileNotFoundError(f"unknown run_id: {run_id}")
        return path