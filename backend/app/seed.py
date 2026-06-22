"""Seed database with initial data for development."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta, time
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.practitioner import Practitioner, Specialty
from app.models.patient import Patient, Gender
from app.models.slot import Slot, SlotStatus
from app.models.drug import DrugFormulary, DrugInteraction
from app.models.consent import ConsentVersion
from app.models.appointment import QuestionnaireAnswer


async def seed():
    async with AsyncSessionLocal() as db:
        # Organization
        org = Organization(
            id=str(uuid.uuid4()),
            name="MediCare Digital Clinic",
            slug="medicare-digital",
            address="123 Health Street, Bangalore, Karnataka 560001",
            phone="+91-80-12345678",
            email="admin@medicare-digital.com",
            branding_color="#0ea5e9",
            registration_number="KAR-MED-2024-001",
            settings={"consultation_types": ["video", "audio"], "max_daily_slots": 20},
            cancellation_policy_hours=24,
        )
        db.add(org)
        await db.flush()

        # Admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            email="admin@clinic.com",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin_user)

        # Clinician users
        dr_patel_user = User(
            id=str(uuid.uuid4()),
            email="dr.patel@clinic.com",
            hashed_password=hash_password("doctor123"),
            role=UserRole.CLINICIAN,
            is_active=True,
            is_verified=True,
        )
        db.add(dr_patel_user)

        dr_sharma_user = User(
            id=str(uuid.uuid4()),
            email="dr.sharma@clinic.com",
            hashed_password=hash_password("doctor123"),
            role=UserRole.CLINICIAN,
            is_active=True,
            is_verified=True,
        )
        db.add(dr_sharma_user)

        dr_mehta_user = User(
            id=str(uuid.uuid4()),
            email="dr.mehta@clinic.com",
            hashed_password=hash_password("doctor123"),
            role=UserRole.CLINICIAN,
            is_active=True,
            is_verified=True,
        )
        db.add(dr_mehta_user)

        await db.flush()

        # Practitioners
        dr_patel = Practitioner(
            id=str(uuid.uuid4()),
            user_id=dr_patel_user.id,
            organization_id=org.id,
            first_name="Rajesh",
            last_name="Patel",
            registration_number="MCI-2015-98765",
            specialty=Specialty.GENERAL_PRACTICE,
            languages=["en", "hi", "gu"],
            consultation_fee=500.0,
            bio="MBBS, MD - 10 years experience in general medicine",
            years_of_experience=10,
            practice_address="123 Health Street, Bangalore",
            slot_duration_minutes=15,
            buffer_minutes=5,
        )
        db.add(dr_patel)

        dr_sharma = Practitioner(
            id=str(uuid.uuid4()),
            user_id=dr_sharma_user.id,
            organization_id=org.id,
            first_name="Priya",
            last_name="Sharma",
            registration_number="MCI-2018-54321",
            specialty=Specialty.DERMATOLOGY,
            languages=["en", "hi"],
            consultation_fee=800.0,
            bio="MBBS, MD Dermatology - Specialist in skin conditions and cosmetic dermatology",
            years_of_experience=6,
            slot_duration_minutes=20,
            buffer_minutes=5,
        )
        db.add(dr_sharma)

        dr_mehta = Practitioner(
            id=str(uuid.uuid4()),
            user_id=dr_mehta_user.id,
            organization_id=org.id,
            first_name="Arjun",
            last_name="Mehta",
            registration_number="MCI-2016-11111",
            specialty=Specialty.MENTAL_HEALTH,
            languages=["en", "hi", "mr"],
            consultation_fee=1200.0,
            bio="MBBS, MD Psychiatry - Specializing in anxiety, depression, and stress management",
            years_of_experience=8,
            slot_duration_minutes=30,
            buffer_minutes=10,
        )
        db.add(dr_mehta)

        await db.flush()

        # Patient user
        patient_user = User(
            id=str(uuid.uuid4()),
            phone="+919876543210",
            hashed_password=hash_password("patient123"),
            role=UserRole.PATIENT,
            is_active=True,
            is_verified=True,
        )
        db.add(patient_user)
        await db.flush()

        patient = Patient(
            id=str(uuid.uuid4()),
            user_id=patient_user.id,
            first_name="Amit",
            last_name="Kumar",
            date_of_birth=datetime(1990, 5, 15).date(),
            gender=Gender.MALE,
            preferred_language="en",
            allergies=["penicillin"],
            medical_history="Mild hypertension since 2022",
        )
        db.add(patient)

        # Generate slots for the next ~90 days (UTC clinic grid; Sundays skipped)
        today = datetime.now(timezone.utc).date()
        for day_offset in range(90):
            d = today + timedelta(days=day_offset + 1)
            if d.weekday() >= 6:  # Skip Sundays
                continue
            day = datetime.combine(d, time(9, 0), tzinfo=timezone.utc)
            for hour in range(9, 17):
                for minute in [0, 15, 30, 45]:
                    slot_start = day.replace(hour=hour, minute=minute)
                    slot_end = slot_start + timedelta(minutes=15)
                    slot = Slot(
                        id=str(uuid.uuid4()),
                        practitioner_id=dr_patel.id,
                        start_time=slot_start,
                        end_time=slot_end,
                        status=SlotStatus.AVAILABLE,
                    )
                    db.add(slot)

            for hour in range(10, 16):
                for minute in [0, 20, 40]:
                    slot_start = day.replace(hour=hour, minute=minute)
                    slot_end = slot_start + timedelta(minutes=20)
                    slot = Slot(
                        id=str(uuid.uuid4()),
                        practitioner_id=dr_sharma.id,
                        start_time=slot_start,
                        end_time=slot_end,
                        status=SlotStatus.AVAILABLE,
                    )
                    db.add(slot)

            for hour in range(10, 17):
                for minute in [0, 30]:
                    slot_start = day.replace(hour=hour, minute=minute)
                    slot_end = slot_start + timedelta(minutes=30)
                    if slot_end > day.replace(hour=17, minute=0):
                        continue
                    slot = Slot(
                        id=str(uuid.uuid4()),
                        practitioner_id=dr_mehta.id,
                        start_time=slot_start,
                        end_time=slot_end,
                        status=SlotStatus.AVAILABLE,
                    )
                    db.add(slot)

        # Drug formulary seed data
        drugs = [
            DrugFormulary(
                id=str(uuid.uuid4()),
                name="Paracetamol",
                generic_name="Acetaminophen",
                brand_names=["Crocin", "Dolo", "Tylenol"],
                drug_class="Analgesic/Antipyretic",
                available_strengths=["500mg", "650mg", "1000mg"],
                dosage_forms=["tablet", "syrup", "injection"],
                routes=["oral", "rectal", "IV"],
                contraindications=["liver failure"],
                common_side_effects=["nausea", "rare liver toxicity in overdose"],
                is_controlled=False,
            ),
            DrugFormulary(
                id=str(uuid.uuid4()),
                name="Amoxicillin",
                generic_name="Amoxicillin",
                brand_names=["Mox", "Amoxil"],
                drug_class="Penicillin Antibiotic",
                available_strengths=["250mg", "500mg"],
                dosage_forms=["capsule", "tablet", "suspension"],
                routes=["oral"],
                contraindications=["penicillin allergy"],
                common_side_effects=["diarrhea", "rash", "nausea"],
                is_controlled=False,
            ),
            DrugFormulary(
                id=str(uuid.uuid4()),
                name="Metformin",
                generic_name="Metformin Hydrochloride",
                brand_names=["Glycomet", "Glucophage"],
                drug_class="Biguanide Antidiabetic",
                available_strengths=["500mg", "850mg", "1000mg"],
                dosage_forms=["tablet", "extended-release tablet"],
                routes=["oral"],
                contraindications=["renal impairment", "hepatic impairment", "contrast dye use"],
                common_side_effects=["nausea", "diarrhea", "B12 deficiency"],
                is_controlled=False,
            ),
            DrugFormulary(
                id=str(uuid.uuid4()),
                name="Atorvastatin",
                generic_name="Atorvastatin Calcium",
                brand_names=["Lipitor", "Atorva"],
                drug_class="Statin",
                available_strengths=["10mg", "20mg", "40mg", "80mg"],
                dosage_forms=["tablet"],
                routes=["oral"],
                contraindications=["liver disease", "pregnancy"],
                common_side_effects=["muscle pain", "elevated liver enzymes"],
                is_controlled=False,
            ),
            DrugFormulary(
                id=str(uuid.uuid4()),
                name="Amlodipine",
                generic_name="Amlodipine Besylate",
                brand_names=["Norvasc", "Amlip"],
                drug_class="Calcium Channel Blocker",
                available_strengths=["2.5mg", "5mg", "10mg"],
                dosage_forms=["tablet"],
                routes=["oral"],
                contraindications=["severe aortic stenosis"],
                common_side_effects=["peripheral edema", "flushing", "headache"],
                is_controlled=False,
            ),
            DrugFormulary(
                id=str(uuid.uuid4()),
                name="Omeprazole",
                generic_name="Omeprazole",
                brand_names=["Omez", "Prilosec"],
                drug_class="Proton Pump Inhibitor",
                available_strengths=["10mg", "20mg", "40mg"],
                dosage_forms=["capsule", "tablet"],
                routes=["oral"],
                contraindications=[],
                common_side_effects=["headache", "nausea", "diarrhea"],
                is_controlled=False,
            ),
            DrugFormulary(
                id=str(uuid.uuid4()),
                name="Cetirizine",
                generic_name="Cetirizine Hydrochloride",
                brand_names=["Zyrtec", "Cetzine"],
                drug_class="Antihistamine",
                available_strengths=["5mg", "10mg"],
                dosage_forms=["tablet", "syrup"],
                routes=["oral"],
                contraindications=["severe renal impairment"],
                common_side_effects=["drowsiness", "dry mouth"],
                is_controlled=False,
            ),
            DrugFormulary(
                id=str(uuid.uuid4()),
                name="Azithromycin",
                generic_name="Azithromycin",
                brand_names=["Azithral", "Zithromax"],
                drug_class="Macrolide Antibiotic",
                available_strengths=["250mg", "500mg"],
                dosage_forms=["tablet", "suspension"],
                routes=["oral", "IV"],
                contraindications=["hypersensitivity to macrolides"],
                common_side_effects=["nausea", "diarrhea", "abdominal pain"],
                is_controlled=False,
            ),
        ]
        for drug in drugs:
            db.add(drug)

        await db.flush()

        # Drug interactions
        interaction = DrugInteraction(
            id=str(uuid.uuid4()),
            drug_a_id=drugs[1].id,  # Amoxicillin
            drug_b_id=drugs[7].id,  # Azithromycin
            severity="moderate",
            description="Concurrent use of two antibiotics may increase risk of antibiotic resistance and GI side effects.",
            clinical_significance="Monitor for increased GI adverse effects. Generally avoid concurrent use unless specifically indicated.",
        )
        db.add(interaction)

        interaction2 = DrugInteraction(
            id=str(uuid.uuid4()),
            drug_a_id=drugs[3].id,  # Atorvastatin
            drug_b_id=drugs[4].id,  # Amlodipine
            severity="minor",
            description="Amlodipine may slightly increase atorvastatin levels.",
            clinical_significance="Monitor for statin side effects. Dose adjustment may be needed.",
        )
        db.add(interaction2)

        # Consent versions
        telemedicine_consent = ConsentVersion(
            id=str(uuid.uuid4()),
            consent_type="telemedicine",
            version=1,
            title="Telemedicine Consultation Consent",
            content="""TELEMEDICINE CONSENT FORM

