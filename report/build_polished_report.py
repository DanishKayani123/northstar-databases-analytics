from __future__ import annotations

import csv
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path("/Users/danishkayani/Documents/Codex/2026-05-23/files-mentioned-by-the-user-msg")
REPORT_DIR = ROOT / "report"
ASSETS_DIR = REPORT_DIR / "assets"
ARTIFACTS_DIR = ROOT / "artifacts" / "outputs"
OUTPUT_DOCX = REPORT_DIR / "northstar_assignment_report_polished.docx"


ACCENT = RGBColor(176, 83, 16)
TEXT = RGBColor(31, 41, 55)
MUTED = RGBColor(95, 99, 104)
LIGHT = RGBColor(245, 239, 230)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def set_page_number(paragraph):
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")

    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"

    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")

    run._r.append(fld_char1)
    run._r.append(instr_text)
    run._r.append(fld_char2)


def style_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.9)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    normal.font.color.rgb = TEXT
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15

    for name, size, bold, color in [
        ("Title", 22, True, TEXT),
        ("Subtitle", 12, False, MUTED),
        ("Heading 1", 15, True, ACCENT),
        ("Heading 2", 12.5, True, TEXT),
        ("Heading 3", 11.5, True, TEXT),
    ]:
        style = styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = bold
        style.font.color.rgb = color
        style.paragraph_format.space_before = Pt(10 if name != "Title" else 0)
        style.paragraph_format.space_after = Pt(6)


def add_footer(section) -> None:
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("NorthStar Assignment Report | Page ")
    run.font.name = "Arial"
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED
    set_page_number(p)


def add_cover_page(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.space_after = Pt(0)
    p.add_run("\n" * 2)

    title = doc.add_paragraph()
    title.style = "Title"
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("Operational Diagnosis and Integrated Database Redesign for NorthStar Urban Mobility and Logistics")

    sub = doc.add_paragraph()
    sub.style = "Subtitle"
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run("Databases and Analytics Coursework Assignment")

    doc.add_paragraph()
    meta = [
        "Student Name: [Add your name]",
        "Student ID: [Add your student ID]",
        "Module: CP60056E Databases and Analytics",
        "Academic Year: 2025-2026",
        "Case Study: NorthStar Urban Mobility and Logistics",
        "GitHub Repository: [Add GitHub repo link after upload]",
        "Submission Date: [Add submission date]"
    ]
    for line in meta:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(line)
        r.font.name = "Arial"
        r.font.size = Pt(11)

    doc.add_paragraph()
    box = doc.add_table(rows=1, cols=1)
    box.autofit = False
    box.columns[0].width = Inches(6.0)
    cell = box.cell(0, 0)
    cell.text = (
        "This report analyses the NorthStar case study using SQL in R, R analytics, "
        "Python data processing, and a MongoDB-style redesign. It focuses on operational "
        "reliability, customer experience, and data architecture improvement."
    )
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "F5EFE6")
    tc_pr.append(shd)

    doc.add_page_break()


def add_table_of_contents(doc: Document) -> None:
    h = doc.add_paragraph("Table of Contents", style="Heading 1")
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    entries = [
        "Abstract",
        "Chapter 1: Introduction",
        "Chapter 2: Data Preparation and Analytical Method",
        "Chapter 3: SQL in R and Relational Findings",
        "Chapter 4: Analytics, Python Processing, and Interpretation",
        "Chapter 5: MongoDB Design and Query Optimisation",
        "Chapter 6: Recommendations and Conclusion",
        "Appendix A: Evidence Files Generated",
    ]
    for entry in entries:
        p = doc.add_paragraph(style="Normal")
        p.paragraph_format.left_indent = Inches(0.15)
        r = p.add_run(entry)
        r.font.name = "Arial"
        r.font.size = Pt(11)
    doc.add_page_break()


def add_abstract(doc: Document) -> None:
    doc.add_paragraph("Abstract", style="Heading 1")
    abstract = (
        "This report investigates the operational, customer-service, and data-management problems "
        "present in the NorthStar Urban Mobility and Logistics case study. The dataset combines "
        "structured operational files with more flexible event and complaint records, making it a "
        "strong example of a business whose reporting model has not kept pace with its data growth. "
        "The analysis was carried out through relational querying, R-oriented analytics, Python-led "
        "feature engineering, and a MongoDB-oriented redesign for semi-structured records. The key "
        "findings show three critical issues: a fragmented order-to-delivery pipeline with 300 orders "
        "missing delivery records, persistent service underperformance in the central operating zone, "
        "and strong risk signals tied to missing proof of completion and vehicles already marked InRepair. "
        "The report concludes that NorthStar requires a hybrid architecture in which structured reporting "
        "remains relational, while customer cases, exception histories, and app event sequences are "
        "remodelled into a document-based store to support more realistic operational analysis."
    )
    doc.add_paragraph(abstract)


