# 🏥 AI-Powered Telehealth Platform — MVP PRD

> **Role:** Lead Product Manager &nbsp;|&nbsp; **Phase:** MVP (Phase 1) &nbsp;|&nbsp; **Market:** India &nbsp;|&nbsp; **Specialties:** General Practice · Dermatology · Mental Health

[![Status](https://img.shields.io/badge/Status-MVP%20Phase%201-brightgreen)](#)
[![Market](https://img.shields.io/badge/Market-India-blue)](#)
[![Compliance](https://img.shields.io/badge/Compliance-DPDP%20%7C%20Telemedicine%20Guidelines-orange)](#)
[![AI](https://img.shields.io/badge/AI-Assisted%20%28Not%20Autonomous%29-purple)](#)

---

## 

A narrow-scope, clinician-first teleconsultation product that automates the patient journey from **booking → video consult → AI-assisted SOAP notes → e-prescription** — compliant with India's regulations, FHIR-ready for future EHR integrations, and designed to ship to mid-sized clinics within a 6–9 month horizon.

---

## 📋 Table of Contents

1. [Problem Space](#1-problem-space)
2. [Product Opportunity](#2-product-opportunity)
3. [Target Users & Personas](#3-target-users--personas)
4. [End-to-End User Journey](#4-end-to-end-user-journey)
5. [Core Feature Set (MVP)](#5-core-feature-set-mvp)
6. [What's Out of Scope](#6-whats-out-of-scope)
7. [Key PM Decisions & Trade-offs](#7-key-pm-decisions--trade-offs)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Risk Register](#9-risk-register)
10. [Success Metrics](#10-success-metrics)
11. [Technology Choices](#11-technology-choices)
12. [PM Thesis](#12-pm-thesis)

---

## 1. Problem Space

Clinics and patients in India's outpatient telehealth space face four compounding friction points:

| # | Problem | Who It Hurts |
|---|---------|-------------|
| 1 | **Fragmented patient journey** — separate booking apps, video tools, and messaging platforms cause missed appointments and duplicated data entry | Patients |
| 2 | **Clinician burnout from admin** — manual note-writing during consultations reduces eye contact and erodes patient trust | Clinicians |
| 3 | **Unstructured prescriptions** — handwritten or separately generated Rx lacks structured data, interaction checks, or easy digital sharing | Clinicians, Pharmacies |
| 4 | **No compliant teleconsult stack** — clinics lack a simple, auditable telehealth platform aligned with India's Telemedicine Practice Guidelines and DPDP Act | Clinic Admins, Medical Directors |

---

## 2. Product Opportunity

> Build a **safe, compliant, AI-assisted** teleconsultation product for high-frequency, low-acuity outpatient care that drastically reduces clinician admin time and improves patient experience — without high-risk autonomous triage.

**Why this market, why now:**
- Teleconsultation is explicitly permitted under India's Telemedicine Practice Guidelines (2020) for GP, dermatology, and mental health
- Clinician admin burden is the #1 satisfaction driver in telehealth NPS surveys
- No incumbent offers a tightly integrated booking → consult → AI notes → e-Rx workflow compliant with DPDP

---

## 3. Target Users & Personas

### Primary Personas

**🧑‍💼 Patient** *(India, 18–65)*
- Mobile-first user booking virtual consults for themselves or family members
- Often on mid-range Android with variable bandwidth
- Needs: simplicity, reminders, easy access to post-consult records

**👨‍⚕️ Clinician** *(GP, Dermatologist, Psychiatrist)*
- Licensed doctor in a clinic or small hospital
- High admin burden from manual note-taking and prescribing
- Needs: fewer clicks, trustworthy AI assistance, fast prescription generation

**🖥️ Clinic Admin / Receptionist**
- Manages clinic schedules, handles patient queries, reconciles payments
- Needs: one dashboard, easy rescheduling, simple reporting

### Secondary Personas

- **Clinic Owner / Medical Director** — evaluates solutions for cost, compliance, and clinician satisfaction
- **Technical Integrator** *(Phase 2)* — EHR/IT partner integrating via FHIR/REST APIs

---

## 4. End-to-End User Journey

```
📲 Discover & Book  →  💳 Pay & Consent  →  🎥 Video Consult  →  🤖 AI SOAP Notes  →  💊 E-Rx & Records
```

| Step | Patient Actions | Clinician Actions |
|------|----------------|-------------------|
| **Book** | Search by specialty/language/fee · Choose slot · Fill pre-consult Q | — |
| **Consent & Pay** | DPDP consent · UPI / card payment · Receive reminder | — |
| **Consult** | Join via deep link · Switch video ↔ audio | View schedule · Join call · See live transcription |
| **Documentation** | — | Click "Generate Notes" · Edit SOAP draft · Confirm diagnosis |
| **Prescription** | Receive signed PDF in app | Search formulary · Review interaction warnings · Sign Rx |
| **Post-Consult** | View visit summary · Download records | — |

**Edge cases handled in MVP:** connectivity drops, audio-only fallback, clinician running late, patient no-show, prescription edit after consult.

---

## 5. Core Feature Set (MVP)

### 5.1 Patient Booking & Onboarding
- Phone OTP auth + optional email; basic KYC (name, DOB, gender, mobile, optional ABHA ID)
- Dynamic slot picker filtered by specialty, language, and fee range
- Customizable pre-consult questionnaire per specialty
- Versioned consent flows aligned with DPDP Act and Telemedicine Guidelines
- Payment via UPI, cards, and wallets through PCI-compliant gateway
- SMS and WhatsApp reminders (DND-compliant)

### 5.2 Teleconsultation (Video / Audio / Chat)
- WebRTC-based video and audio consult with in-call chat
- **Audio-only fallback** with clear UI indicator for degraded connections
- Screen-share for clinician (one-way)
- Call metadata logging (start/end time, participants, quality metrics)
- Patient joins from web or Android app; clinician from desktop web or tablet browser

### 5.3 AI-Assisted Transcription & SOAP Notes
- Server-side Medical ASR transcribes consult audio in near real-time
- LLM generates draft notes in configurable SOAP structure:
  - **S**ubjective — patient symptoms and history
  - **O**bjective — vitals (if recorded), observed findings
  - **A**ssessment — clinician's diagnosis (if mentioned explicitly)
  - **P**lan — proposed treatment, tests, and follow-up
- Clinician can toggle transcription visibility, regenerate notes once per consult
- **All AI outputs clearly labeled as drafts** — clinician edits and approves before saving

### 5.4 E-Prescription Module
- Drug search from curated formulary (name, strength, dosage, frequency, duration)
- Basic drug-interaction and allergy checks (rule-based, not full CDS)
- Digitally signed, clinic-branded PDF with doctor registration number
- Stored internally as FHIR-like `MedicationRequest` / `MedicationStatement`
- Patient receives prescription as in-app view/download

### 5.5 Admin Console & Reporting
- Manage clinician profiles (specialty, languages, fee, availability)
- View and filter appointments by status (booked, completed, no-show, cancelled)
- Basic operational metrics: consults per day/week, no-show rate, avg consult duration
- CSV export for appointments and basic revenue data

### 5.6 Security, Compliance & Auditability
- OAuth2 / OIDC with JWT sessions (short TTL + refresh tokens)
- Role-based access control (patient, clinician, admin)
- PHI encrypted at rest (database-level) and in transit (TLS 1.2+)
- Append-only audit logs: logins, prescription generation/edits, data exports
- Clinician 2FA (password + OTP or authenticator app)
- Privacy policy and consent text aligned with India's DPDP Act

---

## 6. What's Out of Scope

The following are intentionally deferred to later phases:

| Excluded Feature | Reason |
|-----------------|--------|
| Autonomous triage / CDS (diagnosis or test suggestions) | High-risk AI classification; regulatory exposure |
| Full NDHM/ABDM, Epic, NHS EPS production integrations | Complexity; sandboxes allowed for POCs only |
| Payer/claims integration or full RCM | Scope creep; basic payment collection sufficient for MVP |
| Chronic-care modules, remote monitoring | Requires different clinical workflows and device integrations |
| Global regulatory coverage (EU/US) | India is primary reference; HIPAA-aligned practices applied as best effort |
| Fraud detection models | Only basic logging for potential future modeling |

---

## 7. Key PM Decisions & Trade-offs

### 🎯 Narrow specialty focus — GP, Dermatology, Mental Health only
**Decision:** Excluded complex chronic-care and high-risk specialties.  
**Rationale:** These three represent the highest teleconsult acceptance by Indian regulators. Narrowing scope reduces regulatory surface area and enables faster validation with a smaller clinical partner footprint.

### 🤖 AI assists — never decides
**Decision:** All AI outputs require explicit clinician approval; no autonomous recommendations.  
**Rationale:** Keeps the product out of India's high-risk AI and SaMD classification. Builds clinician trust incrementally. Allows launch without a medical device regulatory review cycle.

### 🏗️ FHIR-conformant internals without full EHR integration
**Decision:** Built FHIR R4-aligned data structures internally while deferring production integrations.  
**Rationale:** Pays down architectural debt in advance. When Phase 2 demands ABDM or EHR connectivity, the data model is already right — we expose endpoints rather than refactor the schema.

### 📱 Android-first, bandwidth-aware design
**Decision:** Audio-only fallback and adaptive bitrate are P0 requirements, not P2.  
**Rationale:** India's 18–65 patient persona is predominantly on mid-range Android with variable connectivity. A product that degrades poorly under poor network conditions will fail at the core use case.

### 💰 Deferred marketplace complexity
**Decision:** No complex provider ranking or multi-clinic marketplace logic in MVP.  
**Rationale:** Direct clinic links and simple specialty/fee/language filters are sufficient for pilot validation. Marketplace dynamics require supply-demand balance that doesn't exist at MVP scale.

---

## 8. Non-Functional Requirements

| Dimension | Target |
|-----------|--------|
| **Concurrent video consults** | 100+ in a single region |
| **API latency** (core operations) | < 200 ms average |
| **Video latency** (one-way) | < 150 ms under normal conditions |
| **Uptime** | ≥ 99.5% |
| **Graceful degradation** | Consults and manual notes must work if AI services are down |
| **Security standard** | OWASP ASVS-aligned (input validation, rate limiting, secure sessions) |
| **PHI storage** | Encrypted databases, network segmentation, least-privilege access |
| **Audit logs** | Append-only for medico-legal compliance |

---

## 9. Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| AI outputs mistaken for clinical decisions | 🔴 High | Draft labeling on all AI content; mandatory clinician approval; T&C disclaimers |
| Regulatory non-compliance blocks pilots | 🔴 High | Legal review of DPDP & Telemedicine Guidelines pre-launch; high-risk AI excluded from MVP |
| ASR quality in multilingual/noisy consultations | 🟡 Medium | English/Hinglish pilot only; clinician edit UX; ASR WER logged for model improvement |
| Bandwidth degradation in semi-urban India | 🟡 Medium | Audio-only fallback, adaptive bitrate, lightweight UI |
| Clinician AI adoption resistance | 🟢 Low | Co-design with early adopters; minimal-click workflow; measure time-saved pre/post baseline |

---

## 10. Success Metrics

Success in the first 6–9 months post-MVP will be evaluated across four dimensions:

### Clinical / Experience
- 🎯 Patient CSAT ≥ **4.3 / 5** for teleconsult experience
- 🎯 Clinician survey shows ≥ **30% perceived reduction** in documentation time vs. baseline

### Operational
- 🎯 Average wait time from booking to consult: **< 24 hours** (GP) / **< 72 hours** (specialists)
- 🎯 No-show rate **< 20%** with reminders enabled

### Technical
- 🎯 System uptime ≥ **99.5%**
- 🎯 Transcription WER and note-quality scores **trending positively** in internal evaluations

### Business
- 🎯 At least **2–3 pilot clinics** using the system as primary teleconsult platform
- 🎯 Monthly consult volume ≥ **1,000** within pilot cohort with stable clinician retention

---

## 11. Technology Choices

| Layer | Choices |
|-------|---------|
| **Cloud / Infra** | AWS or Azure (HIPAA-aligned compliant regions), microservices architecture |
| **Auth** | OAuth2 / OIDC, JWT short-TTL sessions, 2FA (OTP or authenticator) |
| **Video** | In-house WebRTC or healthcare-compliant vendor |
| **AI / ASR** | Medical-domain ASR model; LLM with explicit no-training-on-user-data agreement |
| **Interoperability** | FHIR R4 internal model; Aidbox-compatible (Phase 2); ABDM sandbox POC |
| **Payments** | UPI, cards, wallets via PCI-compliant Indian gateway |
| **Messaging** | SMS + WhatsApp via DND-compliant Indian providers |

---

## 12. PM Thesis

### On scope decisions
The full vision included autonomous triage, clinical decision support, global EHR integrations, and fraud detection. But shipping a 12-module system to a 3-person clinical team in Year 1 would have created regulatory exposure, adoption friction, and an unmaintainable surface area.

The MVP scope is a deliberate bet: **prove that AI-assisted documentation alone can save clinicians 30%+ of admin time**, then use that proof to unlock the roadmap. Every excluded feature is an explicit Phase 2+ item, not a forgotten one.

### On architecture as strategy
We could have used a simple relational schema and shipped faster. Instead, the team paid down technical debt in advance — FHIR R4-conformant internals mean that when a hospital partner demands ABDM integration in Phase 2, we don't refactor the data model. We just expose the endpoints. Architecture decisions compound like interest.

### On AI trust in clinical settings
Every AI feature in this PRD is designed to be "opt-in" in terms of autonomy. Clinicians can ignore transcription, override SOAP drafts, and reject drug-interaction suggestions. **Trust is built through transparency, editability, and demonstrated time savings** — not through forcing AI into the workflow. The goal is for clinicians to choose AI assistance because it's genuinely faster, not because the product removes their agency.

---

## 📁 Repository Structure

```
/
├── README.md               ← This file (case study overview)
├── PRD.pdf                 ← Full Narrow-Scope MVP PRD document
├── docs/
│   ├── user-flows.md       ← Detailed user journey flows
│   ├── data-model.md       ← FHIR R4 entity definitions
│   └── compliance.md       ← DPDP + Telemedicine Guidelines mapping
└── assets/
    └── architecture.png    ← System architecture diagram
```

---

## 🔗 Related

- [Phase 2 Roadmap](#) — ABDM integration, lab/pharmacy APIs, CDS
- [Go-to-Market Strategy](#) — Clinic acquisition, pricing, onboarding playbook
- [FHIR Data Model Deep-Dive](#) — Entity relationships and API design

---

*Built with a focus on compliant, scalable, clinician-first product design for India's digital health ecosystem.*
