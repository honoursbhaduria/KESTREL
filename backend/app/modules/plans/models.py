"""SQLAlchemy models for Plans, Versioning, and Compliance Reviews (Phase 3)."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, TenantBaseModel


class Plan(TenantBaseModel):
    """Architectural plan record belonging to a project and tenant organization."""

    __tablename__ = "plans"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    versions: Mapped[list["PlanVersion"]] = relationship(
        "PlanVersion",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanVersion.version",
    )
    reviews: Mapped[list["PlanReview"]] = relationship(
        "PlanReview",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanReview.version",
    )


class PlanVersion(BaseModel):
    """Immutable version snapshot storing full PlanData JSON."""

    __tablename__ = "plan_versions"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(50), default="user", nullable=False
    )  # user | ai | solver
    message: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    plan: Mapped["Plan"] = relationship("Plan", back_populates="versions")


class PlanReview(BaseModel):
    """Archived review results for a specific plan version."""

    __tablename__ = "plan_reviews"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    plan: Mapped["Plan"] = relationship("Plan", back_populates="reviews")
