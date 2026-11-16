"""Building / Floor / date catalog."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Floor:
    id: str
    name: str
    building_id: str


@dataclass
class Building:
    id: str
    name: str
    floors: List[Floor] = field(default_factory=list)


@dataclass
class Catalog:
    buildings: List[Building] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)


def parse_catalog(data):
    data = data if isinstance(data, dict) else {}
    buildings = []
    for raw_building in data.get("buildings") or []:
        if not isinstance(raw_building, dict):
            continue
        building_id = raw_building.get("id") or ""
        floors = []
        for raw_floor in raw_building.get("floors") or []:
            if not isinstance(raw_floor, dict):
                continue
            floors.append(
                Floor(
                    id=raw_floor.get("id") or "",
                    name=raw_floor.get("name") or "",
                    building_id=raw_floor.get("buildingId") or building_id,
                )
            )
        buildings.append(
            Building(
                id=building_id,
                name=raw_building.get("name") or "",
                floors=floors,
            )
        )
    dates = [value for value in data.get("dates") or [] if isinstance(value, str)]
    return Catalog(buildings=buildings, dates=dates)
