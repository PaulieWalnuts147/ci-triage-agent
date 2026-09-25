import pytest
from pydantic import ValidationError

from ci_triage.schema import (
    Classification,
    Evidence,
    EvidenceSource,
    RecommendedAction,
    TriageResult,
)


def _result(**overrides: object) -> TriageResult:
    data: dict[str, object] = {
        "classification": Classification.TEST_BUG,
        "confidence": 0.81,
        "summary": "Assertion failed in test_cart.py",
        "evidence": [
            Evidence(
                source=EvidenceSource.LOG,
                excerpt="AssertionError: assert Decimal('11.00') == Decimal('12.10')",
                pointer="tests/test_cart.py:41",
            )
        ],
        "recommended_action": RecommendedAction.FIX_CODE,
        "cited_log_line": "E       AssertionError: assert Decimal('11.00') == Decimal('12.10')",
    }
    data.update(overrides)
    return TriageResult.model_validate(data)


def test_valid_result() -> None:
    result = _result()
    assert result.classification is Classification.TEST_BUG
    assert result.cited_log_line is not None


def test_unknown_may_omit_cited_log_line() -> None:
    result = _result(
        classification=Classification.UNKNOWN,
        recommended_action=RecommendedAction.NEEDS_HUMAN,
        cited_log_line=None,
        summary="Not enough signal",
    )
    assert result.cited_log_line is None


def test_non_unknown_requires_cited_log_line() -> None:
    with pytest.raises(ValidationError):
        _result(classification=Classification.INFRA, cited_log_line=None)


def test_summary_cannot_exceed_280_chars() -> None:
    with pytest.raises(ValidationError):
        _result(summary="x" * 281)


def test_rejects_unknown_classification_string() -> None:
    with pytest.raises(ValidationError):
        _result(classification="network")
