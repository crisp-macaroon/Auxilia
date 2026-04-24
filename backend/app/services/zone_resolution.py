from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.database import Rider, Zone
from app.services.location_service import location_service


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
    return normalized.strip("-") or "unknown"


def _preferred_locality_name(reverse) -> str | None:
    if reverse is None:
        return None
    # Prefer micro-localities first so rider labels feel nearby and familiar.
    return reverse.suburb or reverse.road or reverse.city or None


async def ensure_placeholder_route_zone(db: AsyncSession, rider: Rider) -> Zone:
    zone_result = await db.execute(select(Zone).where(Zone.id == "route_pending"))
    zone = zone_result.scalar_one_or_none()
    if zone is not None:
        return zone

    zone = Zone(
        id="route_pending",
        name="Route Risk Pending",
        city="Dynamic Route",
        state=None,
        country="IN",
        latitude=float(rider.latitude or 0.0),
        longitude=float(rider.longitude or 0.0),
        radius_km=1.0,
        risk_level="medium",
        base_premium_factor=1.0,
        earning_index=1.0,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(zone)
    await db.flush()
    return zone


async def resolve_zone_from_coordinates(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    *,
    max_distance_km: float | None = None,
) -> dict[str, Any]:
    zones_result = await db.execute(
        select(Zone).where(Zone.is_active == True, Zone.id != "route_pending")
    )
    zones = zones_result.scalars().all()

    nearest_zone = None
    nearest_distance_meters = None
    for zone in zones:
        distance = location_service._calculate_distance(
            latitude,
            longitude,
            zone.latitude,
            zone.longitude,
        )
        if nearest_distance_meters is None or distance < nearest_distance_meters:
            nearest_distance_meters = distance
            nearest_zone = zone

    reverse = await location_service.reverse_geocode(latitude, longitude)
    locality = _preferred_locality_name(reverse)

    within_threshold = (
        nearest_zone is not None
        and (
            max_distance_km is None
            or nearest_distance_meters is None
            or nearest_distance_meters <= max_distance_km * 1000
        )
    )
    if within_threshold:
        return {
            "zone": nearest_zone,
            "distance_meters": round(float(nearest_distance_meters or 0.0), 2),
            "resolved_from": "nearest_active_zone",
            "locality": locality,
            "display_name": reverse.display_name if reverse else None,
        }

    city = reverse.city if reverse and reverse.city else "Unknown City"
    state = reverse.state if reverse and reverse.state else ""
    country = reverse.country if reverse and reverse.country else "IN"
    zone_name = locality or city or "Dynamic Zone"
    zone_id = _slugify(
        f"auto-{city}-{zone_name}-{latitude:.4f}-{longitude:.4f}"
    )

    existing_result = await db.execute(select(Zone).where(Zone.id == zone_id))
    zone = existing_result.scalar_one_or_none()
    if zone is None:
        zone = Zone(
            id=zone_id,
            name=zone_name,
            city=city,
            state=state,
            country=country,
            latitude=latitude,
            longitude=longitude,
            radius_km=settings.DELIVERY_ZONE_MAX_RADIUS_KM,
            risk_level="medium",
            base_premium_factor=1.0,
            earning_index=1.0,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(zone)
        await db.flush()

    return {
        "zone": zone,
        "distance_meters": round(float(nearest_distance_meters or 0.0), 2)
        if nearest_distance_meters is not None
        else None,
        "resolved_from": "dynamic_reverse_geocode",
        "locality": locality,
        "display_name": reverse.display_name if reverse else None,
    }


async def resolve_policy_zone_for_rider(
    db: AsyncSession,
    rider: Rider,
    *,
    preferred_zone_id: str | None = None,
    fallback_zone_id: str | None = None,
) -> dict[str, Any]:
    candidate_ids = [preferred_zone_id, rider.zone_id, fallback_zone_id]
    for zone_id in candidate_ids:
        if not zone_id or zone_id == "route_pending":
            continue
        result = await db.execute(select(Zone).where(Zone.id == zone_id))
        zone = result.scalar_one_or_none()
        if zone is not None:
            return {
                "zone": zone,
                "distance_meters": None,
                "resolved_from": "existing_policy_zone",
                "locality": None,
                "display_name": None,
            }

    if rider.latitude is not None and rider.longitude is not None:
        resolved = await resolve_zone_from_coordinates(
            db,
            rider.latitude,
            rider.longitude,
            max_distance_km=settings.DELIVERY_ZONE_MAX_RADIUS_KM,
        )
        rider.zone_id = resolved["zone"].id
        return resolved

    if preferred_zone_id and preferred_zone_id != "route_pending":
        raise HTTPException(status_code=400, detail=f"Invalid zone_id: {preferred_zone_id}")

    if fallback_zone_id and fallback_zone_id != "route_pending":
        raise HTTPException(status_code=400, detail=f"Invalid zone_id: {fallback_zone_id}")

    placeholder = await ensure_placeholder_route_zone(db, rider)
    rider.zone_id = placeholder.id
    return {
        "zone": placeholder,
        "distance_meters": None,
        "resolved_from": "route_pending_placeholder",
        "locality": None,
        "display_name": None,
    }
