"""Resolve get_directions point inputs (entity selector or map location) to WGS84.

Each origin/destination is either an entity holding latitude/longitude attributes
or a location-selector value (`{"latitude": ..., "longitude": ...}`), resolved at
call time. Waypoints are location-selector values only. Failures raise a
ServiceValidationError naming the exact input at fault.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN


@dataclass(slots=True, frozen=True)
class ResolvedPoint:
    """A route point resolved to a display name and WGS84 coordinates."""

    name: str
    latitude: float
    longitude: float


def _resolve_entity(hass: HomeAssistant, entity_id: str) -> ResolvedPoint:
    """Resolve an entity_id to its coordinate attributes and friendly name."""
    state = hass.states.get(entity_id)
    if state is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entity_not_found",
            translation_placeholders={"entity_id": entity_id},
        )
    latitude = state.attributes.get(ATTR_LATITUDE)
    longitude = state.attributes.get(ATTR_LONGITUDE)
    if not isinstance(latitude, int | float) or not isinstance(longitude, int | float):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entity_missing_coordinates",
            translation_placeholders={"entity_id": entity_id},
        )
    name = state.attributes.get(ATTR_FRIENDLY_NAME) or entity_id
    return ResolvedPoint(name=name, latitude=float(latitude), longitude=float(longitude))


def _location_coords(location: object, *, role: str) -> tuple[float, float]:
    """Extract (latitude, longitude) from a location-selector value, ignoring radius."""
    if isinstance(location, dict):
        latitude = location.get(ATTR_LATITUDE)
        longitude = location.get(ATTR_LONGITUDE)
        if isinstance(latitude, int | float) and isinstance(longitude, int | float):
            return float(latitude), float(longitude)
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="invalid_location",
        translation_placeholders={"role": role, "value": str(location)},
    )


def resolve_point(
    hass: HomeAssistant,
    *,
    role: str,
    entity_id: str | None = None,
    location: object = None,
) -> ResolvedPoint:
    """Resolve one origin/destination input given as entity XOR a location value."""
    if entity_id is not None and location is not None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="point_input_conflict",
            translation_placeholders={"role": role},
        )
    if entity_id is not None:
        return _resolve_entity(hass, entity_id)
    if location is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="point_input_missing",
            translation_placeholders={"role": role},
        )
    latitude, longitude = _location_coords(location, role=role)
    return ResolvedPoint(name=role, latitude=latitude, longitude=longitude)


def resolve_waypoint(location: object, *, index: int) -> ResolvedPoint:
    """Resolve one waypoint given as a location-selector value."""
    name = f"경유지{index}"
    latitude, longitude = _location_coords(location, role=name)
    return ResolvedPoint(name=name, latitude=latitude, longitude=longitude)
