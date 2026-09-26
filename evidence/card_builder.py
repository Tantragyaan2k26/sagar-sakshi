"""
SAGAR-SAKSHI Evidence Card Builder (evidence/card_builder.py)
Constructs prototype EvidenceCard JSON and PDF artifacts.
"""

from datetime import datetime, timezone
import json
import os
from typing import Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from api.schemas import EvidenceCard, AttributionResult


def build_evidence_card_json(
    run_id: str,
    manifest_sha256: str,
    attribution_data: dict[str, Any],
    ais_status: str = "synthetic",
    metadata: dict[str, Any] | None = None,
) -> EvidenceCard:
    """Builds and validates the EvidenceCard Pydantic object."""
    attr_result = AttributionResult(**attribution_data)
    card = EvidenceCard(
        run_id=run_id,
        manifest_sha256=manifest_sha256,
        attribution=attr_result,
        ais_status=ais_status,  # type: ignore
        generated_at_utc=datetime.now(timezone.utc),
        metadata=metadata or {},
    )
    return card


def export_evidence_card_pdf(card: EvidenceCard, output_pdf_path: str):
    """
    Generates an official, publication-quality Evidence Card PDF using ReportLab.
    Includes case overview, headline, posterior breakdown, exclusions, and audit manifest.
    """
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0D2A35"),
    )
    sub_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#46606A"),
    )
    headline_style = ParagraphStyle(
        "HeadlineStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1B6A88"),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0D2A35"),
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("SAGAR-SAKSHI · PROTOTYPE EVIDENCE CARD", title_style))
    story.append(Paragraph(
        f"Smart India Hackathon 2026 | Team Tantragyan (SIH26143) | Run ID: {card.run_id}",
        sub_style,
    ))
    story.append(Spacer(1, 12))

    # 2. Key Findings Summary Box
    attr = card.attribution
    grade_color = "#2B7A57" if attr.grade == "A" else ("#1B6A88" if attr.grade == "B" else "#9A5F0F")
    if attr.grade == "None":
        grade_color = "#B3312A"

    summary_data = [
        [
            Paragraph("<b>EVIDENCE GRADE</b>", body_style),
            Paragraph(f"<font color='{grade_color}'><b>GRADE {attr.grade}</b></font>", body_style),
        ],
        [
            Paragraph("<b>HEADLINE ASSESSMENT</b>", body_style),
            Paragraph(f"<b>{attr.headline}</b>", headline_style),
        ],
        [
            Paragraph("<b>AIS DATA STATUS</b>", body_style),
            Paragraph(f"{card.ais_status.upper()}", body_style),
        ],
        [
            Paragraph("<b>MANIFEST HASH (SHA-256)</b>", body_style),
            Paragraph(f"<font size='7'>{card.manifest_sha256}</font>", body_style),
        ],
    ]
    t_summary = Table(summary_data, colWidths=[150, 380])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF3F2")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#C6D5D4")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C6D5D4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 14))

    # 3. Candidate ranking weights (not calibrated probabilities)
    story.append(Paragraph("<b>Candidate Hypothesis Ranking (normalized, not calibrated)</b>", headline_style))
    story.append(Paragraph(
        "Values below are normalized prototype ranking weights derived from hand-set likelihood ratios; "
        "they are not calibrated probabilities.", body_style
    ))
    story.append(Spacer(1, 6))

    post_rows = [
        [
            Paragraph("<b>Hypothesis / Source</b>", body_style),
            Paragraph("<b>Ranking weight</b>", body_style),
            Paragraph("<b>Drift Fit</b>", body_style),
            Paragraph("<b>Head Prox.</b>", body_style),
            Paragraph("<b>Behavior</b>", body_style),
        ]
    ]

    for h_id, p_val in sorted(attr.posteriors.items(), key=lambda x: x[1], reverse=True):
        terms = attr.evidence_terms.get(h_id, {})
        d_fit = f"{terms.get('drift_consistency', 0.0):.2f}" if h_id != "U" else "N/A"
        h_prox = f"{terms.get('head_proximity', 0.0):.2f}" if h_id != "U" else "N/A"
        b_score = f"{terms.get('behaviour', 0.0):.2f}" if h_id != "U" else "N/A"

        label = "Null / Unknown Source (U)" if h_id == "U" else h_id
        post_rows.append([
            Paragraph(f"<b>{label}</b>", body_style),
            Paragraph(f"<b>{p_val:.4f} ({p_val*100:.1f}%)</b>", body_style),
            Paragraph(d_fit, body_style),
            Paragraph(h_prox, body_style),
            Paragraph(b_score, body_style),
        ])

    t_post = Table(post_rows, colWidths=[180, 110, 80, 80, 80])
    t_post.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2ECEA")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C6D5D4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_post)
    story.append(Spacer(1, 14))

    # 4. Excluded Vessels List
    story.append(Paragraph("<b>Exculpatory Evidence: Excluded Vessels</b>", headline_style))
    story.append(Spacer(1, 6))

    excl_rows = [[Paragraph("<b>Vessel ID</b>", body_style), Paragraph("<b>Exclusion Reason</b>", body_style)]]
    if attr.exclusions:
        for ex in attr.exclusions:
            excl_rows.append([
                Paragraph(ex.get("vessel_id", "Unknown"), body_style),
                Paragraph(ex.get("reason", "Out of reach"), body_style),
            ])
    else:
        excl_rows.append([Paragraph("None", body_style), Paragraph("No vessels ruled out", body_style)])

    t_excl = Table(excl_rows, colWidths=[150, 380])
    t_excl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2ECEA")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C6D5D4")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_excl)
    story.append(Spacer(1, 14))

    # 5. Provenance and prototype limitations
    story.append(Paragraph("<b>Run Sources and Prototype Limitations</b>", headline_style))
    metadata = card.metadata
    provenance_rows = [[Paragraph("<b>Run property</b>", body_style), Paragraph("<b>Recorded value</b>", body_style)]]
    for label, key in [
        ("SAR source", "sar_source"),
        ("Synthetic SAR crop", "sar_synthetic"),
        ("Forcing source", "forcing_source"),
        ("Drift engine", "drift_engine"),
        ("Probabilities calibrated", "probabilities_calibrated"),
    ]:
        if key in metadata:
            provenance_rows.append([Paragraph(label, body_style), Paragraph(str(metadata[key]), body_style)])
    provenance_table = Table(provenance_rows, colWidths=[150, 380])
    provenance_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C6D5D4")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2ECEA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(provenance_table)
    story.append(Spacer(1, 8))
    disclaimer_text = (
        "This prototype may use generated SAR and synthetic AIS, and currently uses configured constant forcing "
        "with simplified drift calculations. It does not fetch CMEMS/ERA5 or run OpenDrift. Coverage must be "
        "independently measured before an unmatched SAR target can be called dark. Evidence grades and ranking "
        "weights are experimental decision-support outputs, not calibrated probabilities or findings of liability."
    )
    story.append(Paragraph(disclaimer_text, body_style))

    doc.build(story)