I hereby consent to participate in a telemedicine consultation through this platform, acknowledging the following:

1. NATURE OF TELEMEDICINE: I understand that telemedicine involves the use of electronic communications to enable healthcare providers to provide consultations remotely. I understand that telemedicine has potential benefits and limitations.

2. LIMITATIONS: I understand that my healthcare provider may not have access to complete medical history and that telemedicine may not be appropriate for all medical conditions. In case of an emergency, I will call emergency services (112).

3. TECHNICAL RISKS: I understand that technical difficulties may arise and could limit the quality of the consultation.

4. PRIVACY: I understand that this consultation may be recorded for quality assurance purposes and that my health information will be kept confidential per applicable law.

5. INDIA TELEMEDICINE GUIDELINES: This consultation is conducted in accordance with India's Telemedicine Practice Guidelines 2020.

6. VOLUNTARY: I understand my participation is voluntary and I may stop the consultation at any time.

By proceeding, I confirm that I have read and understood this consent form.""",
            is_active=True,
        )
        db.add(telemedicine_consent)

        dpdp_consent = ConsentVersion(
            id=str(uuid.uuid4()),
            consent_type="data_processing",
            version=1,
            title="Data Processing Consent (DPDP Act 2023)",
            content="""DATA PROCESSING CONSENT

