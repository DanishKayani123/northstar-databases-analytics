from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus

from PIL import Image, ImageDraw, ImageFont
from pymongo import MongoClient


ROOT = Path("/Users/danishkayani/Documents/Codex/2026-05-23/files-mentioned-by-the-user-msg")
ASSETS_DIR = ROOT / "report" / "assets"
EVIDENCE_DIR = ASSETS_DIR / "evidence"
ARTIFACTS_DIR = ROOT / "artifacts"

USERNAME = "northstarAdmin"
PASSWORD = "I6tIcHUOmKnKW(0WD%YO"
HOST = "mongodb+srv://northstarcluster.6fqfmtj.mongodb.net"
DB_NAME = "northstar_assignment"

BG = "#f7f4ee"
PANEL = "#ffffff"
TEXT = "#1f2937"
MUTED = "#6b7280"
ACCENT = "#b45309"
CODE_BG = "#f3f4f6"
HEADER = "#fef3c7"
BORDER = "#d6d3d1"


def font(size: int, bold: bool = False, mono: bool = False):
    candidates = []
    if mono:
        candidates.extend([
            "/System/Library/Fonts/SFNSMono.ttf",
            "/System/Library/Fonts/Menlo.ttc",
        ])
    elif bold:
        candidates.extend([
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ])
    else:
        candidates.extend([
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        ])
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


TITLE = font(30, bold=True)
SUB = font(18)
BODY = font(18)
BODY_BOLD = font(18, bold=True)
SMALL = font(15)
MONO = font(15, mono=True)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def line_height(draw: ImageDraw.ImageDraw, fnt) -> int:
    box = draw.textbbox((0, 0), "Ag", font=fnt)
    return box[3] - box[1] + 6


def build_uri() -> str:
    creds = f"{quote_plus(USERNAME)}:{quote_plus(PASSWORD)}@"
    return f"{HOST.replace('mongodb+srv://', 'mongodb+srv://'+creds)}/?retryWrites=true&w=majority&appName=NorthStarCluster"


def explain_metrics(explain: dict) -> dict[str, int | str]:
    stats = explain.get("executionStats", {})
    plan = explain.get("queryPlanner", {}).get("winningPlan", {})
    stage = plan.get("stage")
    if not stage and "queryPlan" in plan:
        stage = plan["queryPlan"].get("stage")
    if not stage and "inputStage" in plan:
        stage = plan["inputStage"].get("stage")
    return {
        "winning_stage": stage or "unknown",
        "n_returned": stats.get("nReturned", 0),
        "docs_examined": stats.get("totalDocsExamined", 0),
        "keys_examined": stats.get("totalKeysExamined", 0),
        "execution_time_ms": stats.get("executionTimeMillis", 0),
    }


