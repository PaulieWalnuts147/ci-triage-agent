"""Tools the model may call. Backed by fixture files, not live GitHub yet."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from ci_triage.preprocess import MAX_CHARS, preprocess_log
from ci_triage.store import FixtureStore


@dataclass(frozen=True)
class Job:
    name: str
    conclusion: str


@dataclass(frozen=True)
class WorkflowRun:
    name: str
    sha: str
    branch: str
    conclusion: str
    jobs: list[Job]


@dataclass(frozen=True)
class FailedTest:
    name: str
    file: str
    message: str


@dataclass(frozen=True)
class JunitSummary:
    failed: list[FailedTest]
    reason: str | None = None


def get_failed_job_log(store: FixtureStore, run_id: str) -> str:
    raw = (store.run_dir(run_id) / "job.log").read_text()
    excerpt = preprocess_log(raw)
    if len(excerpt) > MAX_CHARS:
        raise RuntimeError("preprocess_log exceeded MAX_CHARS")
    return excerpt


def get_workflow_run(store: FixtureStore, run_id: str) -> WorkflowRun:
    data = json.loads((store.run_dir(run_id) / "run.json").read_text())
    jobs = [Job(name=j["name"], conclusion=j["conclusion"]) for j in data["jobs"]]
    return WorkflowRun(
        name=data["name"],
        sha=data["sha"],
        branch=data["branch"],
        conclusion=data["conclusion"],
        jobs=jobs,
    )


def get_junit_summary(store: FixtureStore, run_id: str) -> JunitSummary:
    path = store.run_dir(run_id) / "junit.xml"
    if not path.is_file():
        return JunitSummary(failed=[], reason="no JUnit artifact")
    return _parse_junit(path.read_text())


def get_commit_files(store: FixtureStore, run_id: str) -> list[str]:
    paths = json.loads((store.run_dir(run_id) / "commit_files.json").read_text())
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise ValueError("commit_files.json must be a list of paths")
    return list(paths)


def _parse_junit(xml_text: str) -> JunitSummary:
    root = ET.fromstring(xml_text)
    failed: list[FailedTest] = []
    for case in root.findall(".//testcase"):
        failure = case.find("failure")
        if failure is None:
            failure = case.find("error")
        if failure is None:
            continue
        failed.append(
            FailedTest(
                name=case.get("name") or "",
                file=case.get("classname") or "",
                message=failure.get("message") or (failure.text or "").strip(),
            )
        )
    if not failed:
        return JunitSummary(failed=[], reason="JUnit present but no failed tests")
    return JunitSummary(failed=failed, reason=None)
