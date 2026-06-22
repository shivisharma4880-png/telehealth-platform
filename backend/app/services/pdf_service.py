"""Prescription / consultation summary PDF (ReportLab) — layout inspired by clinical summary templates."""
from __future__ import annotations

import html
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings

# Reference-style deep green bands
HEADER_GREEN = HexColor("#1B4332")
FOOTER_GREEN = HexColor("#164A3B")
BODY_TEXT = HexColor("#1f2937")
LABEL_TEXT = HexColor("#111827")
MUTED = HexColor("#4b5563")
RULE = HexColor("#d1d5db")


def _esc(s: Any) -> str:
    t = "" if s is None else str(s)
    return html.escape(t, quote=False).replace("\n", "<br/>")


def _gender_display(raw: str) -> str:
    if not raw or raw == "N/A":
        return "N/A"
    m = {
        "male": "Male",
        "female": "Female",
        "other": "Other",
        "prefer_not_to_say": "Prefer not to say",
    }
    return m.get(raw.lower(), raw.replace("_", " ").title())


def _draw_footer(canvas, doc) -> None:
    """Bottom green band + page number (matches reference footer strip)."""
    canvas.saveState()
    w, h = doc.pagesize
    bar_h = 11 * mm
    canvas.setFillColor(FOOTER_GREEN)
    canvas.rect(0, 0, w, bar_h, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica", 8)
    msg = "For queries about this document, contact your clinic using the phone number in the header."
    canvas.drawCentredString(w / 2, 3.5 * mm, msg)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(w - doc.rightMargin, 3.5 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def generate_prescription_pdf(
    prescription_data: dict,
    practitioner_data: dict,
    patient_data: dict,
    organization_data: dict,
    medications: list,
) -> str:
    """Generate consultation-summary style prescription PDF; return file path."""
    os.makedirs(settings.pdf_storage_path, exist_ok=True)
    filename = f"prescription_{prescription_data['id']}_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(settings.pdf_storage_path, filename)

    left_m = 14 * mm
    right_m = 14 * mm
    top_m = 12 * mm
    bottom_m = 18 * mm

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=left_m,
        rightMargin=right_m,
        topMargin=top_m,
        bottomMargin=bottom_m,
    )
    content_w = doc.width

    story: list = []

    org_name = organization_data.get("name") or "Medical Clinic"
    addr = (organization_data.get("address") or "").strip()
    phone = (organization_data.get("phone") or "").strip()
    org_right = "<br/>".join(
        _esc(x)
        for x in [addr, phone]
        if x
    ) or _esc(" ")

    # --- Top green header band (logo left, address/phone right) ---
    brand = Paragraph(
        f'<font name="Helvetica-Bold" size="20" color="white">{_esc(org_name)}</font>',
        ParagraphStyle("brand", alignment=TA_LEFT, leading=22),
    )
    org_block = Paragraph(
        f'<font name="Helvetica" size="8" color="white">{org_right}</font>',
        ParagraphStyle("orgblk", alignment=TA_RIGHT, leading=10),
    )
    header_tbl = Table([[brand, org_block]], colWidths=[content_w * 0.42, content_w * 0.58])
    header_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HEADER_GREEN),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(header_tbl)
    story.append(Spacer(1, 6 * mm))

    # Document title
    story.append(
        Paragraph(
            '<font name="Helvetica-Bold" size="14" color="#111827">CONSULTATION SUMMARY</font>',
            ParagraphStyle("doctitle", alignment=TA_CENTER, spaceAfter=6 * mm),
        )
    )

    # --- Two-column patient / visit metadata ---
    mrn = patient_data.get("mrn") or (prescription_data.get("id", "")[:12].upper())
    pname = patient_data.get("full_name") or ""
    g = _gender_display(patient_data.get("gender") or "")
    age = patient_data.get("age") or "N/A"
    dob = patient_data.get("date_of_birth") or "-"
    ga_line = f"{g}, {age} Years, {dob}" if dob != "-" else f"{g}, {age} Years"
    pphone = patient_data.get("phone") or "-"
    paddr = patient_data.get("address") or "-"

    issue_dt = datetime.now(timezone.utc).strftime("%d/%m/%Y %I:%M %p")
    consultant = f'{practitioner_data.get("full_name", "")} ({practitioner_data.get("specialty_display", "Clinician")})'
    consult_type = "Teleconsultation — E-Prescription"
    rx_ref = str(prescription_data.get("id", "")).replace("-", "")[:14].upper()

    val = ParagraphStyle("val", fontName="Helvetica", fontSize=8, textColor=BODY_TEXT, leading=11)

    def lv(label: str, value: str) -> Paragraph:
        return Paragraph(f'<font name="Helvetica-Bold">{_esc(label)}</font> {_esc(value)}', val)

    left_cells = [
        lv("Patient MRN:", str(mrn)),
        lv("Patient Name:", pname),
        lv("Gender / Age / DOB:", ga_line),
        lv("Patient Phone No:", pphone),
        lv("Patient Address:", paddr),
    ]
    right_cells = [
        lv("Consultation Date:", issue_dt),
        lv("Consultant:", consultant),
        lv("Consultation Type:", consult_type),
        Paragraph(
            f'<font name="Helvetica-Bold">Rx reference:</font> <font name="Helvetica">{_esc(rx_ref)}</font>',
            val,
        ),
        Paragraph(
            '<font name="Helvetica" size="6" color="#6b7280">[ Barcode not generated — use Rx reference above ]</font>',
            ParagraphStyle("bcnote", fontSize=6, textColor=MUTED, alignment=TA_LEFT),
        ),
    ]
    max_rows = max(len(left_cells), len(right_cells))
    left_cells.extend([Paragraph("", val)] * (max_rows - len(left_cells)))
    right_cells.extend([Paragraph("", val)] * (max_rows - len(right_cells)))

    meta_rows = [[left_cells[i], right_cells[i]] for i in range(max_rows)]
    meta = Table(meta_rows, colWidths=[content_w * 0.5, content_w * 0.5])
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta)
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=0.75, color=RULE, spaceAfter=4 * mm))
    story.append(
        Paragraph(
            '<font size="8" color="#6b7280">Teleconsultation (e-prescription)</font>',
            ParagraphStyle("subsub", alignment=TA_CENTER, spaceAfter=6 * mm),
        )
    )

    sec = ParagraphStyle(
        "section",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=LABEL_TEXT,
        spaceBefore=5,
        spaceAfter=4,
        leading=12,
    )
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=8.5, textColor=BODY_TEXT, leading=12)

    # Chief complaints / HPI — from free-text notes when present
    story.append(Paragraph("CHIEF COMPLAINTS &amp; HISTORY OF PRESENT ILLNESS", sec))
    hpi = (prescription_data.get("notes") or "").strip()
    if not hpi:
        hpi = "As documented during the teleconsultation. See electronic health record for full encounter details."
    story.append(Paragraph(_esc(hpi), body))

    # Diagnosis
    story.append(Paragraph("DIAGNOSIS", sec))
    dx = (prescription_data.get("diagnosis") or "").strip()
    if dx:
        story.append(Paragraph(f"&bull; {_esc(dx)}", body))
    else:
        story.append(Paragraph("&bull; Not recorded on this prescription.", body))

    # Advice
    story.append(Paragraph("ADVICE", sec))
    advice_lines = [
        "Take medications exactly as prescribed. Do not stop or change doses without consulting your clinician.",
        "Seek emergency care for severe or sudden symptoms (chest pain, stroke signs, severe bleeding, trouble breathing, or suicidal thoughts).",
    ]
    for line in advice_lines:
        story.append(Paragraph(f"&bull; {_esc(line)}", body))

    # Medication block (reference-style heading)
    story.append(Paragraph("MEDICATION &mdash; ORDER", sec))
    if medications:
        for med in medications:
            nm = med.get("drug_name") or ""
            st = med.get("strength") or ""
            form = med.get("dosage_form") or ""
            freq = med.get("frequency") or ""
            dur = med.get("duration") or ""
            ins = (med.get("instructions") or "").strip()
            line1 = f"<b>{_esc(nm)}</b>"
            if st or form:
                line1 += f" &mdash; {_esc(st)} {_esc(form)}".strip()
            line2 = f"{_esc(freq)}; duration: {_esc(dur)}."
            if ins:
                line2 += f" {_esc(ins)}"
            story.append(Paragraph(f"&bull; {line1}<br/>{_esc(line2)}", body))
    else:
        story.append(Paragraph("&bull; No medication lines on this prescription.", body))

    # Interaction warnings
    warns: list[str] = []
    for med in medications:
        for w in med.get("interaction_warnings") or []:
            if isinstance(w, dict):
                warns.append(str(w.get("description") or w))
            else:
                warns.append(str(w))
    if warns:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph("<b>Drug interaction / allergy alerts</b>", sec))
        for w in warns:
            story.append(Paragraph(f"&bull; {_esc(w)}", body))

    # Follow-up
    story.append(Paragraph("FOLLOW UP DETAILS", sec))
    fu = (
        f"Follow up with {practitioner_data.get('full_name', 'your consultant')} "
        f"({practitioner_data.get('specialty_display', 'Clinician')}) as clinically advised."
    )
    story.append(Paragraph(f"&bull; {_esc(fu)}", body))

    # Signature
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=4 * mm))
    sig_html = (
        f'<font name="Helvetica-Bold" size="9">{_esc(practitioner_data.get("full_name", ""))}</font><br/>'
        f'<font size="8" color="#4b5563">{_esc(practitioner_data.get("specialty_display", ""))}</font><br/>'
        f'<font size="8" color="#4b5563">Reg. No: {_esc(practitioner_data.get("registration_number", ""))}</font><br/>'
        f'<font size="8" color="#1B4332">Digitally signed prescription</font>'
    )
    story.append(Paragraph(sig_html, ParagraphStyle("sig", alignment=TA_RIGHT, fontSize=9)))

    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            _esc(
                "This document was issued following a teleconsultation under applicable telemedicine guidelines. "
                "Valid as advised by the prescribing clinician. For emergencies, contact local emergency services."
            ),
            ParagraphStyle("disc", fontSize=7, textColor=MUTED, alignment=TA_CENTER, leading=10),
        )
    )

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return filepath


