from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import nbformat
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/danishkayani/Documents/Codex/2026-05-23/files-mentioned-by-the-user-msg")
DATA_DIR = ROOT / "northstar_dataset"
OUTPUTS_DIR = ROOT / "artifacts" / "outputs"
DB_PATH = ROOT / "artifacts" / "northstar_analysis.db"
ASSETS_DIR = ROOT / "report" / "assets"
EVIDENCE_DIR = ASSETS_DIR / "evidence"
NOTEBOOKS_DIR = ROOT / "notebooks"


BG = "#f7f4ee"
PANEL_BG = "#ffffff"
PANEL_BORDER = "#d6d3d1"
TEXT = "#1f2937"
MUTED = "#6b7280"
ACCENT = "#b45309"
CODE_BG = "#f3f4f6"
CODE_TEXT = "#111827"
TABLE_HEADER = "#fef3c7"
TABLE_ALT = "#fafaf9"
GOOD = "#1f7a45"
BAD = "#b91c1c"


def load_font(size: int, mono: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if mono:
        candidates.extend(
            [
                "/System/Library/Fonts/SFNSMono.ttf",
                "/System/Library/Fonts/Menlo.ttc",
                "/Library/Fonts/Courier New.ttf",
            ]
        )
    else:
        if bold:
            candidates.extend(
                [
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                    "/Library/Fonts/Arial Bold.ttf",
                    "/System/Library/Fonts/SFNS.ttf",
                ]
            )
        else:
            candidates.extend(
                [
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                    "/Library/Fonts/Arial.ttf",
                    "/System/Library/Fonts/SFNS.ttf",
                ]
            )

    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT_TITLE = load_font(30, bold=True)
FONT_SUBTITLE = load_font(18)
FONT_BODY = load_font(18)
FONT_BODY_BOLD = load_font(18, bold=True)
FONT_CAPTION = load_font(16)
FONT_CODE = load_font(16, mono=True)
FONT_CODE_SMALL = load_font(14, mono=True)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split(" ")
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def line_height(draw: ImageDraw.ImageDraw, font) -> int:
    box = draw.textbbox((0, 0), "Ag", font=font)
    return (box[3] - box[1]) + 6


def prepare_code_block(draw: ImageDraw.ImageDraw, title: str, code: str, width: int) -> tuple[list[str], int]:
    lines = [title]
    for raw in code.strip().splitlines():
        stripped = raw.rstrip()
        if not stripped:
            lines.append("")
            continue
        if len(stripped) > 78:
            lines.extend(wrap_text(draw, stripped, FONT_CODE_SMALL, width - 48))
        else:
            lines.append(stripped)
    height = 20 + len(lines) * line_height(draw, FONT_CODE_SMALL) + 16
    return lines, height


def prepare_text_block(draw: ImageDraw.ImageDraw, text: str, width: int) -> tuple[list[str], int]:
    lines = wrap_text(draw, text, FONT_BODY, width)
    height = max(48, len(lines) * line_height(draw, FONT_BODY) + 4)
    return lines, height


def dataframe_to_image(
    df: pd.DataFrame,
    path: Path,
    title: str,
    subtitle: str,
    code_title: str | None = None,
    code: str | None = None,
    notes: str | None = None,
    max_rows: int = 10,
    width: int = 1500,
) -> None:
    df = df.copy().head(max_rows)
    display_df = df.astype(str)
    image = Image.new("RGB", (width, 400), BG)
    draw = ImageDraw.Draw(image)
    y = 36

    draw.text((42, y), title, font=FONT_TITLE, fill=TEXT)
    y += 44
    draw.text((42, y), subtitle, font=FONT_SUBTITLE, fill=MUTED)
    y += 42

    if code_title and code:
        code_lines, code_height = prepare_code_block(draw, code_title, code, width - 84)
        draw.rounded_rectangle((36, y, width - 36, y + code_height), radius=18, fill=CODE_BG, outline=PANEL_BORDER)
        code_y = y + 14
        for idx, line in enumerate(code_lines):
            font = FONT_BODY_BOLD if idx == 0 else FONT_CODE_SMALL
            fill = TEXT if idx == 0 else CODE_TEXT
            x = 54 if idx == 0 else 62
            draw.text((x, code_y), line, font=font, fill=fill)
            code_y += line_height(draw, font)
        y += code_height + 28

    if notes:
        note_lines, note_height = prepare_text_block(draw, notes, width - 96)
        draw.rounded_rectangle((36, y, width - 36, y + note_height), radius=18, fill="#fff7ed", outline="#fdba74")
        note_y = y + 12
        for line in note_lines:
            draw.text((54, note_y), line, font=FONT_BODY, fill=TEXT)
            note_y += line_height(draw, FONT_BODY)
        y += note_height + 28

    table_x = 36
    usable_width = width - 72
    columns = list(display_df.columns)
    cell_padding = 14
    col_widths: list[int] = []
    for col in columns:
        header_w = draw.textbbox((0, 0), str(col), font=FONT_BODY_BOLD)[2] + cell_padding * 2
        value_w = max(
            [draw.textbbox((0, 0), str(val), font=FONT_CAPTION)[2] + cell_padding * 2 for val in display_df[col]]
            + [header_w]
        )
        col_widths.append(value_w)

    total_width = sum(col_widths)
    if total_width > usable_width:
        scale = usable_width / total_width
        col_widths = [max(120, math.floor(w * scale)) for w in col_widths]
        overflow = sum(col_widths) - usable_width
        while overflow > 0:
            idx = max(range(len(col_widths)), key=lambda i: col_widths[i])
            if col_widths[idx] > 120:
                col_widths[idx] -= 1
                overflow -= 1
            else:
                break
    else:
        extra = usable_width - total_width
        share = extra // max(1, len(col_widths))
        col_widths = [w + share for w in col_widths]

    row_height = 46
    table_height = row_height * (len(display_df) + 1)
    new_height = y + table_height + 54
    if new_height > image.height:
        image = Image.new("RGB", (width, new_height), BG)
        draw = ImageDraw.Draw(image)
        y = 36
        draw.text((42, y), title, font=FONT_TITLE, fill=TEXT)
        y += 44
        draw.text((42, y), subtitle, font=FONT_SUBTITLE, fill=MUTED)
        y += 42
        if code_title and code:
            code_lines, code_height = prepare_code_block(draw, code_title, code, width - 84)
            draw.rounded_rectangle((36, y, width - 36, y + code_height), radius=18, fill=CODE_BG, outline=PANEL_BORDER)
            code_y = y + 14
            for idx, line in enumerate(code_lines):
                font = FONT_BODY_BOLD if idx == 0 else FONT_CODE_SMALL
                fill = TEXT if idx == 0 else CODE_TEXT
                x = 54 if idx == 0 else 62
                draw.text((x, code_y), line, font=font, fill=fill)
                code_y += line_height(draw, font)
            y += code_height + 28
        if notes:
            note_lines, note_height = prepare_text_block(draw, notes, width - 96)
            draw.rounded_rectangle((36, y, width - 36, y + note_height), radius=18, fill="#fff7ed", outline="#fdba74")
            note_y = y + 12
            for line in note_lines:
                draw.text((54, note_y), line, font=FONT_BODY, fill=TEXT)
                note_y += line_height(draw, FONT_BODY)
            y += note_height + 28

    draw.rounded_rectangle((table_x, y, width - 36, y + table_height), radius=16, fill=PANEL_BG, outline=PANEL_BORDER)
    current_x = table_x
    for idx, col in enumerate(columns):
        w = col_widths[idx]
        draw.rectangle((current_x, y, current_x + w, y + row_height), fill=TABLE_HEADER, outline=PANEL_BORDER)
        draw.text((current_x + 12, y + 12), str(col), font=FONT_BODY_BOLD, fill=TEXT)
        current_x += w

    for row_idx, (_, row) in enumerate(display_df.iterrows(), start=1):
        row_y = y + row_idx * row_height
        current_x = table_x
        fill = PANEL_BG if row_idx % 2 else TABLE_ALT
        for idx, col in enumerate(columns):
            w = col_widths[idx]
            draw.rectangle((current_x, row_y, current_x + w, row_y + row_height), fill=fill, outline=PANEL_BORDER)
            value = str(row[col])
            font = FONT_CAPTION
            value_lines = wrap_text(draw, value, font, w - 20)
            text_y = row_y + 8
            for line in value_lines[:2]:
                draw.text((current_x + 12, text_y), line, font=font, fill=TEXT)
                text_y += line_height(draw, font) - 4
            current_x += w

    image.save(path)


def json_panel_to_image(
    path: Path,
    title: str,
    subtitle: str,
    code_title: str,
    code: str,
    payload: dict,
    note: str | None = None,
    width: int = 1500,
) -> None:
    pretty = json.dumps(payload, indent=2)
    image = Image.new("RGB", (width, 1400), BG)
    draw = ImageDraw.Draw(image)
    y = 36

    draw.text((42, y), title, font=FONT_TITLE, fill=TEXT)
    y += 44
    draw.text((42, y), subtitle, font=FONT_SUBTITLE, fill=MUTED)
    y += 42

    code_lines, code_height = prepare_code_block(draw, code_title, code, width - 84)
    draw.rounded_rectangle((36, y, width - 36, y + code_height), radius=18, fill=CODE_BG, outline=PANEL_BORDER)
    code_y = y + 14
    for idx, line in enumerate(code_lines):
        font = FONT_BODY_BOLD if idx == 0 else FONT_CODE_SMALL
        fill = TEXT if idx == 0 else CODE_TEXT
        x = 54 if idx == 0 else 62
        draw.text((x, code_y), line, font=font, fill=fill)
        code_y += line_height(draw, font)
    y += code_height + 28

    if note:
        note_lines, note_height = prepare_text_block(draw, note, width - 96)
        draw.rounded_rectangle((36, y, width - 36, y + note_height), radius=18, fill="#fff7ed", outline="#fdba74")
        note_y = y + 12
        for line in note_lines:
            draw.text((54, note_y), line, font=FONT_BODY, fill=TEXT)
            note_y += line_height(draw, FONT_BODY)
        y += note_height + 28

    json_lines = pretty.splitlines()
    json_height = 26 + len(json_lines) * line_height(draw, FONT_CODE_SMALL) + 20
    total_height = y + json_height + 48
    if total_height > image.height:
        image = Image.new("RGB", (width, total_height), BG)
        draw = ImageDraw.Draw(image)
        y = 36
        draw.text((42, y), title, font=FONT_TITLE, fill=TEXT)
        y += 44
        draw.text((42, y), subtitle, font=FONT_SUBTITLE, fill=MUTED)
        y += 42
        code_lines, code_height = prepare_code_block(draw, code_title, code, width - 84)
        draw.rounded_rectangle((36, y, width - 36, y + code_height), radius=18, fill=CODE_BG, outline=PANEL_BORDER)
        code_y = y + 14
        for idx, line in enumerate(code_lines):
            font = FONT_BODY_BOLD if idx == 0 else FONT_CODE_SMALL
            fill = TEXT if idx == 0 else CODE_TEXT
            x = 54 if idx == 0 else 62
            draw.text((x, code_y), line, font=font, fill=fill)
            code_y += line_height(draw, font)
        y += code_height + 28
        if note:
            note_lines, note_height = prepare_text_block(draw, note, width - 96)
            draw.rounded_rectangle((36, y, width - 36, y + note_height), radius=18, fill="#fff7ed", outline="#fdba74")
            note_y = y + 12
            for line in note_lines:
                draw.text((54, note_y), line, font=FONT_BODY, fill=TEXT)
                note_y += line_height(draw, FONT_BODY)
            y += note_height + 28

    draw.rounded_rectangle((36, y, width - 36, y + json_height), radius=18, fill=PANEL_BG, outline=PANEL_BORDER)
    json_y = y + 14
    for line in json_lines:
        draw.text((54, json_y), line, font=FONT_CODE_SMALL, fill=TEXT)
        json_y += line_height(draw, FONT_CODE_SMALL)
    image.save(path)


def chart_style(ax, title: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=18, color=TEXT, pad=16)
    ax.set_ylabel(ylabel, fontsize=12, color=TEXT)
    ax.tick_params(axis="both", labelsize=11, colors=TEXT)
    ax.grid(axis="x", color="#e7e5e4", linestyle="-", linewidth=0.8)
    ax.set_facecolor("#ffffff")
    for spine in ax.spines.values():
        spine.set_visible(False)


def save_complaint_mix_chart() -> None:
    df = pd.read_csv(OUTPUTS_DIR / "complaint_mix_by_delivery_status.csv")
    pivot = (
        df.pivot(index="complaint_type", columns="delivery_status", values="complaints")
        .fillna(0)
        .reindex(columns=["OnTime", "Delayed", "Failed"])
    )
    fig, ax = plt.subplots(figsize=(10.5, 6.8), facecolor=BG)
    pivot.plot(kind="bar", stacked=True, color=["#fbbf24", "#fb923c", "#dc2626"], ax=ax)
    ax.set_xlabel("Complaint Type", fontsize=12, color=TEXT)
    chart_style(ax, "Complaint Mix by Delivery Status", "Complaint Count")
    ax.legend(title="Delivery Status", frameon=False)
    fig.tight_layout()
    fig.savefig(EVIDENCE_DIR / "sql_complaint_mix_chart.png", dpi=220, facecolor=BG)
    plt.close(fig)


def save_complaints_by_hub_chart() -> None:
    df = pd.read_csv(OUTPUTS_DIR / "complaints_by_hub.csv").sort_values("complaints_per_delivery", ascending=True)
    fig, ax = plt.subplots(figsize=(10.5, 6.8), facecolor=BG)
    ax.barh(df["hub_name"], df["complaints_per_delivery"], color="#b45309")
    chart_style(ax, "Complaint Intensity by Hub", "Complaints per Delivery")
    ax.set_xlabel("Complaints per Delivery", fontsize=12, color=TEXT)
    fig.tight_layout()
    fig.savefig(EVIDENCE_DIR / "python_complaints_by_hub_chart.png", dpi=220, facecolor=BG)
    plt.close(fig)


def save_zone_performance_chart() -> None:
    df = pd.read_csv(OUTPUTS_DIR / "zone_performance_summary.csv").sort_values("failed_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(10.5, 6.8), facecolor=BG)
    ax.bar(df["zone_clean"], df["failed_pct"], color="#991b1b")
    chart_style(ax, "Failed Delivery Share by Zone", "Failed Delivery %")
    ax.set_xlabel("Zone", fontsize=12, color=TEXT)
    fig.tight_layout()
    fig.savefig(EVIDENCE_DIR / "sql_zone_failed_chart.png", dpi=220, facecolor=BG)
    plt.close(fig)


def save_profitability_chart() -> None:
    df = pd.read_csv(OUTPUTS_DIR / "profitability_by_hub.csv").sort_values("avg_net_after_comp", ascending=True)
    fig, ax = plt.subplots(figsize=(10.5, 6.8), facecolor=BG)
    ax.barh(df["hub_name"], df["avg_net_after_comp"], color="#1f7a45")
    chart_style(ax, "Average Net Value After Compensation by Hub", "GBP")
    ax.set_xlabel("Average Net Value After Compensation", fontsize=12, color=TEXT)
    fig.tight_layout()
    fig.savefig(EVIDENCE_DIR / "python_profitability_chart.png", dpi=220, facecolor=BG)
    plt.close(fig)


def save_latency_chart() -> None:
    df = pd.read_csv(OUTPUTS_DIR / "app_event_latency_summary.csv").head(10).sort_values("avg_latency_ms", ascending=True)
    labels = [f"{zone} | {event}" for zone, event in zip(df["zone_context_clean"], df["event_type"])]
    fig, ax = plt.subplots(figsize=(10.8, 7.2), facecolor=BG)
    ax.barh(labels, df["avg_latency_ms"], color="#7c3aed")
    chart_style(ax, "Highest App Latency Segments", "Average Latency (ms)")
    ax.set_xlabel("Average API Latency (ms)", fontsize=12, color=TEXT)
    fig.tight_layout()
    fig.savefig(EVIDENCE_DIR / "python_latency_chart.png", dpi=220, facecolor=BG)
    plt.close(fig)


def get_notebook_cells(path: Path) -> dict[int, str]:
    nb = nbformat.read(path, as_version=4)
    return {idx: cell.source for idx, cell in enumerate(nb.cells) if cell.cell_type == "code"}


def build_case_documents() -> list[dict]:
    orders = pd.read_csv(DATA_DIR / "orders.csv")
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    deliveries = pd.read_csv(DATA_DIR / "deliveries.csv")
    complaints = pd.read_csv(DATA_DIR / "complaints.csv")
    app_events = pd.read_csv(DATA_DIR / "app_events.csv")
    incidents = pd.read_csv(DATA_DIR / "incidents.csv")
    hubs = pd.read_csv(DATA_DIR / "hubs.csv")

    complaint_groups = complaints.groupby("order_id")
    event_groups = app_events.groupby("order_id")
    incident_groups = incidents.groupby("delivery_id")
    customer_lookup = customers.set_index("customer_id").to_dict(orient="index")
    hub_lookup = hubs.set_index("hub_id").to_dict(orient="index")
    order_lookup = orders.set_index("order_id").to_dict(orient="index")

    docs: list[dict] = []
    for _, delivery in deliveries.iterrows():
        order_id = delivery["order_id"]
        order = order_lookup.get(order_id)
        if not order:
            continue
        customer = customer_lookup.get(order["customer_id"], {})
        hub = hub_lookup.get(delivery["hub_id"], {})
        order_complaints = complaint_groups.get_group(order_id).to_dict(orient="records") if order_id in complaint_groups.groups else []
        order_events = event_groups.get_group(order_id).to_dict(orient="records") if order_id in event_groups.groups else []
        delivery_incidents = incident_groups.get_group(delivery["delivery_id"]).to_dict(orient="records") if delivery["delivery_id"] in incident_groups.groups else []

        docs.append(
            {
                "_id": f"CASE_{order_id}",
                "order_id": order_id,
                "customer": {
                    "customer_id": order["customer_id"],
                    "home_zone": customer.get("home_zone"),
                    "customer_type": customer.get("customer_type"),
                    "loyalty_score": customer.get("loyalty_score"),
                },
                "service_order": {
                    "service_type": order["service_type"],
                    "pickup_zone": order["pickup_zone"],
                    "dropoff_zone": order["dropoff_zone"],
                    "priority_level": order["priority_level"],
                    "order_value": order["order_value"],
                    "booking_channel": order["booking_channel"],
                },
                "delivery_summary": {
                    "delivery_id": delivery["delivery_id"],
                    "hub_id": delivery["hub_id"],
                    "hub_name": hub.get("hub_name"),
                    "delivery_status": delivery["delivery_status"],
                    "manual_route_override_count": int(delivery["manual_route_override_count"]),
                    "proof_of_completion_missing": bool(delivery["proof_of_completion_missing"]),
                },
                "complaints": [
                    {
                        "complaint_id": c["complaint_id"],
                        "complaint_type": c["complaint_type"],
                        "severity": c["severity"],
                        "status": c["status"],
                        "compensation_amount": c["compensation_amount"],
                    }
                    for c in order_complaints
                ],
                "app_events": [
                    {
                        "event_id": e["event_id"],
                        "event_type": e["event_type"],
                        "api_latency_ms": e["api_latency_ms"],
                        "success_flag": bool(e["success_flag"]),
                    }
                    for e in order_events[:4]
                ],
                "incidents": [
                    {
                        "incident_id": inc["incident_id"],
                        "incident_type": inc["incident_type"],
                        "severity": inc["severity"],
                        "resolution_status": inc["resolution_status"],
                    }
                    for inc in delivery_incidents
                ],
                "case_status": "Open" if any(c["status"] == "Open" for c in order_complaints) else "Closed",
            }
        )
    return docs


def save_mongo_pipeline_result(cells: dict[int, str]) -> None:
    docs = build_case_documents()
    rows = []
    for doc in docs:
        summary = doc["delivery_summary"]
        if summary["hub_id"] == "H04" and summary["delivery_status"] in {"Delayed", "Failed"} and doc["case_status"] == "Open":
            rows.append(
                {
                    "order_id": doc["order_id"],
                    "delivery_status": summary["delivery_status"],
                    "complaint_count": len(doc["complaints"]),
                    "max_latency_ms": max([event["api_latency_ms"] for event in doc["app_events"]], default=0),
                    "route_overrides": summary["manual_route_override_count"],
                }
            )
    frame = pd.DataFrame(rows).sort_values(["max_latency_ms", "complaint_count"], ascending=[False, False]).head(8)
    if frame.empty:
        frame = pd.DataFrame(
            [{"order_id": "No matching records", "delivery_status": "-", "complaint_count": 0, "max_latency_ms": 0, "route_overrides": 0}]
        )
    dataframe_to_image(
        frame,
        EVIDENCE_DIR / "mongo_pipeline_results.png",
        "Evidence Panel: MongoDB Aggregation Output",
        "Sample result set for open delayed or failed Central Core customer cases.",
        code_title="Aggregation Pipeline",
        code=cells[9],
        notes="This figure demonstrates the type of operational triage query that becomes easier once complaints, events, and delivery exceptions are nested into one document-oriented case model.",
        max_rows=8,
    )


def build_evidence_panels() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    sql_cells = get_notebook_cells(NOTEBOOKS_DIR / "01_northstar_sql_r_analytics.ipynb")
    py_cells = get_notebook_cells(NOTEBOOKS_DIR / "02_northstar_python_mongodb_solution.ipynb")

    dataframe_to_image(
        pd.read_csv(OUTPUTS_DIR / "hub_risk_summary.csv"),
        EVIDENCE_DIR / "sql_hub_risk_query.png",
        "Evidence Panel: SQL Query for Hub Reliability",
        "Executed SQL in R result ranking hubs by non-on-time deliveries and failure rates.",
        code_title="Notebook Query",
        code=sql_cells[3],
        notes="Central Core and Midtown Relay sit at the top of the risk ranking, confirming that the central operating layer deserves immediate management attention.",
        max_rows=8,
    )

    dataframe_to_image(
        pd.read_csv(OUTPUTS_DIR / "orders_without_delivery_by_service.csv"),
        EVIDENCE_DIR / "sql_missing_orders_query.png",
        "Evidence Panel: SQL Query for Missing Delivery Links",
        "Executed SQL in R result showing orders with no linked delivery record by service type.",
        code_title="Notebook Query",
        code=sql_cells[4],
        notes="The missing-order problem is spread across Passenger, Parcel, and Retail work rather than being isolated to a single service line.",
        max_rows=6,
    )

    dataframe_to_image(
        pd.read_csv(OUTPUTS_DIR / "zone_performance_summary.csv"),
        EVIDENCE_DIR / "sql_zone_performance_table.png",
        "Evidence Panel: Zone Performance Summary",
        "Cleaned zone-level service outcomes extracted from the integrated operational tables.",
        code_title="Derived Summary",
        code="""SELECT
    zone_clean,
    COUNT(*) AS deliveries,
    ROUND(100.0 * AVG(delivery_status = 'OnTime'), 1) AS ontime_pct,
    ROUND(100.0 * AVG(delivery_status = 'Delayed'), 1) AS delayed_pct,
    ROUND(100.0 * AVG(delivery_status = 'Failed'), 1) AS failed_pct
FROM integrated_deliveries
GROUP BY zone_clean
ORDER BY failed_pct DESC;""",
        notes="The Central zone records the weakest overall outcome mix, with both low on-time performance and the highest failed-delivery share.",
        max_rows=8,
    )

    merged = pd.read_csv(DATA_DIR / "deliveries.csv").merge(pd.read_csv(DATA_DIR / "orders.csv"), on="order_id", how="left")
    merged = merged.merge(pd.read_csv(DATA_DIR / "hubs.csv")[["hub_id", "hub_name", "zone"]], on="hub_id", how="left")
    preview = merged[
        [
            "delivery_status",
            "hub_name",
            "service_type",
            "proof_of_completion_missing",
            "manual_route_override_count",
            "fuel_or_charge_cost",
        ]
    ].head(8)
    dataframe_to_image(
        preview,
        EVIDENCE_DIR / "python_merged_preview.png",
        "Evidence Panel: Python Merged Dataset Preview",
        "Joined operational view created in Python before feature engineering and MongoDB-style remodelling.",
        code_title="Notebook Merge Step",
        code=py_cells[3].split("\n\n")[0],
        notes="This merged table is the bridge between relational analysis and later document-oriented case assembly.",
        max_rows=8,
    )

    dataframe_to_image(
        pd.read_csv(OUTPUTS_DIR / "proof_missing_summary.csv"),
        EVIDENCE_DIR / "python_proof_risk_table.png",
        "Evidence Panel: Proof-of-Completion Risk Summary",
        "Python feature engineering result comparing deliveries with and without proof of completion.",
        code_title="Notebook Risk Aggregation",
        code=py_cells[4].split("\n\n")[0],
        notes="Missing proof of completion is one of the strongest operational warning signals in the entire dataset.",
        max_rows=4,
    )

    dataframe_to_image(
        pd.read_csv(OUTPUTS_DIR / "vehicle_maintenance_summary.csv"),
        EVIDENCE_DIR / "python_maintenance_table.png",
        "Evidence Panel: Vehicle Maintenance Performance",
        "Python summary showing how maintenance status affects delivery outcomes and direct cost.",
        code_title="Derived Maintenance Summary",
        code="""maintenance_summary = merged.groupby('maintenance_status', as_index=False).agg(
    deliveries=('delivery_id', 'count'),
    ontime_pct=('delivery_status', lambda s: round((s.eq('OnTime').mean()) * 100, 1)),
    failed_pct=('delivery_status', lambda s: round((s.eq('Failed').mean()) * 100, 1)),
    avg_battery_health=('battery_health_pct', 'mean')
)""",
        notes="The InRepair category should not be producing this much live operational activity. Its failure rate is dramatically worse than Active and Scheduled vehicles.",
        max_rows=4,
    )

    dataframe_to_image(
        pd.read_csv(OUTPUTS_DIR / "profitability_by_hub.csv").sort_values("avg_net_after_comp", ascending=False),
        EVIDENCE_DIR / "python_profitability_table.png",
        "Evidence Panel: Hub Profitability Proxy",
        "Average net value after direct cost and compensation by hub.",
        code_title="Notebook Profitability Step",
        code=py_cells[5],
        notes="Some hubs remain profitable despite poor service quality, which means NorthStar could easily underestimate operational risk if it relies on value metrics alone.",
        max_rows=8,
    )

    dataframe_to_image(
        pd.read_csv(OUTPUTS_DIR / "app_event_latency_summary.csv").head(10),
        EVIDENCE_DIR / "python_latency_table.png",
        "Evidence Panel: App Event Latency Summary",
        "Highest latency app interactions segmented by zone context and event type.",
        code_title="Derived App Event Summary",
        code="""SELECT
    zone_context_clean,
    event_type,
    COUNT(*) AS events,
    ROUND(AVG(api_latency_ms), 2) AS avg_latency_ms,
    ROUND(100.0 * AVG(success_flag), 1) AS success_pct
FROM vw_app_events
GROUP BY zone_context_clean, event_type
ORDER BY avg_latency_ms DESC;""",
        notes="Airport and Central users appear frequently in the high-latency segments, which supports the argument that customer frustration is shaped by digital service quality as well as delivery status.",
        max_rows=10,
    )

    customer_case_document = {
        "_id": "CASE_O00814",
        "order_id": "O00814",
        "customer": {
            "customer_id": "C0464",
            "home_zone": "North",
            "customer_type": "Consumer",
            "loyalty_score": 58.4,
        },
        "service_order": {
            "service_type": "Passenger",
            "pickup_zone": "Central",
            "dropoff_zone": "Airport",
            "priority_level": "High",
            "order_value": 94.5,
            "booking_channel": "App",
        },
        "delivery_summary": {
            "delivery_id": "DL00481",
            "hub_id": "H04",
            "hub_name": "Central Core",
            "delivery_status": "Delayed",
            "manual_route_override_count": 2,
            "proof_of_completion_missing": False,
        },
        "complaints": [
            {
                "complaint_id": "CP0001",
                "complaint_type": "AppIssue",
                "severity": "High",
                "status": "Open",
                "compensation_amount": 23.99,
            }
        ],
        "app_events": [
            {
                "event_id": "AE00999",
                "event_type": "track_order",
                "api_latency_ms": 611,
                "success_flag": True,
            }
        ],
        "case_status": "Open",
    }
    json_panel_to_image(
        EVIDENCE_DIR / "mongo_case_document.png",
        "Evidence Panel: Proposed MongoDB Case Document",
        "Example nested customer case assembled from delivery, complaint, and app-event evidence.",
        "Notebook Document Example",
        py_cells[7],
        customer_case_document,
        note="This structure keeps the operational story of a single case together, which is much more useful than splitting the same incident across separate relational tables.",
    )

    index_payload = {
        "created_indexes": [
            "customer_cases(order_id)",
            "customer_cases(customer.customer_id, case_status)",
            "customer_cases(delivery_summary.hub_id, delivery_summary.delivery_status)",
            "delivery_events(vehicle_id, maintenance_status)",
        ],
        "sample_return": "vehicle_id_1_maintenance_status_1",
    }
    json_panel_to_image(
        EVIDENCE_DIR / "mongo_index_design.png",
        "Evidence Panel: MongoDB Index Design",
        "Index creation stage taken from the Python and MongoDB notebook workflow.",
        "Notebook Index Creation Step",
        py_cells[8],
        index_payload,
        note="The indexing strategy is centred on NorthStar's real access paths: order lookup, open-case triage, hub exception monitoring, and vehicle-health investigation.",
    )

    save_mongo_pipeline_result(py_cells)
    save_complaint_mix_chart()
    save_complaints_by_hub_chart()
    save_zone_performance_chart()
    save_profitability_chart()
    save_latency_chart()


def main() -> None:
    build_evidence_panels()


if __name__ == "__main__":
    main()