def add_intro(doc: Document) -> None:
    doc.add_paragraph("Chapter 1: Introduction", style="Heading 1")
    doc.add_paragraph("1.1 Background", style="Heading 2")
    doc.add_paragraph(
        "NorthStar Urban Mobility and Logistics operates across multiple UK city zones and combines "
        "passenger transport, parcel handling, warehouse dispatch, charging infrastructure, and mobile-platform services. "
        "The case study presents a business that has grown quickly but now suffers from fragmented reporting, "
        "inconsistent performance, and poor integration between structured operational data and newer event-driven records."
    )
    doc.add_paragraph("1.2 Aim", style="Heading 2")
    doc.add_paragraph(
        "The aim of this assignment is to identify NorthStar's most significant operational and analytical failures, "
        "analyse the evidence using appropriate database and analytics methods, and propose a justified redesign that "
        "uses both relational processing and MongoDB-based document modelling."
    )
    doc.add_paragraph("1.3 Objectives", style="Heading 2")
    objectives = [
        "Use SQL within an R-oriented workflow to identify reliability, hub, and pipeline issues.",
        "Apply analytics techniques to interpret complaint, latency, and performance patterns.",
        "Use Python to clean inconsistent data and engineer cross-file analytical features.",
        "Design a MongoDB-oriented document model for complaints, cases, events, and delivery exceptions.",
        "Recommend indexing and optimisation strategies for both the relational and document-based parts of the solution.",
    ]
    for item in objectives:
        doc.add_paragraph(item, style="List Bullet")


def add_methodology(doc: Document) -> None:
    quality = read_csv_rows(ARTIFACTS_DIR / "dataset_quality_summary.csv")
    qmap = {row["metric"]: row["value"] for row in quality}

    doc.add_paragraph("Chapter 2: Data Preparation and Analytical Method", style="Heading 1")
    doc.add_paragraph("2.1 Dataset Overview", style="Heading 2")
    doc.add_paragraph(
        "The NorthStar dataset contains orders, deliveries, customers, drivers, vehicles, hubs, complaints, "
        "incidents, and app events. The data was analysed as an integrated business system rather than as isolated files, "
        "because the case study explicitly states that NorthStar's failures arise from disconnected views of the same operations."
    )

    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "Data quality issue"
    hdr[1].text = "Count"
    for key, label in [
        ("customers_preferred_channel_missing", "Missing customer preferred channel"),
        ("orders_booking_channel_missing", "Missing booking channel"),
        ("deliveries_completed_timestamp_missing", "Missing delivery completion timestamp"),
        ("deliveries_rating_missing", "Missing post-delivery rating"),
        ("orders_without_delivery_record", "Orders without delivery record"),
    ]:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = qmap[key]

    doc.add_paragraph("2.2 Cleaning and Standardisation", style="Heading 2")
    doc.add_paragraph(
        "Before analysis, location categories were standardised across files because values such as North, NORTH, north, "
        "Central, CENTRAL, and Ctr would otherwise fragment the results. Missing values were retained where analytically useful, "
        "because absence itself was a signal in some fields such as proof-of-completion and delivery completion timestamps."
    )
    doc.add_paragraph("2.3 Analytical Workflow", style="Heading 2")
    doc.add_paragraph(
        "The workflow followed four stages. First, relational files were joined and grouped using SQL in an R-style environment. "
        "Second, customer and service patterns were interpreted using analytics summaries. Third, Python was used to engineer new features "
        "including completion hours, cleaned zones, profitability proxies, and grouped route-override bands. Finally, the semi-structured "
        "problem domain was remodelled into a document-oriented MongoDB design."
    )


def add_image(doc: Document, path: Path, width: float, caption: str) -> None:
    doc.add_picture(str(path), width=Inches(width))
    p = doc.paragraphs[-1]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp = doc.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cp.add_run(caption)
    run.italic = True
    run.font.name = "Arial"
    run.font.size = Pt(9)
    run.font.color.rgb = MUTED