def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    client = MongoClient(build_uri(), serverSelectionTimeoutMS=20000)
    db = client[DB_NAME]
    db.command("ping")

    counts = {name: db[name].count_documents({}) for name in sorted(db.list_collection_names())}
    query = {
        "delivery_summary.hub_id": "H04",
        "delivery_summary.delivery_status": {"$in": ["Delayed", "Failed"]},
        "case_status": "Open",
    }
    pipeline = [
        {"$match": query},
        {
            "$project": {
                "_id": 0,
                "order_id": 1,
                "delivery_status": "$delivery_summary.delivery_status",
                "complaint_count": {"$size": "$complaints"},
                "route_overrides": "$delivery_summary.manual_route_override_count",
            }
        },
        {"$sort": {"complaint_count": -1, "route_overrides": -1}},
        {"$limit": 8},
    ]
    live_cases = list(db.customer_cases.aggregate(pipeline))

    indexed = db.command(
        {
            "explain": {
                "find": "customer_cases",
                "filter": query,
            },
            "verbosity": "executionStats",
        }
    )
    natural = db.command(
        {
            "explain": {
                "find": "customer_cases",
                "filter": query,
                "hint": {"$natural": 1},
            },
            "verbosity": "executionStats",
        }
    )

    payload = {
        "collection_counts": counts,
        "live_case_sample": live_cases,
        "indexed_explain": explain_metrics(indexed),
        "natural_explain": explain_metrics(natural),
    }
    (ARTIFACTS_DIR / "atlas_live_evidence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    width = 1500
    height = 1500
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    y = 34
    draw.text((40, y), "Evidence Panel: Live Atlas Query and Explain Output", font=TITLE, fill=TEXT)
    y += 46
    draw.text((40, y), "Generated from the real MongoDB Atlas cluster after loading the NorthStar coursework database.", font=SUB, fill=MUTED)
    y += 42

    code = [
        "Atlas query: customer_cases filtered to delayed/failed open Central Core cases",
        "db.customer_cases.find({",
        "  'delivery_summary.hub_id': 'H04',",
        "  'delivery_summary.delivery_status': { '$in': ['Delayed', 'Failed'] },",
        "  'case_status': 'Open'",
        "}).explain('executionStats')",
    ]
    code_h = 22 + len(code) * line_height(draw, MONO) + 16
    draw.rounded_rectangle((36, y, width - 36, y + code_h), radius=18, fill=CODE_BG, outline=BORDER)
    cy = y + 12
    for idx, line in enumerate(code):
        draw.text((54, cy), line, font=BODY_BOLD if idx == 0 else MONO, fill=TEXT)
        cy += line_height(draw, BODY_BOLD if idx == 0 else MONO)
    y += code_h + 24

    counts_text = "Live collection counts: " + ", ".join(f"{k}={v}" for k, v in counts.items())
    lines = wrap(draw, counts_text, BODY, width - 108)
    note_h = 20 + len(lines) * line_height(draw, BODY) + 14
    draw.rounded_rectangle((36, y, width - 36, y + note_h), radius=18, fill="#fff7ed", outline="#fdba74")
    ny = y + 12
    for line in lines:
        draw.text((54, ny), line, font=BODY, fill=TEXT)
        ny += line_height(draw, BODY)
    y += note_h + 24

    table_top = y
    row_h = 44
    cols = [
        ("Scenario", 250),
        ("Winning Stage", 250),
        ("Docs Examined", 220),
        ("Keys Examined", 220),
        ("Returned", 180),
        ("Exec ms", 180),
    ]
    draw.rounded_rectangle((36, table_top, width - 36, table_top + row_h * 3), radius=16, fill=PANEL, outline=BORDER)
    x = 36
    for name, w in cols:
        draw.rectangle((x, table_top, x + w, table_top + row_h), fill=HEADER, outline=BORDER)
        draw.text((x + 10, table_top + 11), name, font=BODY_BOLD, fill=TEXT)
        x += w

    rows = [
        ("Indexed query", payload["indexed_explain"]["winning_stage"], payload["indexed_explain"]["docs_examined"], payload["indexed_explain"]["keys_examined"], payload["indexed_explain"]["n_returned"], payload["indexed_explain"]["execution_time_ms"]),
        ("Natural scan", payload["natural_explain"]["winning_stage"], payload["natural_explain"]["docs_examined"], payload["natural_explain"]["keys_examined"], payload["natural_explain"]["n_returned"], payload["natural_explain"]["execution_time_ms"]),
    ]
    for ridx, row in enumerate(rows, start=1):
        x = 36
        ry = table_top + ridx * row_h
        fill = "#ffffff" if ridx % 2 else "#fafaf9"
        for (name, w), value in zip(cols, row):
            draw.rectangle((x, ry, x + w, ry + row_h), fill=fill, outline=BORDER)
            draw.text((x + 10, ry + 11), str(value), font=SMALL, fill=TEXT)
            x += w
    y += row_h * 3 + 26

    draw.text((40, y), "Sample aggregation output from Atlas", font=BODY_BOLD, fill=TEXT)
    y += 30
    sample_lines = json.dumps(live_cases[:4], indent=2).splitlines()
    json_h = 20 + min(26, len(sample_lines)) * line_height(draw, MONO) + 14
    draw.rounded_rectangle((36, y, width - 36, y + json_h), radius=16, fill=PANEL, outline=BORDER)
    jy = y + 10
    for line in sample_lines[:26]:
        draw.text((54, jy), line, font=MONO, fill=TEXT)
        jy += line_height(draw, MONO)

    img.save(EVIDENCE_DIR / "atlas_live_query_panel.png")


if __name__ == "__main__":
    main()
