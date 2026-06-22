"""Drug interaction and allergy checking service."""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.models.drug import DrugFormulary, DrugInteraction
from typing import List


async def check_interactions(
    db: AsyncSession,
    drug_ids: List[str],
    patient_allergies: List[str] | None = None,
    drug_names: List[str] | None = None,
) -> List[dict]:
    """Check drug-drug interactions and allergy conflicts."""
    warnings = []

    # Drug-drug interaction checks
    if len(drug_ids) >= 2:
        for i in range(len(drug_ids)):
            for j in range(i + 1, len(drug_ids)):
                result = await db.execute(
                    select(DrugInteraction).where(
                        or_(
                            and_(
                                DrugInteraction.drug_a_id == drug_ids[i],
                                DrugInteraction.drug_b_id == drug_ids[j],
                            ),
                            and_(
                                DrugInteraction.drug_a_id == drug_ids[j],
                                DrugInteraction.drug_b_id == drug_ids[i],
                            ),
                        )
                    )
                )
                interactions = result.scalars().all()
                for interaction in interactions:
                    # Get drug names
                    drug_a = await db.get(DrugFormulary, interaction.drug_a_id)
                    drug_b = await db.get(DrugFormulary, interaction.drug_b_id)
                    warnings.append({
                        "type": "drug_interaction",
                        "severity": interaction.severity,
                        "drug_a": drug_a.name if drug_a else "Unknown",
                        "drug_b": drug_b.name if drug_b else "Unknown",
                        "description": interaction.description,
                        "clinical_significance": interaction.clinical_significance,
                    })

    # Allergy checks
    if patient_allergies and drug_names:
        for allergy in patient_allergies:
            allergy_lower = allergy.lower()
            for drug_name in drug_names:
                # Simple name-based allergy check
                if allergy_lower in drug_name.lower():
                    warnings.append({
                        "type": "allergy_alert",
                        "severity": "high",
                        "drug": drug_name,
                        "allergen": allergy,
                        "description": f"Patient has a recorded allergy to {allergy}. {drug_name} may cross-react.",
                    })
                # Check class-level (penicillin -> amoxicillin)
                if allergy_lower == "penicillin" and any(
                    term in drug_name.lower() for term in ["amoxicillin", "ampicillin", "oxacillin"]
                ):
                    warnings.append({
                        "type": "allergy_alert",
                        "severity": "high",
                        "drug": drug_name,
                        "allergen": allergy,
                        "description": f"Patient has penicillin allergy. {drug_name} is a penicillin-class antibiotic.",
                    })

    return warnings


async def search_drugs(db: AsyncSession, query: str, limit: int = 20) -> List[DrugFormulary]:
    """Search drug formulary by name."""
    result = await db.execute(
        select(DrugFormulary)
        .where(
            and_(
                DrugFormulary.is_active == True,
                or_(
                    DrugFormulary.name.ilike(f"%{query}%"),
                    DrugFormulary.generic_name.ilike(f"%{query}%"),
                ),
            )
        )
        .limit(limit)
    )
    return result.scalars().all()
