import csv
import os
import sqlite3
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path("/Users/danishkayani/Documents/Codex/2026-05-23/files-mentioned-by-the-user-msg")
DATA_DIR = ROOT / "northstar_dataset"
ARTIFACTS_DIR = ROOT / "artifacts"
OUTPUTS_DIR = ARTIFACTS_DIR / "outputs"
DB_PATH = ARTIFACTS_DIR / "northstar_analysis.db"


def ensure_dirs() -> None:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)


def sqlite_connect() -> sqlite3.Connection:
    if DB_PATH.exists():
        DB_PATH.unlink()
    return sqlite3.connect(DB_PATH)


def load_csvs(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    for path in sorted(DATA_DIR.glob("*.csv")):
        if path.name == "data_dictionary.csv":
            continue
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            headers = next(reader)
            table_name = path.stem
            columns_sql = ", ".join([f'"{header}" TEXT' for header in headers])
            cur.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            cur.execute(f'CREATE TABLE "{table_name}" ({columns_sql})')
            placeholders = ",".join(["?"] * len(headers))
            cur.executemany(
                f'INSERT INTO "{table_name}" VALUES ({placeholders})',
                reader,
            )
    conn.commit()


def create_views(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    zone_case = """
    CASE
        WHEN upper(trim({col})) = 'NORTH' THEN 'North'
        WHEN upper(trim({col})) = 'SOUTH' THEN 'South'
        WHEN upper(trim({col})) = 'EAST' THEN 'East'
        WHEN upper(trim({col})) = 'WEST' THEN 'West'
        WHEN upper(trim({col})) = 'AIRPORT' THEN 'Airport'
        WHEN upper(trim({col})) IN ('CENTRAL', 'CTR') THEN 'Central'
        WHEN upper(trim({col})) = 'RIVERSIDE' THEN 'Riverside'
        ELSE trim({col})
    END
    """

    statements = [
        f"""
        CREATE VIEW vw_customers AS
        SELECT
            customer_id,
            CAST(age AS INTEGER) AS age,
            {zone_case.format(col='home_zone')} AS home_zone_clean,
            customer_type,
            signup_date,
            CAST(loyalty_score AS REAL) AS loyalty_score,
            CAST(app_engagement_score AS REAL) AS app_engagement_score,
            NULLIF(preferred_channel, '') AS preferred_channel,
            account_status
        FROM customers
        """,
        f"""
        CREATE VIEW vw_orders AS
        SELECT
            order_id,
            customer_id,
            service_type,
            order_created_at,
            CAST(promised_window_hours AS REAL) AS promised_window_hours,
            {zone_case.format(col='pickup_zone')} AS pickup_zone_clean,
            {zone_case.format(col='dropoff_zone')} AS dropoff_zone_clean,
            NULLIF(priority_level, '') AS priority_level,
            CAST(order_value AS REAL) AS order_value,
            NULLIF(booking_channel, '') AS booking_channel,
            CAST(special_handling_flag AS INTEGER) AS special_handling_flag
        FROM orders
        """,
        f"""
        CREATE VIEW vw_deliveries AS
        SELECT
            delivery_id,
            order_id,
            driver_id,
            vehicle_id,
            hub_id,
            dispatch_time,
            NULLIF(delivery_completed_at, '') AS delivery_completed_at,
            delivery_status,
            CAST(route_distance_km AS REAL) AS route_distance_km,
            CAST(manual_route_override_count AS INTEGER) AS manual_route_override_count,
            CAST(proof_of_completion_missing AS INTEGER) AS proof_of_completion_missing,
            CAST(NULLIF(customer_rating_post_delivery, '') AS REAL) AS customer_rating_post_delivery,
            CAST(fuel_or_charge_cost AS REAL) AS fuel_or_charge_cost,
            ROUND((julianday(NULLIF(delivery_completed_at, '')) - julianday(dispatch_time)) * 24, 2) AS completion_hours
        FROM deliveries
        """,
        f"""
        CREATE VIEW vw_drivers AS
        SELECT
            driver_id,
            {zone_case.format(col='base_zone')} AS base_zone_clean,
            employment_type,
            CAST(years_experience AS INTEGER) AS years_experience,
            CAST(training_score AS REAL) AS training_score,
            CAST(driver_rating AS REAL) AS driver_rating,
            shift_preference,
            CAST(active_flag AS INTEGER) AS active_flag
        FROM drivers
        """,
        f"""
        CREATE VIEW vw_vehicles AS
        SELECT
            vehicle_id,
            vehicle_type,
            {zone_case.format(col='assigned_zone')} AS assigned_zone_clean,
            commission_date,
            CAST(battery_health_pct AS REAL) AS battery_health_pct,
            CAST(odometer_km AS REAL) AS odometer_km,
            maintenance_status,
            telematics_version
        FROM vehicles
        """,
        f"""
        CREATE VIEW vw_hubs AS
        SELECT
            hub_id,
            hub_name,
            {zone_case.format(col='zone')} AS zone_clean,
            hub_type,
            CAST(capacity_score AS REAL) AS capacity_score
        FROM hubs
        """,
        """
        CREATE VIEW vw_complaints AS
        SELECT
            complaint_id,
            customer_id,
            order_id,
            complaint_type,
            channel,
            severity,
            created_at,
            status,
            CAST(resolution_days AS REAL) AS resolution_days,
            CAST(compensation_amount AS REAL) AS compensation_amount
        FROM complaints
        """,
        f"""
        CREATE VIEW vw_app_events AS
        SELECT
            event_id,
            customer_id,
            NULLIF(order_id, '') AS order_id,
            event_timestamp,
            event_type,
            session_id,
            device_type,
            {zone_case.format(col='zone_context')} AS zone_context_clean,
            CAST(api_latency_ms AS REAL) AS api_latency_ms,
            CAST(success_flag AS INTEGER) AS success_flag
        FROM app_events
        """,
        """
        CREATE VIEW vw_incidents AS
        SELECT
            incident_id,
            delivery_id,
            incident_type,
            reported_at,
            severity,
            resolution_status,
            CAST(resolved_hours AS REAL) AS resolved_hours
        FROM incidents
        """,
    ]

    for statement in statements:
        cur.execute(statement)
    conn.commit()


def export_query(conn: sqlite3.Connection, name: str, sql: str) -> list[dict[str, object]]:
    cur = conn.cursor()
    rows = cur.execute(sql).fetchall()
    headers = [col[0] for col in cur.description]
    records = [dict(zip(headers, row)) for row in rows]

    output_path = OUTPUTS_DIR / f"{name}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records)
    return records


def write_svg_bar_chart(
    records: list[dict[str, object]],
    label_key: str,
    value_key: str,
    filename: str,
    title: str,
    subtitle: str,
    value_suffix: str = "%",
) -> None:
    width = 900
    height = 540
    margin_left = 190
    margin_right = 80
    margin_top = 90
    margin_bottom = 70
    bar_gap = 14
    bar_height = 34
    max_value = max(float(row[value_key]) for row in records) if records else 1
    chart_width = width - margin_left - margin_right
    chart_height = len(records) * (bar_height + bar_gap)
    height = max(height, margin_top + chart_height + margin_bottom)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f4ee"/>',
        f'<text x="{margin_left}" y="40" font-size="28" font-family="Helvetica, Arial, sans-serif" fill="#1f2937" font-weight="700">{escape(title)}</text>',
        f'<text x="{margin_left}" y="64" font-size="14" font-family="Helvetica, Arial, sans-serif" fill="#6b7280">{escape(subtitle)}</text>',
    ]

    for tick in range(0, 6):
        tick_value = max_value * tick / 5
        x = margin_left + chart_width * tick / 5
        parts.append(
            f'<line x1="{x}" y1="{margin_top}" x2="{x}" y2="{height - margin_bottom}" stroke="#d1d5db" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x}" y="{height - margin_bottom + 24}" text-anchor="middle" font-size="12" font-family="Helvetica, Arial, sans-serif" fill="#6b7280">{tick_value:.0f}{escape(value_suffix)}</text>'
        )

    for idx, row in enumerate(records):
        y = margin_top + idx * (bar_height + bar_gap)
        label = str(row[label_key])
        value = float(row[value_key])
        bar_width = 0 if max_value == 0 else chart_width * value / max_value
        parts.append(
            f'<text x="{margin_left - 12}" y="{y + 23}" text-anchor="end" font-size="14" font-family="Helvetica, Arial, sans-serif" fill="#374151">{escape(label)}</text>'
        )
        parts.append(
            f'<rect x="{margin_left}" y="{y}" width="{bar_width:.1f}" height="{bar_height}" rx="6" fill="#d97706"/>'
        )
        parts.append(
            f'<text x="{margin_left + bar_width + 10:.1f}" y="{y + 23}" font-size="14" font-family="Helvetica, Arial, sans-serif" fill="#111827" font-weight="700">{value:.1f}{escape(value_suffix)}</text>'
        )

    parts.append("</svg>")
    (OUTPUTS_DIR / filename).write_text("\n".join(parts), encoding="utf-8")


def build_summary_markdown(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    metrics = {
        "orders": cur.execute("SELECT COUNT(*) FROM vw_orders").fetchone()[0],
        "deliveries": cur.execute("SELECT COUNT(*) FROM vw_deliveries").fetchone()[0],
        "orders_without_delivery": cur.execute(
            """
            SELECT COUNT(*)
            FROM vw_orders o
            LEFT JOIN vw_deliveries d ON d.order_id = o.order_id
            WHERE d.order_id IS NULL
            """
        ).fetchone()[0],
        "complaints": cur.execute("SELECT COUNT(*) FROM vw_complaints").fetchone()[0],
        "incidents": cur.execute("SELECT COUNT(*) FROM vw_incidents").fetchone()[0],
        "app_events": cur.execute("SELECT COUNT(*) FROM vw_app_events").fetchone()[0],
    }

    text = f"""# NorthStar Artifact Summary

- Orders: {metrics['orders']}
- Deliveries: {metrics['deliveries']}
- Orders without delivery records: {metrics['orders_without_delivery']}
- Complaints: {metrics['complaints']}
- Incidents: {metrics['incidents']}
- App events: {metrics['app_events']}

The CSV summaries and SVG charts in `artifacts/outputs` were produced from the cleaned SQLite views in `artifacts/northstar_analysis.db`.
"""
    (ARTIFACTS_DIR / "SUMMARY.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    conn = sqlite_connect()
    load_csvs(conn)
    create_views(conn)

    query_map = {
        "dataset_quality_summary": """
        SELECT 'customers_preferred_channel_missing' AS metric, COUNT(*) AS value
        FROM vw_customers WHERE preferred_channel IS NULL
        UNION ALL
        SELECT 'orders_booking_channel_missing', COUNT(*) FROM vw_orders WHERE booking_channel IS NULL
        UNION ALL
        SELECT 'deliveries_completed_timestamp_missing', COUNT(*) FROM vw_deliveries WHERE delivery_completed_at IS NULL
        UNION ALL
        SELECT 'deliveries_rating_missing', COUNT(*) FROM vw_deliveries WHERE customer_rating_post_delivery IS NULL
        UNION ALL
        SELECT 'orders_without_delivery_record',
               COUNT(*)
        FROM vw_orders o
        LEFT JOIN vw_deliveries d ON d.order_id = o.order_id
        WHERE d.order_id IS NULL
        """,
        "hub_risk_summary": """
        SELECT
            h.hub_name,
            h.zone_clean,
            COUNT(*) AS deliveries,
            ROUND(100.0 * SUM(CASE WHEN d.delivery_status != 'OnTime' THEN 1 ELSE 0 END) / COUNT(*), 1) AS non_ontime_pct,
            ROUND(100.0 * SUM(CASE WHEN d.delivery_status = 'Failed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS failed_pct,
            ROUND(AVG(d.manual_route_override_count), 2) AS avg_route_overrides,
            ROUND(AVG(d.completion_hours), 2) AS avg_completion_hours,
            ROUND(AVG(d.fuel_or_charge_cost), 2) AS avg_direct_cost
        FROM vw_deliveries d
        JOIN vw_hubs h ON h.hub_id = d.hub_id
        GROUP BY h.hub_name, h.zone_clean
        ORDER BY non_ontime_pct DESC, failed_pct DESC
        """,
        "zone_performance_summary": """
        SELECT
            h.zone_clean,
            COUNT(*) AS deliveries,
            ROUND(100.0 * SUM(CASE WHEN d.delivery_status = 'OnTime' THEN 1 ELSE 0 END) / COUNT(*), 1) AS ontime_pct,
            ROUND(100.0 * SUM(CASE WHEN d.delivery_status = 'Delayed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS delayed_pct,
            ROUND(100.0 * SUM(CASE WHEN d.delivery_status = 'Failed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS failed_pct,
            ROUND(AVG(d.manual_route_override_count), 2) AS avg_route_overrides,
            ROUND(AVG(d.completion_hours), 2) AS avg_completion_hours
        FROM vw_deliveries d
        JOIN vw_hubs h ON h.hub_id = d.hub_id
        GROUP BY h.zone_clean
        ORDER BY failed_pct DESC, delayed_pct DESC
        """,
        "proof_missing_summary": """
        SELECT
            proof_of_completion_missing,
            COUNT(*) AS deliveries,
            ROUND(100.0 * SUM(CASE WHEN delivery_status = 'Delayed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS delayed_pct,
            ROUND(100.0 * SUM(CASE WHEN delivery_status = 'Failed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS failed_pct,
            ROUND(AVG(customer_rating_post_delivery), 2) AS avg_rating
        FROM vw_deliveries
        GROUP BY proof_of_completion_missing
        ORDER BY proof_of_completion_missing
        """,
        "route_override_summary": """
        SELECT
            CASE
                WHEN manual_route_override_count = 0 THEN '0'
                WHEN manual_route_override_count = 1 THEN '1'
                WHEN manual_route_override_count = 2 THEN '2'
                ELSE '3+'
            END AS override_band,
            COUNT(*) AS deliveries,
            ROUND(100.0 * SUM(CASE WHEN delivery_status != 'OnTime' THEN 1 ELSE 0 END) / COUNT(*), 1) AS non_ontime_pct,
            ROUND(AVG(customer_rating_post_delivery), 2) AS avg_rating
        FROM vw_deliveries
        GROUP BY override_band
        ORDER BY override_band
        """,
        "orders_without_delivery_by_service": """
        SELECT
            service_type,
            COUNT(*) AS missing_orders,
            ROUND(AVG(order_value), 2) AS avg_order_value,
            ROUND(AVG(promised_window_hours), 2) AS avg_promised_window_hours
        FROM vw_orders o
        LEFT JOIN vw_deliveries d ON d.order_id = o.order_id
        WHERE d.order_id IS NULL
        GROUP BY service_type
        ORDER BY missing_orders DESC
        """,
        "complaint_mix_by_delivery_status": """
        SELECT
            c.complaint_type,
            d.delivery_status,
            COUNT(*) AS complaints
        FROM vw_complaints c
        JOIN vw_deliveries d ON d.order_id = c.order_id
        GROUP BY c.complaint_type, d.delivery_status
        ORDER BY c.complaint_type, complaints DESC
        """,
        "complaints_by_hub": """
        SELECT
            h.hub_name,
            COUNT(c.complaint_id) AS complaints,
            COUNT(DISTINCT d.delivery_id) AS deliveries,
            ROUND(1.0 * COUNT(c.complaint_id) / COUNT(DISTINCT d.delivery_id), 3) AS complaints_per_delivery,
            ROUND(AVG(c.compensation_amount), 2) AS avg_compensation
        FROM vw_deliveries d
        JOIN vw_hubs h ON h.hub_id = d.hub_id
        LEFT JOIN vw_complaints c ON c.order_id = d.order_id
        GROUP BY h.hub_name
        ORDER BY complaints_per_delivery DESC
        """,
        "app_event_latency_summary": """
        SELECT
            zone_context_clean,
            event_type,
            COUNT(*) AS events,
            ROUND(AVG(api_latency_ms), 2) AS avg_latency_ms,
            ROUND(100.0 * AVG(success_flag), 1) AS success_pct
        FROM vw_app_events
        GROUP BY zone_context_clean, event_type
        HAVING COUNT(*) >= 10
        ORDER BY avg_latency_ms DESC
        """,
        "vehicle_maintenance_summary": """
        SELECT
            maintenance_status,
            COUNT(*) AS deliveries,
            ROUND(100.0 * SUM(CASE WHEN d.delivery_status = 'OnTime' THEN 1 ELSE 0 END) / COUNT(*), 1) AS ontime_pct,
            ROUND(100.0 * SUM(CASE WHEN d.delivery_status = 'Failed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS failed_pct,
            ROUND(AVG(v.battery_health_pct), 2) AS avg_battery_health,
            ROUND(AVG(d.fuel_or_charge_cost), 2) AS avg_direct_cost
        FROM vw_deliveries d
        JOIN vw_vehicles v ON v.vehicle_id = d.vehicle_id
        GROUP BY maintenance_status
        ORDER BY failed_pct DESC
        """,
        "incident_outcome_summary": """
        SELECT
            i.incident_type,
            d.delivery_status,
            COUNT(*) AS incident_count,
            ROUND(AVG(d.manual_route_override_count), 2) AS avg_route_overrides,
            ROUND(AVG(d.customer_rating_post_delivery), 2) AS avg_rating
        FROM vw_incidents i
        JOIN vw_deliveries d ON d.delivery_id = i.delivery_id
        GROUP BY i.incident_type, d.delivery_status
        ORDER BY i.incident_type, incident_count DESC
        """,
        "profitability_by_hub": """
        SELECT
            h.hub_name,
            COUNT(*) AS deliveries,
            ROUND(AVG(o.order_value), 2) AS avg_order_value,
            ROUND(AVG(d.fuel_or_charge_cost), 2) AS avg_direct_cost,
            ROUND(AVG(COALESCE(c.compensation_amount, 0)), 2) AS avg_compensation,
            ROUND(AVG(o.order_value - d.fuel_or_charge_cost - COALESCE(c.compensation_amount, 0)), 2) AS avg_net_after_comp,
            ROUND(100.0 * SUM(CASE WHEN d.delivery_status != 'OnTime' THEN 1 ELSE 0 END) / COUNT(*), 1) AS non_ontime_pct
        FROM vw_deliveries d
        JOIN vw_orders o ON o.order_id = d.order_id
        JOIN vw_hubs h ON h.hub_id = d.hub_id
        LEFT JOIN vw_complaints c ON c.order_id = d.order_id
        GROUP BY h.hub_name
        ORDER BY avg_net_after_comp ASC
        """,
    }

    exported = {
        name: export_query(conn, name, sql)
        for name, sql in query_map.items()
    }

    write_svg_bar_chart(
        exported["hub_risk_summary"],
        "hub_name",
        "non_ontime_pct",
        "hub_non_ontime_risk.svg",
        "Hub Reliability Risk",
        "Share of deliveries that were delayed or failed by hub",
    )
    write_svg_bar_chart(
        exported["vehicle_maintenance_summary"],
        "maintenance_status",
        "failed_pct",
        "maintenance_failed_rate.svg",
        "Maintenance Status vs Failure Rate",
        "Vehicles already in repair are strongly over-represented in failed deliveries",
    )
    write_svg_bar_chart(
        exported["orders_without_delivery_by_service"],
        "service_type",
        "missing_orders",
        "orders_without_delivery_by_service.svg",
        "Orders Without Delivery Records",
        "Potential backlog or process break between order intake and dispatch",
        value_suffix="",
    )

    build_summary_markdown(conn)
    conn.close()


if __name__ == "__main__":
    main()