def add_sql_r_section(doc: Document) -> None:
    doc.add_paragraph("Chapter 3: SQL in R and Relational Findings", style="Heading 1")
    doc.add_paragraph("3.1 Relational Querying Strategy", style="Heading 2")
    doc.add_paragraph(
        "The SQL component focused on operational reliability, missing order-to-delivery links, and hub performance. "
        "This was appropriate because the core operational records remain highly structured and lend themselves to grouped queries, joins, and filters."
    )
    doc.add_paragraph("3.2 Key Findings", style="Heading 2")
    findings = [
        "300 of 1,250 orders had no delivery record, indicating a major process break between order intake and dispatch visibility.",
        "Central Core had the highest non-on-time delivery share at 41.7%, while East Dock performed best at 28.6%.",
        "The Central zone had only 60.5% on-time delivery and 20.2% failed delivery, making it the weakest area in the network.",
        "Missing orders were spread across service types rather than concentrated in only one operational category.",
    ]
    for item in findings:
        doc.add_paragraph(item, style="List Bullet")

    add_image(
        doc,
        ASSETS_DIR / "hub_non_ontime_risk.png",
        6.2,
        "Figure 1. Hub-level reliability risk based on delayed or failed deliveries.",
    )
    add_image(
        doc,
        ASSETS_DIR / "orders_without_delivery_by_service.png",
        6.2,
        "Figure 2. Orders with no linked delivery record by service type.",
    )
    add_image(
        doc,
        ASSETS_DIR / "sql_r_notebook_crop.png",
        6.0,
        "Figure 3. Executed SQL in R notebook showing grouped hub-risk and missing-order outputs.",
    )


def add_analytics_section(doc: Document) -> None:
    doc.add_paragraph("Chapter 4: Analytics, Python Processing, and Interpretation", style="Heading 1")
    doc.add_paragraph("4.1 Customer Experience and Complaint Patterns", style="Heading 2")
    doc.add_paragraph(
        "Customer dissatisfaction is not explained by failed deliveries alone. Delay, AppIssue, DriverBehaviour, and MissedPickup complaints "
        "all appear against records that were operationally marked OnTime. This supports the case study's claim that NorthStar's systems record "
        "service closure differently from how customers experience the service."
    )
    doc.add_paragraph("4.2 Feature Engineering and Risk Signals", style="Heading 2")
    doc.add_paragraph(
        "Python was used to engineer cleaned zones, completion hours, route-override bands, joined complaint totals, and a direct profitability proxy "
        "calculated from order value, direct delivery cost, and compensation amounts. These features exposed much stronger patterns than the raw files alone."
    )
    risk_table = doc.add_table(rows=1, cols=4)
    risk_table.style = "Table Grid"
    hdr = risk_table.rows[0].cells
    hdr[0].text = "Condition"
    hdr[1].text = "Delayed %"
    hdr[2].text = "Failed %"
    hdr[3].text = "Average rating"
    for row_data in [
        ("Proof present", "17.8", "12.3", "3.92"),
        ("Proof missing", "65.2", "34.8", "3.17"),
    ]:
        row = risk_table.add_row().cells
        for idx, val in enumerate(row_data):
            row[idx].text = val

    doc.add_paragraph("4.3 Asset and Maintenance Evidence", style="Heading 2")
    doc.add_paragraph(
        "Vehicles marked InRepair performed substantially worse than Active or Scheduled vehicles. This strongly suggests that NorthStar's maintenance "
        "state is not being incorporated into dispatch control as effectively as it should be."
    )
    add_image(
        doc,
        ASSETS_DIR / "maintenance_failed_rate.png",
        6.0,
        "Figure 4. Delivery failure rate by maintenance status.",
    )
    add_image(
        doc,
        ASSETS_DIR / "python_mongo_notebook_crop.png",
        6.0,
        "Figure 5. Executed Python notebook showing analytical feature engineering and MongoDB-oriented workflow.",
    )


