"""Contract for a triage result.

Haiku must return JSON that matches these types. Lambda validates it and
posts the GitHub comment; the model cannot post directly. Invalid shapes
(including a real classification with no cited log line) are rejected.
"""

from enum import StrEnum
from pydantic import BaseModel, Field, model_validator

class Classification(StrEnum):
    FLAKE = "flake"
    PRODUCT_REGRESSION = "product_regression"
    INFRA = "infra"
    TEST_BUG = "test_bug"
    UNKNOWN = "unknown"

class EvidenceSource(StrEnum):
    LOG = "log"
    JUNIT = "junit"
    COMMIT = "commit"

class RecommendedAction(StrEnum):
    FIX_CODE = "fix_code"
    FIX_TEST = "fix_test"
    RETRY_LATER = "retry_later"
    NEEDS_HUMAN = "needs_human"

class Evidence(BaseModel):
    source: EvidenceSource
    excerpt: str
    pointer: str

class TriageResult(BaseModel):
    classification: Classification
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(max_length=280)
    evidence: list[Evidence]
    recommended_action: RecommendedAction
    cited_log_line: str | None = None

    @model_validator(mode="after")
    def cited_log_line_required_unless_unknown(self) -> "TriageResult":
        if self.classification is not Classification.UNKNOWN and not self.cited_log_line:
                    raise ValueError("cited_log_line is required unless classification is unknown")
        return self