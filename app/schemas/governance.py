from datetime import datetime

from pydantic import BaseModel, Field


class GovernanceRuleCreate(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=200)
    rule_type: str = Field(..., pattern=r"^(format_check|dedup|desensitize|clean|quality)$")
    rule_config: dict | None = None
    phase: str = Field(..., min_length=1, max_length=50)
    is_active: bool = True


class GovernanceRuleResponse(BaseModel):
    id: int
    rule_name: str
    rule_type: str
    rule_config: dict | None
    phase: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class QualityReportResponse(BaseModel):
    total_records: int
    completeness_rate: float
    dedup_rate: float
    anomaly_rate: float
    timeliness_score: float
    overall_score: float
    generated_at: datetime | None = None


class LineageResponse(BaseModel):
    id: int
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    transform_step: str
    executed_at: datetime

    model_config = {"from_attributes": True}


class LogResponse(BaseModel):
    id: int
    target_type: str
    target_id: int
    rule_id: int | None
    action: str
    before_value: dict | None
    after_value: dict | None
    executed_at: datetime

    model_config = {"from_attributes": True}
