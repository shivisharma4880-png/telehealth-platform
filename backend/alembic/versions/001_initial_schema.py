"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("phone", sa.String(20), unique=True, nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("role", sa.Enum("patient", "clinician", "admin", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("totp_secret", sa.String(32), nullable=True),
        sa.Column("totp_enabled", sa.Boolean, default=False),
        sa.Column("otp_code", sa.String(6), nullable=True),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_phone", "users", ["phone"])

    # organizations
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("branding_color", sa.String(7), nullable=True),
        sa.Column("registration_number", sa.String(100), nullable=True),
        sa.Column("settings", sa.JSON, nullable=True),
        sa.Column("cancellation_policy_hours", sa.Integer, default=24),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # practitioners
    op.create_table(
        "practitioners",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("registration_number", sa.String(100), nullable=False, unique=True),
        sa.Column("specialty", sa.Enum(
            "general_practice", "dermatology", "mental_health", "pediatrics",
            "cardiology", "orthopedics", "other", name="specialty"
        ), nullable=False),
        sa.Column("languages", sa.JSON, nullable=False),
        sa.Column("consultation_fee", sa.Numeric(10, 2), default=0.0),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("years_of_experience", sa.Integer, default=0),
        sa.Column("practice_address", sa.Text, nullable=True),
        sa.Column("digital_signature_text", sa.String(500), nullable=True),
        sa.Column("slot_duration_minutes", sa.Integer, default=15),
        sa.Column("buffer_minutes", sa.Integer, default=5),
        sa.Column("is_available", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # patients
    op.create_table(
        "patients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("gender", sa.Enum("male", "female", "other", "prefer_not_to_say", name="gender"), nullable=True),
        sa.Column("abha_id", sa.String(50), nullable=True),
        sa.Column("preferred_language", sa.String(10), default="en"),
        sa.Column("allergies", sa.JSON, nullable=True),
        sa.Column("medical_history", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_patients_abha_id", "patients", ["abha_id"])

    # dependents
    op.create_table(
        "dependents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("gender", sa.Enum("male", "female", "other", "prefer_not_to_say", name="gender"), nullable=True),
        sa.Column("relationship_to_patient", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # slots
    op.create_table(
        "slots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("practitioner_id", sa.String(36), sa.ForeignKey("practitioners.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("available", "booked", "blocked", name="slotstatus"), default="available"),
        sa.Column("is_blocked", sa.Boolean, default=False),
        sa.Column("block_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # appointments
    op.create_table(
        "appointments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("practitioner_id", sa.String(36), sa.ForeignKey("practitioners.id"), nullable=False),
        sa.Column("slot_id", sa.String(36), sa.ForeignKey("slots.id"), unique=True, nullable=False),
        sa.Column("dependent_id", sa.String(36), sa.ForeignKey("dependents.id"), nullable=True),
        sa.Column("status", sa.Enum(
            "booked", "confirmed", "in_progress", "completed", "no_show", "cancelled", "rescheduled",
            name="appointmentstatus"
        ), default="booked"),
        sa.Column("chief_complaint", sa.Text, nullable=True),
        sa.Column("questionnaire_answers", sa.JSON, nullable=True),
        sa.Column("payment_status", sa.Enum("pending", "paid", "refunded", "failed", name="paymentstatus"), default="pending"),
        sa.Column("payment_reference", sa.String(100), nullable=True),
        sa.Column("amount_paid", sa.Numeric(10, 2), default=0.0),
        sa.Column("cancellation_reason", sa.String(500), nullable=True),
        sa.Column("reminder_sent", sa.Boolean, default=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # questionnaire_templates
    op.create_table(
        "questionnaire_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("specialty", sa.String(50), nullable=False),
        sa.Column("questions", sa.JSON, nullable=False),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # encounters
    op.create_table(
        "encounters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("appointment_id", sa.String(36), sa.ForeignKey("appointments.id"), unique=True, nullable=False),
        sa.Column("practitioner_id", sa.String(36), sa.ForeignKey("practitioners.id"), nullable=False),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("status", sa.Enum("scheduled", "in_progress", "completed", "cancelled", name="encounterstatus"), default="scheduled"),
        sa.Column("livekit_room_name", sa.String(100), nullable=True, unique=True),
        sa.Column("call_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("call_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer, nullable=True),
        sa.Column("call_quality_metrics", sa.JSON, nullable=True),
        sa.Column("full_transcript", sa.Text, nullable=True),
        sa.Column("transcription_enabled", sa.Boolean, default=True),
        sa.Column("soap_note_status", sa.Enum("draft", "final", name="notestatus"), default="draft"),
        sa.Column("soap_subjective", sa.Text, nullable=True),
        sa.Column("soap_objective", sa.Text, nullable=True),
        sa.Column("soap_assessment", sa.Text, nullable=True),
        sa.Column("soap_plan", sa.Text, nullable=True),
        sa.Column("soap_generated_count", sa.Integer, default=0),
        sa.Column("soap_finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("diagnosis_codes", sa.JSON, nullable=True),
        sa.Column("investigations", sa.Text, nullable=True),
        sa.Column("follow_up_notes", sa.Text, nullable=True),
        sa.Column("vitals", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # transcript_segments
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("encounter_id", sa.String(36), sa.ForeignKey("encounters.id"), nullable=False),
        sa.Column("speaker", sa.String(50), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("start_offset_seconds", sa.Numeric(10, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # drug_formulary
    op.create_table(
        "drug_formulary",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("generic_name", sa.String(255), nullable=True),
        sa.Column("brand_names", sa.JSON, nullable=True),
        sa.Column("drug_class", sa.String(100), nullable=True),
        sa.Column("available_strengths", sa.JSON, nullable=True),
        sa.Column("dosage_forms", sa.JSON, nullable=True),
        sa.Column("routes", sa.JSON, nullable=True),
        sa.Column("contraindications", sa.JSON, nullable=True),
        sa.Column("common_side_effects", sa.JSON, nullable=True),
        sa.Column("is_controlled", sa.Boolean, default=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_drug_formulary_name", "drug_formulary", ["name"])

    # drug_interactions
    op.create_table(
        "drug_interactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("drug_a_id", sa.String(36), sa.ForeignKey("drug_formulary.id"), nullable=False),
        sa.Column("drug_b_id", sa.String(36), sa.ForeignKey("drug_formulary.id"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("clinical_significance", sa.Text, nullable=True),
    )

    # prescriptions
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("encounter_id", sa.String(36), sa.ForeignKey("encounters.id"), nullable=False),
        sa.Column("practitioner_id", sa.String(36), sa.ForeignKey("practitioners.id"), nullable=False),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("status", sa.String(20), default="draft"),
        sa.Column("diagnosis", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_signed", sa.Boolean, default=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("pdf_token", sa.String(64), nullable=True),
        sa.Column("pdf_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prescriptions_pdf_token", "prescriptions", ["pdf_token"])

    # medication_requests
    op.create_table(
        "medication_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("prescription_id", sa.String(36), sa.ForeignKey("prescriptions.id"), nullable=False),
        sa.Column("drug_id", sa.String(36), sa.ForeignKey("drug_formulary.id"), nullable=True),
        sa.Column("drug_name", sa.String(255), nullable=False),
        sa.Column("strength", sa.String(100), nullable=True),
        sa.Column("dosage_form", sa.String(100), nullable=True),
        sa.Column("route", sa.String(50), default="oral"),
        sa.Column("frequency", sa.String(100), nullable=False),
        sa.Column("duration", sa.String(100), nullable=True),
        sa.Column("quantity", sa.String(100), nullable=True),
        sa.Column("instructions", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("active", "completed", "stopped", name="medicationstatus"), default="active"),
        sa.Column("interaction_warnings", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # consent_versions
    op.create_table(
        "consent_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("consent_type", sa.String(50), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # consents
    op.create_table(
        "consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("consent_versions.id"), nullable=False),
        sa.Column("accepted", sa.Boolean, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
    )

    # audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("consents")
    op.drop_table("consent_versions")
    op.drop_table("medication_requests")
    op.drop_table("prescriptions")
    op.drop_table("drug_interactions")
    op.drop_table("drug_formulary")
    op.drop_table("transcript_segments")
    op.drop_table("encounters")
    op.drop_table("questionnaire_templates")
    op.drop_table("appointments")
    op.drop_table("slots")
    op.drop_table("dependents")
    op.drop_table("patients")
    op.drop_table("practitioners")
    op.drop_table("organizations")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS specialty")
    op.execute("DROP TYPE IF EXISTS gender")
    op.execute("DROP TYPE IF EXISTS slotstatus")
    op.execute("DROP TYPE IF EXISTS appointmentstatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS encounterstatus")
    op.execute("DROP TYPE IF EXISTS notestatus")
    op.execute("DROP TYPE IF EXISTS medicationstatus")
