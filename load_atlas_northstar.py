from __future__ import annotations

import csv
import os
from pathlib import Path
from urllib.parse import quote_plus

from pymongo import ASCENDING, DESCENDING, MongoClient


ROOT = Path("/Users/danishkayani/Documents/Codex/2026-05-23/files-mentioned-by-the-user-msg")
DATA_DIR = ROOT / "northstar_dataset"

USERNAME = "northstarAdmin"
PASSWORD = "I6tIcHUOmKnKW(0WD%YO"
HOST = "mongodb+srv://northstarcluster.6fqfmtj.mongodb.net"
DB_NAME = "northstar_assignment"


def read_csv(name: str) -> list[dict]:
    path = DATA_DIR / name
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def clean_zone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    mapping = {
        "NORTH": "North",
        "SOUTH": "South",
        "EAST": "East",
        "WEST": "West",
        "AIRPORT": "Airport",
        "CENTRAL": "Central",
        "CTR": "Central",
        "RIVERSIDE": "Riverside",
    }
    return mapping.get(value.upper(), value)


def as_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def as_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def as_bool(value: str | None) -> bool | None:
    if value in (None, ""):
        return None
    return bool(int(value))


def build_uri() -> str:
    return f"{HOST.replace('mongodb+srv://', 'mongodb+srv://'+quote_plus(USERNAME)+':'+quote_plus(PASSWORD)+'@')}/?retryWrites=true&w=majority&appName=NorthStarCluster"


