"""
Report Service — PDF and JSON reports for RSWF conservation and SDG planning.

Generates two separate reports from the same live analytics data:

  * Conservation & Plantation Planning report — the field decision-support document, with
    site overview, zone breakdown, plantation health, areas needing action and next steps.
  * SDG & Project Impact report — a shorter funder-facing document mapping the field work
    onto UN Sustainable Development Goals with measurable evidence.

Both PDFs share a common visual language (header band, KPI strip, section numbering, table
styling and footer with page numbers), kept in a small set of helper functions near the top.
Report text is written for RSWF staff and funders — plain, no implementation jargon.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.services.analytics_service import AnalyticsService
from app.services.data_service import (
    load_clean_csv_records,
    load_planted_plants_store,
    load_monitoring_store,
)

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------------------------
# Shared visual language
# --------------------------------------------------------------------------------------------

PAGE = A4
PAGE_W, PAGE_H = PAGE
MARGIN = 18 * mm

# Palette — green primary (RSWF), slate neutrals, muted accents for data rows
PRIMARY = colors.HexColor("#0f766e")       # teal-green: headings, KPI accents
PRIMARY_DARK = colors.HexColor("#0a4f49")  # darker teal: section bars
INK = colors.HexColor("#111827")           # near-black body
MUTED = colors.HexColor("#64748b")         # labels, captions
RULE = colors.HexColor("#e2e8f0")          # table borders
ZEBRA = colors.HexColor("#f8fafc")         # alternating rows
PANEL = colors.HexColor("#ecfdf5")         # KPI background
WARN = colors.HexColor("#b45309")          # amber for warning badges
DANGER = colors.HexColor("#b91c1c")        # red for high-priority
GOOD = colors.HexColor("#166534")          # dark green for Alive

_styles = getSampleStyleSheet()


def _style(name: str, **kwargs) -> ParagraphStyle:
    base = _styles["Normal"]
    return ParagraphStyle(name, parent=base, **kwargs)


S_TITLE = _style(
    "ReportTitle", fontName="Helvetica-Bold", fontSize=20, leading=24,
    textColor=colors.white, alignment=TA_LEFT,
)
S_SUBTITLE = _style(
    "ReportSubtitle", fontName="Helvetica", fontSize=10.5, leading=14,
    textColor=colors.HexColor("#d1fae5"), alignment=TA_LEFT,
)
S_SECTION = _style(
    "SectionHead", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
    textColor=PRIMARY_DARK, spaceBefore=14, spaceAfter=4,
)
S_SUB = _style(
    "SubHead", fontName="Helvetica-Bold", fontSize=10, leading=13,
    textColor=INK, spaceBefore=6, spaceAfter=2,
)
S_BODY = _style(
    "Body", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INK,
    spaceAfter=4,
)
S_BODY_SMALL = _style(
    "BodySmall", fontName="Helvetica", fontSize=8.5, leading=12, textColor=INK,
    spaceAfter=3,
)
S_META = _style(
    "Meta", fontName="Helvetica", fontSize=8.5, leading=12, textColor=MUTED,
)
S_META_WHITE = _style(
    "MetaWhite", fontName="Helvetica", fontSize=8.5, leading=12,
    textColor=colors.HexColor("#d1fae5"),
)
S_KPI_LABEL = _style(
    "KPIlabel", fontName="Helvetica", fontSize=8, leading=10,
    textColor=MUTED, alignment=TA_CENTER,
)
S_KPI_VALUE = _style(
    "KPIvalue", fontName="Helvetica-Bold", fontSize=18, leading=22,
    textColor=PRIMARY_DARK, alignment=TA_CENTER,
)
S_FOOTNOTE = _style(
    "Footnote", fontName="Helvetica-Oblique", fontSize=8, leading=11,
    textColor=MUTED,
)
S_COVER_META = _style(
    "CoverMeta", fontName="Helvetica", fontSize=9.5, leading=13.5,
    textColor=colors.HexColor("#e2e8f0"), alignment=TA_LEFT,
)


# --------------------------------------------------------------------------------------------
# Visual building blocks
# --------------------------------------------------------------------------------------------

def _header_band(title: str, subtitle: str, meta: Dict[str, str]) -> Table:
    """
    Top-of-page title band: title, subtitle and a two-column metadata strip. Used only on
    page one of each report; subsequent pages get the slim running header via onLaterPages.
    """
    meta_pairs = [
        ("Organization", meta.get("organization", "")),
        ("Project site", meta.get("project_site", "")),
        ("Generated", meta.get("generated_at", "")),
        ("Report version", meta.get("version", "1.0")),
    ]
    rows = [
        [Paragraph(f"<b>{k}</b>", S_META_WHITE), Paragraph(v, S_COVER_META)]
        for k, v in meta_pairs
    ]
    meta_t = Table(rows, colWidths=[32 * mm, (PAGE_W - 2 * MARGIN) - 32 * mm])
    meta_t.setStyle(TableStyle([
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    inner = Table(
        [
            [Paragraph(title, S_TITLE)],
            [Paragraph(subtitle, S_SUBTITLE)],
            [Spacer(1, 4)],
            [meta_t],
        ],
        colWidths=[PAGE_W - 2 * MARGIN],
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    return inner


def _kpi_strip(items: List[Dict[str, str]]) -> Table:
    """A row of equally-sized KPI cards (label + big number)."""
    cols = len(items) if items else 1
    cell_w = (PAGE_W - 2 * MARGIN) / cols
    row = [
        Table(
            [
                [Paragraph(it["label"], S_KPI_LABEL)],
                [Paragraph(str(it["value"]), S_KPI_VALUE)],
                [Paragraph(it.get("note", ""), S_META)] if it.get("note") else [Spacer(1, 1)],
            ],
            colWidths=[cell_w - 6],
        )
        for it in items
    ]
    for sub in row:
        sub.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PANEL),
            ("BOX", (0, 0), (-1, -1), 0.4, RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
    outer = Table([row], colWidths=[cell_w] * cols)
    outer.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return outer


def _section_heading(number: int, title: str) -> Table:
    """Numbered section header with a thin coloured accent bar on the left."""
    inner = Paragraph(f"<b>{number}. {title}</b>", _style(
        "SectionInner", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=PRIMARY_DARK,
    ))
    t = Table(
        [[inner]],
        colWidths=[PAGE_W - 2 * MARGIN],
    )
    t.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, -1), 3, PRIMARY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _data_table(headers: List[str], rows: List[List[Any]], col_widths: Optional[List[float]] = None) -> Table:
    """Standard data table: coloured header row, grid, alternating row backgrounds, cells wrap."""
    content: List[List[Any]] = [[Paragraph(f"<b>{h}</b>", _style(
        "TH", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white,
    )) for h in headers]]
    for r in rows:
        formatted: List[Any] = []
        for cell in r:
            if hasattr(cell, "wrap"):
                formatted.append(cell)
            else:
                formatted.append(Paragraph(str(cell) if cell is not None else "", S_BODY_SMALL))
        content.append(formatted)

    t = Table(content, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
    ]))
    return t


def _status_pill(label: str, kind: str) -> Paragraph:
    """A small coloured pill: 'ok' | 'warn' | 'danger' | 'neutral'. Used inline in tables."""
    palette = {
        "ok": ("#ecfdf5", "#166534"),
        "warn": ("#fef3c7", "#b45309"),
        "danger": ("#fee2e2", "#b91c1c"),
        "neutral": ("#f1f5f9", "#475569"),
    }
    bg, fg = palette.get(kind, palette["neutral"])
    return Paragraph(
        f'<font color="{fg}"><b>{label}</b></font>',
        _style(
            f"pill_{kind}", fontName="Helvetica-Bold", fontSize=8, leading=11,
            backColor=colors.HexColor(bg), borderPadding=(2, 5, 2, 5),
            borderRadius=4, alignment=TA_CENTER,
        ),
    )


def _draw_footer(canvas, doc, report_label: str) -> None:
    """onFirstPage/onLaterPages callback: footer with report label, site and page number."""
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 10 * mm, f"{report_label} · Van Udyan, Bavdhan, Pune")
    canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


# --------------------------------------------------------------------------------------------
# Shared data layer (dynamic; no hardcoded totals)
# --------------------------------------------------------------------------------------------

def _common_data() -> Dict[str, Any]:
    bio = AnalyticsService.get_biodiversity_analytics()
    zones = AnalyticsService.get_zone_analytics()
    coverage = AnalyticsService.get_coverage_analytics()
    actions = AnalyticsService.get_action_priorities()
    temporal = AnalyticsService.get_temporal_analytics()

    plants = load_planted_plants_store() or []
    alive = sum(1 for p in plants if (p.get("status") or "").lower() == "alive")
    dead = sum(1 for p in plants if (p.get("status") or "").lower() == "dead")
    unknown = sum(1 for p in plants if (p.get("status") or "").lower() == "unknown")
    known = alive + dead
    survival_pct = round(alive / known * 100, 1) if known > 0 else None

    source_counts = bio.get("observations_by_source", {}) if bio else {}
    inat_count = source_counts.get("iNaturalist", 0)
    ngo_count = source_counts.get("NGO / New Upload", 0)

    monitoring_visits = len(load_monitoring_store() or [])

    return {
        "generated_at": datetime.now().strftime("%d %B %Y, %H:%M IST"),
        "biodiversity": bio,
        "zones_analytics": zones,
        "coverage": coverage,
        "actions": actions.get("priorities", []) if actions else [],
        "temporal": temporal,
        "plants": plants,
        "alive": alive,
        "dead": dead,
        "unknown": unknown,
        "known_status": known,
        "survival_pct": survival_pct,
        "inat_count": inat_count,
        "ngo_count": ngo_count,
        "monitoring_visits": monitoring_visits,
    }


def _survival_text(d: Dict[str, Any]) -> str:
    """Short, stable display string for the survival KPI. Backwards-compatible wording."""
    if d["survival_pct"] is None:
        return "Insufficient monitoring data."
    return f"{d['survival_pct']}%"


def _survival_detail(d: Dict[str, Any]) -> str:
    """Longer form used only in cover KPI strips and prose."""
    if d["survival_pct"] is None:
        return "Not enough health-check data yet."
    return f"{d['survival_pct']}% ({d['alive']} of {d['known_status']} alive)"


# --------------------------------------------------------------------------------------------
# ReportService — public API
# --------------------------------------------------------------------------------------------

class ReportService:
    """Builds conservation and SDG reports from live analytics data."""

    # ===== JSON payloads (unchanged shape for backward compatibility) =====

    @staticmethod
    def get_conservation_report_data() -> Dict[str, Any]:
        """Full JSON payload for the conservation report. Kept broad so the API stays stable."""
        d = _common_data()
        bio = d["biodiversity"] or {}
        zones_dict = (d["zones_analytics"] or {}).get("zones", {})
        zone_list = list(zones_dict.values()) if isinstance(zones_dict, dict) else zones_dict
        coverage = d["coverage"] or {}
        active_area = (coverage.get("active_zones_summary") or {}).get("area_ha", 0.55)
        outer_area = (coverage.get("non_active_portion_summary") or {}).get("area_ha", 3.02)

        plant_inventory = [
            {
                "plant_id": p.get("id"),
                "plant_code": p.get("plant_code"),
                "scientific_name": p.get("scientific_name"),
                "common_name": p.get("common_name"),
                "zone_code": p.get("zone_code"),
                "planted_on": p.get("planted_on"),
                "status": p.get("status"),
            }
            for p in d["plants"]
        ]

        # Rule-based next actions derived from live state (not hardcoded plant codes)
        next_actions: List[Dict[str, str]] = []
        if d["unknown"] > 0:
            next_actions.append({
                "title": "Visit plants with unknown health",
                "description": f"{d['unknown']} planted plants have no recent health check. Record a visit to confirm whether each one is alive, dead or missing.",
            })
        if d["dead"] > 0:
            next_actions.append({
                "title": "Inspect sites of dead plants",
                "description": f"{d['dead']} planted plants are recorded as dead. Walk those sites to understand what went wrong (water, soil, grazing) before planting replacements.",
            })
        if (coverage.get("non_active_portion_summary") or {}).get("recorded_observations", 0) > 0:
            next_actions.append({
                "title": "Expand field monitoring beyond the active zones",
                "description": f"{(coverage.get('non_active_portion_summary') or {}).get('recorded_observations', 0)} plants were recorded outside the three active zones ({outer_area} ha of the site). Consider adding a fourth zone or doing periodic surveys there.",
            })
        if d["ngo_count"] < 50 or d["monitoring_visits"] < 10:
            next_actions.append({
                "title": "Hold a volunteer field upload drive",
                "description": "The dashboard identifies species from any geotagged photo. A short volunteer event with phones can add hundreds of field records in a day.",
            })
        if not next_actions:
            next_actions.append({
                "title": "Continue the current monitoring routine",
                "description": "All indicators are healthy. Keep scheduling monthly health checks and field uploads.",
            })

        # Plantation assessments: areas with no planted plants or with mortality
        assessments: List[Dict[str, str]] = []
        for z in zone_list:
            code = z.get("zone_code")
            if z.get("planted_plants_count", 0) == 0:
                assessments.append({
                    "area_code": code,
                    "assessment_category": "No planted plants recorded",
                    "indicator": "This active zone has no planted plants in the database yet.",
                    "note": "Confirm whether any plantings exist here and add them to the system.",
                })
            else:
                st = z.get("plant_status_counts", {}) or {}
                if st.get("Dead", 0) > 0 or st.get("Unknown", 0) > 0:
                    assessments.append({
                        "area_code": code,
                        "assessment_category": "Needs field inspection",
                        "indicator": f"{st.get('Dead', 0)} dead and {st.get('Unknown', 0)} unknown-status plants.",
                        "note": "Check soil, water and tags; log a health visit for each.",
                    })

        return {
            "title": "Van Udyan Conservation & Plantation Planning Report",
            "subtitle": "A field decision-support summary for the RSWF Van Udyan project",
            "metadata": {
                "generated_at": d["generated_at"],
                "project_site": "Bavdhan Van Udyan, Pune (Plus Code GQ9J+74Q)",
                "organization": "Reform Social Welfare Foundation (RSWF), Pune",
                "data_sources": [
                    "iNaturalist records inside the Van Udyan boundary (reference baseline)",
                    "RSWF planted plants with planting dates and locations",
                    "RSWF volunteer field photo uploads",
                    "Health-check visits recorded by RSWF staff",
                ],
                "data_limitations_notice": (
                    "The numbers in this report describe what has been recorded in the database. "
                    "An area with no records means no one has recorded anything there yet — "
                    "it does not mean the area has no plants."
                ),
                "version": "2.0",
            },
            "project_area": {
                "site_name": "Bavdhan Van Udyan, Pune",
                "plus_code": "GQ9J+74Q",
                "total_boundary_area_ha": 3.58,
                "active_zones_count": 3,
                "active_zones_total_area_ha": active_area,
                "unmonitored_outer_area_ha": outer_area,
            },
            "biodiversity_overview": bio,
            "biodiversity_trends": d["temporal"] or {},
            "plantation_status": {
                "total_planted": len(d["plants"]),
                "alive_count": d["alive"],
                "dead_count": d["dead"],
                "unknown_count": d["unknown"],
                "records": plant_inventory,
            },
            "plant_survival": {
                "total_planted": len(d["plants"]),
                "alive_count": d["alive"],
                "dead_count": d["dead"],
                "unknown_count": d["unknown"],
                "known_status_count": d["known_status"],
                "survival_rate": d["survival_pct"],
                "survival_rate_display": _survival_text(d),
                "survival_rate_detail": _survival_detail(d),
            },
            "plantation_progress_impact": {
                # Backwards-compatible payload — kept so API consumers that read this field
                # (and the Phase 14 test suite) continue to work after the report redesign.
                "total_planted_recorded": len(d["plants"]),
                "alive_count": d["alive"],
                "dead_count": d["dead"],
                "unknown_count": d["unknown"],
                "known_status_count": d["known_status"],
                "survival_rate": d["survival_pct"],
                "survival_rate_display": _survival_text(d),
                "summary_statement": f"{len(d['plants'])} planted plants are currently recorded in the system.",
                "status_detail": (
                    f"{d['alive']} of {d['known_status']} plants with known status are currently recorded as Alive."
                    if d["known_status"] > 0 else "Insufficient monitoring data."
                ),
                "mortality_detail": (
                    f"{d['dead']} plants are recorded as Dead and may require field inspection."
                    if d["dead"] > 0 else "0 plants are currently recorded as Dead."
                ),
                "biodiversity_impact_statement": (
                    "Direct biodiversity impact cannot yet be quantified from the available dataset."
                ),
            },
            "zone_analysis": d["zones_analytics"] or {},
            "areas_requiring_action": d["actions"],
            "potential_plantation_assessments": assessments,
            "data_gaps_and_limitations": [
                f"{outer_area} ha of the site lies outside the three active zones — no routine monitoring there.",
                f"{d['ngo_count']} RSWF field uploads so far; growing this is the main way to broaden coverage.",
                f"{d['monitoring_visits']} health-check visits logged; a monthly cadence per plant is the goal.",
                "Some records may still need an expert's confirmation of the species.",
            ],
            "recommended_next_actions": [
                {"action_id": i + 1, **a} for i, a in enumerate(next_actions)
            ],
            "sdg_contributions": _sdg_rows(d),
            "conclusion": (
                "The dashboard turns scattered field photos and planting records into a single, "
                "always-current picture of Van Udyan. Using it means RSWF can direct volunteer "
                "effort, check on plantings in time, and show funders exactly what the work has achieved."
            ),
        }

    @staticmethod
    def get_sdg_report_data() -> Dict[str, Any]:
        d = _common_data()
        return {
            "title": "Van Udyan — Sustainable Development Goals Impact Report",
            "subtitle": "How the RSWF Van Udyan project contributes to the UN SDGs",
            "metadata": {
                "generated_at": d["generated_at"],
                "project_site": "Bavdhan Van Udyan, Pune (Plus Code GQ9J+74Q)",
                "organization": "Reform Social Welfare Foundation (RSWF), Pune",
                "version": "2.0",
            },
            "headline_numbers": {
                "total_recorded_observations": d["biodiversity"].get("total_recorded_observations", 0) if d["biodiversity"] else 0,
                "unique_recorded_taxa_count": d["biodiversity"].get("unique_recorded_taxa_count", 0) if d["biodiversity"] else 0,
                "active_monitoring_zones": 3,
                "planted_plants_tracked": len(d["plants"]),
                "survival_text": _survival_text(d),
                "field_uploads": d["ngo_count"],
                "monitoring_visits": d["monitoring_visits"],
            },
            "sdg_contributions": _sdg_rows(d),
        }

    # ===== PDF generators =====

    @staticmethod
    def generate_conservation_report_pdf() -> bytes:
        payload = ReportService.get_conservation_report_data()
        return _render_pdf(
            payload=payload,
            report_label="Conservation & Plantation Planning Report",
            builder=_build_conservation_story,
        )

    @staticmethod
    def generate_sdg_report_pdf() -> bytes:
        payload = ReportService.get_sdg_report_data()
        return _render_pdf(
            payload=payload,
            report_label="SDG & Project Impact Report",
            builder=_build_sdg_story,
        )


# --------------------------------------------------------------------------------------------
# SDG rows — reused in both reports
# --------------------------------------------------------------------------------------------

def _sdg_rows(d: Dict[str, Any]) -> List[Dict[str, str]]:
    """SDG contributions table rows, written from live data. Species names are not hardcoded."""
    bio = d["biodiversity"] or {}
    total_obs = bio.get("total_recorded_observations", 0)
    total_taxa = bio.get("unique_recorded_taxa_count", 0)
    plant_examples = ", ".join(
        p.get("common_name") or p.get("scientific_name") or p.get("plant_code")
        for p in d["plants"][:3]
    ) or "the trees RSWF has planted"

    return [
        {
            "sdg": "SDG 15 — Life on Land",
            "contribution": "Map, catalogue and protect the plant life of an urban forest patch.",
            "measurable_evidence": f"{total_obs} plant records, {total_taxa} species and taxa, and {len(d['plants'])} tracked plantings.",
        },
        {
            "sdg": "SDG 11 — Sustainable Cities & Communities",
            "contribution": "Document and manage urban green space inside Pune so it is not lost to construction.",
            "measurable_evidence": "3.58 ha of mapped site boundary, with 3 actively monitored work zones.",
        },
        {
            "sdg": "SDG 13 — Climate Action",
            "contribution": "Track whether the trees RSWF plants actually survive and grow, which is what makes the carbon claim real.",
            "measurable_evidence": f"Plant survival: {_survival_text(d)}. Tracked plants include {plant_examples}.",
        },
        {
            "sdg": "SDG 4 — Quality Education",
            "contribution": "Involve students and volunteers in a real conservation dataset through the public dashboard.",
            "measurable_evidence": f"{d['ngo_count']} field photos uploaded by volunteers so far, each spatially verified and open to the public.",
        },
        {
            "sdg": "SDG 17 — Partnerships for the Goals",
            "contribution": "An NGO + academic + open-data partnership that any other park or NGO can reuse.",
            "measurable_evidence": "iNaturalist, OpenStreetMap and Pl@ntNet integrated into one RSWF-owned dashboard, with downloads open to anyone.",
        },
    ]


# --------------------------------------------------------------------------------------------
# PDF rendering
# --------------------------------------------------------------------------------------------

def _render_pdf(
    payload: Dict[str, Any],
    report_label: str,
    builder: Callable[[Dict[str, Any]], List[Any]],
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=22 * mm,  # leaves room for the footer
        title=payload["title"],
        author="RSWF — Van Udyan Biodiversity Platform",
    )

    story = builder(payload)

    def _first(c, d):
        _draw_footer(c, d, report_label)

    def _later(c, d):
        _draw_footer(c, d, report_label)

    doc.build(story, onFirstPage=_first, onLaterPages=_later)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def _build_conservation_story(p: Dict[str, Any]) -> List[Any]:
    story: List[Any] = []
    bio = p.get("biodiversity_overview") or {}
    surv = p.get("plant_survival") or {}
    area = p.get("project_area") or {}
    plant_status = p.get("plantation_status") or {}

    # ----- Header band + KPI strip -----
    story.append(_header_band(p["title"], p["subtitle"], p["metadata"]))
    story.append(Spacer(1, 10))

    story.append(_kpi_strip([
        {"label": "Plant records", "value": bio.get("total_recorded_observations", 0), "note": "Across the whole site"},
        {"label": "Species & taxa", "value": bio.get("unique_recorded_taxa_count", 0), "note": "Distinct plant names"},
        {"label": "Active zones", "value": area.get("active_zones_count", 3), "note": f"≈ {area.get('active_zones_total_area_ha', 0)} ha"},
        {"label": "Plant survival", "value": surv.get("survival_rate_display", "—"), "note": f"{plant_status.get('alive_count', 0)} of {surv.get('known_status_count', 0)} alive"},
    ]))

    # ----- Section 1: Executive summary -----
    story.append(_section_heading(1, "Executive summary"))
    story.append(Paragraph(
        f"Van Udyan is a {area.get('total_boundary_area_ha', 3.58)} ha urban forest patch in Bavdhan, Pune, "
        f"that RSWF monitors through three active work zones (A, B, C). As of this report, the project "
        f"database holds <b>{bio.get('total_recorded_observations', 0)} plant records</b> across "
        f"<b>{bio.get('unique_recorded_taxa_count', 0)} species and taxa</b>, drawn from public iNaturalist "
        f"records (reference baseline), RSWF plantings, volunteer field photos and health-check visits. "
        f"Current plant survival stands at <b>{surv.get('survival_rate_display', '—')}</b>.",
        S_BODY,
    ))
    story.append(Paragraph(
        f"<i>How to read this document.</i> {p['metadata'].get('data_limitations_notice', '')}",
        S_FOOTNOTE,
    ))

    # ----- Section 2: Site & zones -----
    story.append(_section_heading(2, "The site and the active zones"))
    story.append(Paragraph(
        f"The complete site boundary covers <b>{area.get('total_boundary_area_ha', 3.58)} ha</b>. "
        f"RSWF's active work takes place in three zones totalling about "
        f"<b>{area.get('active_zones_total_area_ha', 0.55)} ha</b> — Zone A (0.20 ha), Zone B (0.11 ha) and "
        f"Zone C (0.24 ha). The remaining <b>{area.get('unmonitored_outer_area_ha', 3.02)} ha</b> is "
        f"inside the site boundary but outside the current RSWF work zones.",
        S_BODY,
    ))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Zone-by-zone breakdown", S_SUB))
    zone_rows = _zone_table_rows(p.get("zone_analysis") or {})
    story.append(_data_table(
        headers=["Area", "Records", "Species / taxa", "Planted plants", "Health status"],
        rows=zone_rows,
        col_widths=[36 * mm, 22 * mm, 28 * mm, 26 * mm, 60 * mm],
    ))

    # ----- Section 3: Plantation status (keep heading with inventory table) -----
    plant_block: List[Any] = []
    plant_block.append(_section_heading(3, "RSWF plantation status and health"))
    plant_block.append(Paragraph(
        f"RSWF has <b>{plant_status.get('total_planted', 0)} planted plants</b> registered in the system. "
        f"Of these, <b>{plant_status.get('alive_count', 0)} are recorded as alive</b>, "
        f"{plant_status.get('dead_count', 0)} as dead and {plant_status.get('unknown_count', 0)} as "
        f"unknown. Health is logged in the <i>Monitoring Zones</i> and <i>Manage Plantations</i> "
        f"sections of the dashboard, with the full visit history preserved for each plant.",
        S_BODY,
    ))
    inv_rows: List[List[Any]] = []
    for r in plant_status.get("records", []):
        kind = {"alive": "ok", "dead": "danger", "unknown": "warn"}.get(
            (r.get("status") or "").lower(), "neutral",
        )
        inv_rows.append([
            r.get("plant_code") or "—",
            r.get("scientific_name") or r.get("common_name") or "Unspecified",
            r.get("zone_code") or "Outside zones",
            r.get("planted_on") or "—",
            _status_pill(r.get("status") or "Unknown", kind),
        ])
    if inv_rows:
        plant_block.append(Spacer(1, 4))
        plant_block.append(_data_table(
            headers=["Plant code", "Species", "Zone", "Planted on", "Current status"],
            rows=inv_rows,
            col_widths=[22 * mm, 60 * mm, 20 * mm, 24 * mm, 46 * mm],
        ))
    else:
        plant_block.append(Paragraph(
            "<i>No planted plants are registered yet. Use the dashboard's <b>Manage Plantations</b> tab to add RSWF plantings as they happen.</i>",
            S_FOOTNOTE,
        ))
    story.append(KeepTogether(plant_block))

    # ----- Section 4: Areas needing action -----
    story.append(_section_heading(4, "Areas needing attention"))
    action_rows: List[List[Any]] = []
    for a in p.get("areas_requiring_action", []):
        level = (a.get("priority_level") or "").upper()
        kind = {"HIGH": "danger", "MEDIUM": "warn", "LOW": "neutral"}.get(level, "neutral")
        priority_label = (a.get("priority_type") or "").replace("_", " ").title()
        area_name = "Outside active zones" if a.get("area_code") == "OUTSIDE_ACTIVE_ZONES" else (a.get("area_code") or "—")
        action_rows.append([
            area_name,
            _status_pill(priority_label or level or "Monitor", kind),
            a.get("reason") or "",
            a.get("recommended_action") or "",
        ])
    if action_rows:
        story.append(_data_table(
            headers=["Area", "Priority", "What the data shows", "Suggested next step"],
            rows=action_rows,
            col_widths=[32 * mm, 24 * mm, 56 * mm, 60 * mm],
        ))
    else:
        story.append(Paragraph("No specific action is flagged by current data.", S_BODY))

    # ----- Section 5: Potential plantation assessments -----
    assessments = p.get("potential_plantation_assessments") or []
    if assessments:
        story.append(_section_heading(5, "Where to look before the next plantings"))
        for a in assessments:
            area = "Outside active zones" if a.get("area_code") == "OUTSIDE_ACTIVE_ZONES" else a.get("area_code")
            story.append(Paragraph(
                f"• <b>{area} — {a.get('assessment_category', '')}:</b> {a.get('indicator', '')} "
                f"<i>{a.get('note', '')}</i>",
                S_BODY,
            ))

    # ----- Section 6: Next actions -----
    story.append(_section_heading(6, "Recommended next actions for RSWF"))
    for na in p.get("recommended_next_actions", []):
        story.append(Paragraph(
            f"<b>{na.get('action_id', '')}. {na.get('title', '')}.</b> {na.get('description', '')}",
            S_BODY,
        ))

    # ----- Section 7: Data limitations -----
    story.append(_section_heading(7, "Data gaps and limitations"))
    for g in p.get("data_gaps_and_limitations", []):
        story.append(Paragraph(f"• {g}", S_BODY))

    # ----- Section 8: Conclusion + sources -----
    story.append(_section_heading(8, "In closing"))
    story.append(Paragraph(p.get("conclusion", ""), S_BODY))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=0.4, color=RULE))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Data sources</b>", S_SUB))
    for src in p["metadata"].get("data_sources", []):
        story.append(Paragraph(f"• {src}", S_BODY_SMALL))

    return story


def _zone_table_rows(zone_analysis: Dict[str, Any]) -> List[List[Any]]:
    """
    Builds the zone-by-zone row list. Fixes the earlier bug where OUTSIDE_ACTIVE_ZONES
    appeared twice (once from analytics, once from a manual appended row).
    """
    rows: List[List[Any]] = []
    zones_dict = zone_analysis.get("zones", {})
    zone_list = list(zones_dict.values()) if isinstance(zones_dict, dict) else zones_dict
    for z in zone_list:
        code = z.get("zone_code") or ""
        label = "Outside active zones" if code == "OUTSIDE_ACTIVE_ZONES" else code
        st = z.get("plant_status_counts", {}) or {}
        status_text = (
            f"{st.get('Alive', 0)} alive · {st.get('Dead', 0)} dead · {st.get('Unknown', 0)} unknown"
        )
        rows.append([
            label,
            z.get("recorded_observations_count", 0),
            z.get("unique_recorded_taxa_count", 0),
            z.get("planted_plants_count", 0),
            status_text,
        ])
    return rows


def _build_sdg_story(p: Dict[str, Any]) -> List[Any]:
    story: List[Any] = []
    head = p["headline_numbers"]

    story.append(_header_band(p["title"], p["subtitle"], p["metadata"]))
    story.append(Spacer(1, 10))

    story.append(_kpi_strip([
        {"label": "Plant records", "value": head["total_recorded_observations"]},
        {"label": "Species & taxa", "value": head["unique_recorded_taxa_count"]},
        {"label": "Tracked plantings", "value": head["planted_plants_tracked"]},
        {"label": "Volunteer uploads", "value": head["field_uploads"]},
    ]))

    story.append(_section_heading(1, "What this report shows"))
    story.append(Paragraph(
        "The RSWF Van Udyan project protects, maps and plants trees in a 3.58 ha urban forest patch "
        "in Bavdhan, Pune. This report connects that work to the UN Sustainable Development Goals, "
        "using live numbers from the project dashboard as evidence.",
        S_BODY,
    ))
    story.append(Paragraph(
        f"Current plant survival: <b>{head['survival_text']}</b>. "
        f"Field health-check visits logged so far: <b>{head['monitoring_visits']}</b>.",
        S_BODY,
    ))

    story.append(_section_heading(2, "Contribution to each SDG"))
    sdg_rows = [
        [s["sdg"], s["contribution"], s["measurable_evidence"]]
        for s in p.get("sdg_contributions", [])
    ]
    story.append(_data_table(
        headers=["SDG target", "What the project does", "Measurable evidence"],
        rows=sdg_rows,
        col_widths=[58 * mm, 58 * mm, 55 * mm],
    ))

    story.append(_section_heading(3, "Why these numbers are honest"))
    story.append(Paragraph(
        "Every number in this report comes from the project database and updates whenever a volunteer "
        "uploads a photo or an RSWF staff member logs a visit. We do not inflate counts: an area with "
        "no records means no one has recorded there yet, not that it is empty. The dashboard is open "
        "to the public at the project URL so anyone can verify the figures.",
        S_BODY,
    ))

    story.append(_section_heading(4, "What RSWF plans next"))
    for item in [
        "Grow the number of volunteer-contributed field photos through monthly bio-blitz events.",
        "Record a routine monthly health check for every planted plant.",
        "Extend the active zone coverage to parts of the site that are still unmonitored.",
        "Publish an annual plant-survival report using this document as the template.",
    ]:
        story.append(Paragraph(f"• {item}", S_BODY))

    return story
