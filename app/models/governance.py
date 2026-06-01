from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GovernanceRule(Base):
    __tablename__ = "governance_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_config: Mapped[str | None] = mapped_column(JSON)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )


class GovernanceLog(Base):
    __tablename__ = "governance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("governance_rules.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    before_value: Mapped[str | None] = mapped_column(JSON)
    after_value: Mapped[str | None] = mapped_column(JSON)
    executed_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )


class DataLineage(Base):
    __tablename__ = "data_lineage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    transform_step: Mapped[str] = mapped_column(String(200), nullable=False)
    executed_at: Mapped[str] = mapped_column(
        DateTime, server_default=func.now()
    )