def build_collections(db) -> None:
    orders = read_csv("orders.csv")
    deliveries = read_csv("deliveries.csv")
    customers = read_csv("customers.csv")
    complaints = read_csv("complaints.csv")
    app_events = read_csv("app_events.csv")
    incidents = read_csv("incidents.csv")
    drivers = read_csv("drivers.csv")
    vehicles = read_csv("vehicles.csv")
    hubs = read_csv("hubs.csv")

    db.orders.drop()
    db.deliveries.drop()
    db.customers.drop()
    db.complaints.drop()
    db.app_events.drop()
    db.incidents.drop()
    db.drivers.drop()
    db.vehicles.drop()
    db.hubs.drop()
    db.customer_cases.drop()

    customer_lookup = {row["customer_id"]: row for row in customers}
    order_lookup = {row["order_id"]: row for row in orders}
    hub_lookup = {row["hub_id"]: row for row in hubs}
    complaint_lookup: dict[str, list[dict]] = {}
    for row in complaints:
        complaint_lookup.setdefault(row["order_id"], []).append(row)
    event_lookup: dict[str, list[dict]] = {}
    for row in app_events:
        order_id = row.get("order_id") or ""
        if order_id:
            event_lookup.setdefault(order_id, []).append(row)
    incident_lookup: dict[str, list[dict]] = {}
    for row in incidents:
        incident_lookup.setdefault(row["delivery_id"], []).append(row)

    db.orders.insert_many(
        [
            {
                "_id": row["order_id"],
                "customer_id": row["customer_id"],
                "service_type": row["service_type"],
                "order_created_at": row["order_created_at"],
                "promised_window_hours": as_float(row["promised_window_hours"]),
                "pickup_zone": clean_zone(row["pickup_zone"]),
                "dropoff_zone": clean_zone(row["dropoff_zone"]),
                "priority_level": row["priority_level"] or None,
                "order_value": as_float(row["order_value"]),
                "booking_channel": row["booking_channel"] or None,
                "special_handling_flag": as_bool(row["special_handling_flag"]),
            }
            for row in orders
        ]
    )

    db.deliveries.insert_many(
        [
            {
                "_id": row["delivery_id"],
                "order_id": row["order_id"],
                "driver_id": row["driver_id"],
                "vehicle_id": row["vehicle_id"],
                "hub_id": row["hub_id"],
                "dispatch_time": row["dispatch_time"],
                "delivery_completed_at": row["delivery_completed_at"] or None,
                "delivery_status": row["delivery_status"],
                "route_distance_km": as_float(row["route_distance_km"]),
                "manual_route_override_count": as_int(row["manual_route_override_count"]),
                "proof_of_completion_missing": as_bool(row["proof_of_completion_missing"]),
                "customer_rating_post_delivery": as_float(row["customer_rating_post_delivery"]),
                "fuel_or_charge_cost": as_float(row["fuel_or_charge_cost"]),
            }
            for row in deliveries
        ]
    )

    db.customers.insert_many(
        [
            {
                "_id": row["customer_id"],
                "age": as_int(row["age"]),
                "home_zone": clean_zone(row["home_zone"]),
                "customer_type": row["customer_type"],
                "signup_date": row["signup_date"],
                "loyalty_score": as_float(row["loyalty_score"]),
                "app_engagement_score": as_float(row["app_engagement_score"]),
                "preferred_channel": row["preferred_channel"] or None,
                "account_status": row["account_status"],
            }
            for row in customers
        ]
    )

    db.complaints.insert_many(
        [
            {
                "_id": row["complaint_id"],
                "customer_id": row["customer_id"],
                "order_id": row["order_id"],
                "complaint_type": row["complaint_type"],
                "channel": row["channel"],
                "severity": row["severity"],
                "created_at": row["created_at"],
                "status": row["status"],
                "resolution_days": as_float(row["resolution_days"]),
                "compensation_amount": as_float(row["compensation_amount"]),
            }
            for row in complaints
        ]
    )

    db.app_events.insert_many(
        [
            {
                "_id": row["event_id"],
                "customer_id": row["customer_id"],
                "order_id": row["order_id"] or None,
                "event_timestamp": row["event_timestamp"],
                "event_type": row["event_type"],
                "session_id": row["session_id"],
                "device_type": row["device_type"],
                "zone_context": clean_zone(row["zone_context"]),
                "api_latency_ms": as_float(row["api_latency_ms"]),
                "success_flag": as_bool(row["success_flag"]),
            }
            for row in app_events
        ]
    )

    db.incidents.insert_many(
        [
            {
                "_id": row["incident_id"],
                "delivery_id": row["delivery_id"],
                "incident_type": row["incident_type"],
                "reported_at": row["reported_at"],
                "severity": row["severity"],
                "resolution_status": row["resolution_status"],
                "resolved_hours": as_float(row["resolved_hours"]),
            }
            for row in incidents
        ]
    )

    db.drivers.insert_many(
        [
            {
                "_id": row["driver_id"],
                "base_zone": clean_zone(row["base_zone"]),
                "employment_type": row["employment_type"],
                "years_experience": as_int(row["years_experience"]),
                "training_score": as_float(row["training_score"]),
                "driver_rating": as_float(row["driver_rating"]),
                "shift_preference": row["shift_preference"],
                "active_flag": as_bool(row["active_flag"]),
            }
            for row in drivers
        ]
    )

    db.vehicles.insert_many(
        [
            {
                "_id": row["vehicle_id"],
                "vehicle_type": row["vehicle_type"],
                "assigned_zone": clean_zone(row["assigned_zone"]),
                "commission_date": row["commission_date"],
                "battery_health_pct": as_float(row["battery_health_pct"]),
                "odometer_km": as_float(row["odometer_km"]),
                "maintenance_status": row["maintenance_status"],
                "telematics_version": row["telematics_version"],
            }
            for row in vehicles
        ]
    )

    db.hubs.insert_many(
        [
            {
                "_id": row["hub_id"],
                "hub_name": row["hub_name"],
                "zone": clean_zone(row["zone"]),
                "hub_type": row["hub_type"],
                "capacity_score": as_float(row["capacity_score"]),
            }
            for row in hubs
        ]
    )

    customer_cases = []
    for delivery in deliveries:
        order = order_lookup.get(delivery["order_id"])
        if not order:
            continue
        customer = customer_lookup.get(order["customer_id"], {})
        hub = hub_lookup.get(delivery["hub_id"], {})
        order_complaints = complaint_lookup.get(order["order_id"], [])
        order_events = event_lookup.get(order["order_id"], [])
        linked_incidents = incident_lookup.get(delivery["delivery_id"], [])
        customer_cases.append(
            {
                "_id": f"CASE_{order['order_id']}",
                "order_id": order["order_id"],
                "customer": {
                    "customer_id": order["customer_id"],
                    "home_zone": clean_zone(customer.get("home_zone")),
                    "customer_type": customer.get("customer_type"),
                    "loyalty_score": as_float(customer.get("loyalty_score")),
                },
                "service_order": {
                    "service_type": order["service_type"],
                    "pickup_zone": clean_zone(order["pickup_zone"]),
                    "dropoff_zone": clean_zone(order["dropoff_zone"]),
                    "priority_level": order["priority_level"] or None,
                    "order_value": as_float(order["order_value"]),
                    "booking_channel": order["booking_channel"] or None,
                },
                "delivery_summary": {
                    "delivery_id": delivery["delivery_id"],
                    "hub_id": delivery["hub_id"],
                    "hub_name": hub.get("hub_name"),
                    "delivery_status": delivery["delivery_status"],
                    "manual_route_override_count": as_int(delivery["manual_route_override_count"]),
                    "proof_of_completion_missing": as_bool(delivery["proof_of_completion_missing"]),
                },
                "complaints": [
                    {
                        "complaint_id": row["complaint_id"],
                        "complaint_type": row["complaint_type"],
                        "severity": row["severity"],
                        "status": row["status"],
                        "compensation_amount": as_float(row["compensation_amount"]),
                    }
                    for row in order_complaints
                ],
                "app_events": [
                    {
                        "event_id": row["event_id"],
                        "event_type": row["event_type"],
                        "api_latency_ms": as_float(row["api_latency_ms"]),
                        "success_flag": as_bool(row["success_flag"]),
                    }
                    for row in order_events[:8]
                ],
                "incidents": [
                    {
                        "incident_id": row["incident_id"],
                        "incident_type": row["incident_type"],
                        "severity": row["severity"],
                        "resolution_status": row["resolution_status"],
                    }
                    for row in linked_incidents
                ],
                "case_status": "Open" if any(row["status"] == "Open" for row in order_complaints) else "Closed",
            }
        )

    db.customer_cases.insert_many(customer_cases)

    db.customer_cases.create_index([("order_id", ASCENDING)], name="order_id_1")
    db.customer_cases.create_index([("customer.customer_id", ASCENDING), ("case_status", ASCENDING)], name="customer_case_status")
    db.customer_cases.create_index([("delivery_summary.hub_id", ASCENDING), ("delivery_summary.delivery_status", ASCENDING)], name="hub_delivery_status")
    db.customer_cases.create_index([("delivery_summary.proof_of_completion_missing", ASCENDING)], name="proof_missing")
    db.deliveries.create_index([("vehicle_id", ASCENDING), ("delivery_status", ASCENDING)], name="vehicle_delivery_status")
    db.vehicles.create_index([("maintenance_status", ASCENDING)], name="maintenance_status_1")


def main() -> None:
    uri = build_uri()
    client = MongoClient(uri, serverSelectionTimeoutMS=20000)
    client.admin.command("ping")
    db = client[DB_NAME]
    build_collections(db)
    print(f"Loaded database: {DB_NAME}")
    print("Collections:", ", ".join(sorted(db.list_collection_names())))


if __name__ == "__main__":
    main()