def add_mongo_section(doc: Document) -> None:
    doc.add_paragraph("Chapter 5: MongoDB Design and Query Optimisation", style="Heading 1")
    doc.add_paragraph("5.1 MongoDB Design Rationale", style="Heading 2")
    doc.add_paragraph(
        "NorthStar's app events, complaint histories, exception records, and evolving case timelines are not well suited to a rigid relational design. "
        "A document model is more appropriate where related nested histories need to stay together and where records evolve over time."
    )
    doc.add_paragraph("5.2 Proposed Collections", style="Heading 2")
    collections = [
        "customer_cases for customer, order, complaint, app-event, and incident history in one operational document.",
        "service_orders for order-level structured detail and lightweight dispatch references.",
        "delivery_events for delivery timelines, route overrides, proof records, and incident snapshots.",
        "asset_health for vehicle state, maintenance history, and recent linked delivery activity.",
    ]
    for item in collections:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_paragraph("5.3 Indexing Strategy", style="Heading 2")
    idx_table = doc.add_table(rows=1, cols=2)
    idx_table.style = "Table Grid"
    hdr = idx_table.rows[0].cells
    hdr[0].text = "Index"
    hdr[1].text = "Purpose"
    rows = [
        ("customer_cases(order_id)", "Fast lookup of a case by operational order identifier."),
        ("customer_cases(customer.customer_id, case_status)", "Open or closed customer cases by customer."),
        ("customer_cases(delivery_summary.hub_id, delivery_summary.delivery_status)", "Delayed and failed cases by hub."),
        ("delivery_events(vehicle_id, maintenance_status)", "Exception analysis by vehicle and maintenance state."),
    ]
    for index_name, purpose in rows:
        row = idx_table.add_row().cells
        row[0].text = index_name
        row[1].text = purpose

    doc.add_paragraph("5.4 Explain-Plan Logic", style="Heading 2")
    doc.add_paragraph(
        "In a live MongoDB Atlas environment, explain plans should be captured before and after index creation to demonstrate reduced collection scans, "
        "fewer documents examined, and lower execution time. In this workspace, the notebook was executed with a MongoDB-compatible fallback client, so the "
        "Atlas logic is demonstrated but explain statistics still need a live cluster connection if the tutor requires them."
    )


def add_recommendations(doc: Document) -> None:
    doc.add_paragraph("Chapter 6: Recommendations and Conclusion", style="Heading 1")
    doc.add_paragraph("6.1 Recommendations", style="Heading 2")
    recs = [
        "Investigate the 300 orders with no delivery record as a priority control failure.",
        "Intervene first in the central hub network, particularly Central Core and Midtown Relay.",
        "Treat missing proof of completion as a formal exception trigger rather than a passive data field.",
        "Prevent or justify the operational use of vehicles already marked InRepair.",
        "Deploy a unified customer-case model so complaint, event, and delivery records are no longer analysed in isolation.",
        "Monitor app latency as part of service quality, especially for Airport and Central interactions.",
    ]
    for item in recs:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_paragraph("6.2 Conclusion", style="Heading 2")
    doc.add_paragraph(
        "The NorthStar case is not a simple late-delivery problem. It is a broader visibility and integration problem in which operational truth is split "
        "across multiple systems. SQL in R was appropriate for structured operational analysis, Python was effective for data cleaning and feature engineering, "
        "and MongoDB is the correct target for nested, evolving histories such as customer cases and app-event chains. The final recommendation is therefore a "
        "hybrid architecture: retain relational reporting for structured records, strengthen data-quality control through Python workflows, and redesign semi-structured "
        "operational histories into MongoDB documents for better decision support."
    )


def add_appendix(doc: Document) -> None:
    doc.add_paragraph("Appendix A: Evidence Files Generated", style="Heading 1")
    items = [
        "Executed SQL in R notebook HTML and screenshot.",
        "Executed Python and MongoDB notebook HTML and screenshot.",
        "CSV summary outputs for hub risk, complaints, zone performance, and profitability.",
        "Rendered chart images inserted into the report.",
        "Local Git repository containing the assignment pack and execution outputs.",
    ]
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def main() -> None:
    doc = Document()
    style_document(doc)
    add_footer(doc.sections[0])
    add_cover_page(doc)
    add_footer(doc.sections[0])
    add_table_of_contents(doc)
    add_abstract(doc)
    doc.add_page_break()
    add_intro(doc)
    add_methodology(doc)
    add_sql_r_section(doc)
    add_analytics_section(doc)
    add_mongo_section(doc)
    add_recommendations(doc)
    add_appendix(doc)
    doc.save(OUTPUT_DOCX)


if __name__ == "__main__":
    main()