Under India's Digital Personal Data Protection (DPDP) Act 2023, we request your consent to process your personal and health data:

1. DATA COLLECTED: Name, contact details, date of birth, medical history, consultation notes, and prescription records.

2. PURPOSE: To provide healthcare services, maintain medical records, and improve service quality.

3. STORAGE: Your data is stored securely on encrypted servers in India, in compliance with applicable data localization requirements.

4. RETENTION: Health records are retained as per applicable medical record retention guidelines (minimum 3 years from last consultation).

5. SHARING: Your data may be shared with treating physicians and, with your consent, with pharmacies or laboratories.

6. YOUR RIGHTS: You have the right to access, correct, and request deletion of your personal data (subject to legal retention requirements).

7. CONTACT: For data-related queries, contact our Data Protection Officer at privacy@medicare-digital.com.

By proceeding, you provide explicit consent for the processing of your personal data as described above.""",
            is_active=True,
        )
        db.add(dpdp_consent)

        # Questionnaire templates
        gp_questionnaire = QuestionnaireAnswer(
            id=str(uuid.uuid4()),
            specialty="general_practice",
            questions=[
                {"id": "chief_complaint", "label": "What is your main concern today?", "type": "textarea", "required": True},
                {"id": "duration", "label": "How long have you had this issue?", "type": "select", "options": ["Less than 1 day", "1-3 days", "4-7 days", "1-2 weeks", "More than 2 weeks"], "required": True},
                {"id": "severity", "label": "How severe is your discomfort? (1-10)", "type": "slider", "min": 1, "max": 10, "required": True},
                {"id": "symptoms", "label": "Select any associated symptoms:", "type": "multiselect", "options": ["Fever", "Headache", "Nausea", "Vomiting", "Fatigue", "Body aches", "Cough", "Cold", "Shortness of breath"], "required": False},
                {"id": "medications", "label": "Current medications (if any):", "type": "textarea", "required": False},
                {"id": "allergies_confirm", "label": "Do you have any known drug allergies?", "type": "radio", "options": ["Yes", "No"], "required": True},
            ],
            version=1,
            is_active=True,
        )
        db.add(gp_questionnaire)

        derma_questionnaire = QuestionnaireAnswer(
            id=str(uuid.uuid4()),
            specialty="dermatology",
            questions=[
                {"id": "chief_complaint", "label": "Describe your skin concern:", "type": "textarea", "required": True},
                {"id": "location", "label": "Where is the affected area?", "type": "text", "required": True},
                {"id": "duration", "label": "How long have you had this?", "type": "select", "options": ["Less than 1 week", "1-4 weeks", "1-3 months", "More than 3 months"], "required": True},
                {"id": "itching", "label": "Is there itching?", "type": "radio", "options": ["Yes - severe", "Yes - mild", "No"], "required": True},
                {"id": "previous_treatment", "label": "Have you tried any treatment?", "type": "textarea", "required": False},
                {"id": "photo_upload", "label": "Please be ready to share photos during the consultation if needed", "type": "info", "required": False},
            ],
            version=1,
            is_active=True,
        )
        db.add(derma_questionnaire)

        mental_health_questionnaire = QuestionnaireAnswer(
            id=str(uuid.uuid4()),
            specialty="mental_health",
            questions=[
                {"id": "reason", "label": "What brings you to this consultation?", "type": "textarea", "required": True},
                {"id": "phq2", "label": "Over the last 2 weeks, how often have you had little interest or pleasure in doing things?", "type": "select", "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"], "required": True},
                {"id": "phq2_2", "label": "Over the last 2 weeks, how often have you felt down, depressed, or hopeless?", "type": "select", "options": ["Not at all", "Several days", "More than half the days", "Nearly every day"], "required": True},
                {"id": "anxiety", "label": "Have you been experiencing anxiety or worry?", "type": "radio", "options": ["Yes - significant", "Yes - mild", "No"], "required": True},
                {"id": "sleep", "label": "How has your sleep been?", "type": "select", "options": ["Good", "Fair", "Poor - difficulty falling asleep", "Poor - waking up frequently", "Sleeping too much"], "required": True},
                {"id": "previous_care", "label": "Have you received mental health treatment before?", "type": "radio", "options": ["Yes", "No"], "required": True},
            ],
            version=1,
            is_active=True,
        )
        db.add(mental_health_questionnaire)

        await db.commit()
        print("✓ Seed data created successfully!")
        print("\nSeed accounts:")
        print("  Admin:     admin@clinic.com / admin123")
        print("  Doctor 1:  dr.patel@clinic.com / doctor123 (GP)")
        print("  Doctor 2:  dr.sharma@clinic.com / doctor123 (Dermatology)")
        print("  Doctor 3:  dr.mehta@clinic.com / doctor123 (Mental Health)")
        print("  Patient:   +919876543210 / OTP: 123456 (mock)")


if __name__ == "__main__":
    asyncio.run(seed())