def _draw_footer_ai_demo(canvas, doc) -> None:
    canvas.saveState()
    w, _h = doc.pagesize
    bar_h = 11 * mm
    canvas.setFillColor(FOOTER_GREEN)
    canvas.rect(0, 0, w, bar_h, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(
        w / 2,
        3.5 * mm,
        "AI-generated demo summary — not medical advice. Use emergency services for urgent symptoms.",
    )
    canvas.drawRightString(w - doc.rightMargin, 3.5 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def generate_ai_voice_visit_summary_pdf(
    *,
    organization_data: dict,
    patient_data: dict,
    visit_datetime_display: str,
    booked_clinician: str | None,
    chief_complaint: str | None,
    session_ref: str,
    visit_summary: str,
    prescription_section: str,
    safety_disclaimer: str,
    filepath: str,
) -> str:
    """Same visual language as clinician consultation PDF — green header, two-column meta, section headings."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    left_m = 14 * mm
    right_m = 14 * mm
    top_m = 12 * mm
    bottom_m = 18 * mm

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=left_m,
        rightMargin=right_m,
        topMargin=top_m,
        bottomMargin=bottom_m,
    )
    content_w = doc.width
    story: list = []

    org_name = organization_data.get("name") or "Medical Clinic"
    addr = (organization_data.get("address") or "").strip()
    phone = (organization_data.get("phone") or "").strip()
    org_right = "<br/>".join(_esc(x) for x in [addr, phone] if x) or _esc(" ")

    brand = Paragraph(
        f'<font name="Helvetica-Bold" size="20" color="white">{_esc(org_name)}</font>',
        ParagraphStyle("brand_ai", alignment=TA_LEFT, leading=22),
    )
    org_block = Paragraph(
        f'<font name="Helvetica" size="8" color="white">{org_right}</font>',
        ParagraphStyle("orgblk_ai", alignment=TA_RIGHT, leading=10),
    )
    header_tbl = Table([[brand, org_block]], colWidths=[content_w * 0.42, content_w * 0.58])
    header_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HEADER_GREEN),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(header_tbl)
    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            '<font name="Helvetica-Bold" size="14" color="#111827">CONSULTATION SUMMARY</font>',
            ParagraphStyle("doctitle_ai", alignment=TA_CENTER, spaceAfter=2 * mm),
        )
    )
    story.append(
        Paragraph(
            '<font name="Helvetica" size="9" color="#4b5563">AI voice visit (demo) — draft document, not a formal prescription</font>',
            ParagraphStyle("subtitle_ai", alignment=TA_CENTER, spaceAfter=6 * mm),
        )
    )

    mrn = patient_data.get("mrn") or "-"
    pname = patient_data.get("full_name") or ""
    g = _gender_display(patient_data.get("gender") or "")
    age = patient_data.get("age") or "N/A"
    dob = patient_data.get("date_of_birth") or "-"
    ga_line = f"{g}, {age} Years, {dob}" if dob != "-" else f"{g}, {age} Years"
    pphone = patient_data.get("phone") or "-"
    paddr = patient_data.get("address") or "-"

    val = ParagraphStyle("val_ai", fontName="Helvetica", fontSize=8, textColor=BODY_TEXT, leading=11)

    def lv(label: str, value: str) -> Paragraph:
        return Paragraph(f'<font name="Helvetica-Bold">{_esc(label)}</font> {_esc(value)}', val)

    bc = booked_clinician or "-"
    cc = (chief_complaint or "").strip() or "-"

    left_cells = [
        lv("Patient MRN:", str(mrn)),
        lv("Patient Name:", pname),
        lv("Gender / Age / DOB:", ga_line),
        lv("Patient Phone No:", pphone),
        lv("Patient Address:", paddr),
    ]
    right_cells = [
        lv("Consultation Date:", visit_datetime_display),
        lv("Consultation Type:", "AI voice consult (demo)"),
        lv("Booked clinician:", bc),
        lv("Reason on file:", cc),
        lv("Session reference:", session_ref),
    ]
    max_rows = max(len(left_cells), len(right_cells))
    left_cells.extend([Paragraph("", val)] * (max_rows - len(left_cells)))
    right_cells.extend([Paragraph("", val)] * (max_rows - len(right_cells)))

    meta = Table([[left_cells[i], right_cells[i]] for i in range(max_rows)], colWidths=[content_w * 0.5, content_w * 0.5])
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta)
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=0.75, color=RULE, spaceAfter=4 * mm))
    story.append(
        Paragraph(
            '<font size="8" color="#6b7280">AI-assisted teleconsultation (voice demo)</font>',
            ParagraphStyle("subsub_ai", alignment=TA_CENTER, spaceAfter=6 * mm),
        )
    )

    sec = ParagraphStyle(
        "sec_ai",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=LABEL_TEXT,
        spaceBefore=5,
        spaceAfter=4,
        leading=12,
    )
    body = ParagraphStyle("body_ai", fontName="Helvetica", fontSize=8.5, textColor=BODY_TEXT, leading=12)

    story.append(Paragraph("CHIEF COMPLAINTS &amp; HISTORY OF PRESENT ILLNESS", sec))
    hpi = cc if cc != "-" else ""
    if not hpi:
        hpi = (
            "Reason for visit as captured at booking or during the AI intake. "
            "This demo summary does not replace a full clinical history."
        )
    story.append(Paragraph(_esc(hpi), body))

    story.append(Paragraph("VISIT SUMMARY", sec))
    vs = (visit_summary or "").strip()
    if not vs:
        vs = "No visit summary text was generated for this session."
    story.append(Paragraph(_esc(vs), body))

    story.append(Paragraph("CARE PLAN / PRESCRIPTION SECTION (DRAFT)", sec))
    story.append(
        Paragraph(
            '<font size="8" color="#b45309"><i>Not a formal prescription — educational draft only.</i></font>',
            ParagraphStyle("draft_note", fontSize=8, spaceAfter=3),
        )
    )
    ps = (prescription_section or "").strip()
    if not ps:
        ps = "No care-plan draft text was generated."
    story.append(Paragraph(_esc(ps), body))

    story.append(Paragraph("IMPORTANT DISCLAIMERS", sec))
    sd = (safety_disclaimer or "").strip()
    if sd:
        story.append(Paragraph(_esc(sd), body))
    story.append(
        Paragraph(
            _esc(
                "This document was produced by an automated demo system. It is not medical advice and does not replace "
                "a licensed clinician. For emergencies, contact local emergency services."
            ),
            body,
        )
    )

    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=4 * mm))
    story.append(
        Paragraph(
            '<font size="9" color="#1B4332"><b>Generated electronically</b></font><br/>'
            '<font size="8" color="#4b5563">AI voice demo — not clinician-signed</font>',
            ParagraphStyle("egen", alignment=TA_RIGHT, fontSize=9),
        )
    )
    story.append(Spacer(1, 5 * mm))

    doc.build(story, onFirstPage=_draw_footer_ai_demo, onLaterPages=_draw_footer_ai_demo)
    return filepath


pdf_service = type("PDFService", (), {"generate": staticmethod(generate_prescription_pdf)})()
