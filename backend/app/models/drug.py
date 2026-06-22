from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DrugFormulary(Base):
    __tablename__ = "drug_formulary"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    generic_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    drug_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    available_strengths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    dosage_forms: Mapped[list | None] = mapped_column(JSON, nullable=True)
    routes: Mapped[list | None] = mapped_column(JSON, nullable=True, default=lambda: ["oral"])
    contraindications: Mapped[list | None] = mapped_column(JSON, nullable=True)
    common_side_effects: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_controlled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    interactions_as_drug_a: Mapped[list["DrugInteraction"]] = relationship(
        "DrugInteraction", foreign_keys="DrugInteraction.drug_a_id", back_populates="drug_a"
    )
    interactions_as_drug_b: Mapped[list["DrugInteraction"]] = relationship(
        "DrugInteraction", foreign_keys="DrugInteraction.drug_b_id", back_populates="drug_b"
    )


class DrugInteraction(Base):
    __tablename__ = "drug_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    drug_a_id: Mapped[str] = mapped_column(String(36), ForeignKey("drug_formulary.id"), nullable=False)
    drug_b_id: Mapped[str] = mapped_column(String(36), ForeignKey("drug_formulary.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_significance: Mapped[str | None] = mapped_column(Text, nullable=True)

    drug_a: Mapped["DrugFormulary"] = relationship(
        "DrugFormulary", foreign_keys=[drug_a_id], back_populates="interactions_as_drug_a"
    )
    drug_b: Mapped["DrugFormulary"] = relationship(
        "DrugFormulary", foreign_keys=[drug_b_id], back_populates="interactions_as_drug_b"
    )
