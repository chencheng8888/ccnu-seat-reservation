"""Spaces on a Floor and their live seat counts."""

import urllib.parse
from dataclasses import dataclass

# Convenience aliases for well-known Spaces. Runtime discovery through the
# catalog and ``findRoomDuration`` stays the source of truth.
SPACE_CODES = {
    "n1": {
        "id": "1995338268580167680",
        "name": "南湖分馆一楼开敞座位区",
        "building_id": "1995324636303638528",
        "building_name": "南湖分馆",
        "floor_id": "1995330412514557952",
        "floor_name": "南湖分馆一楼",
    },
    "n1m": {
        "id": "1995338594917990400",
        "name": "南湖分馆一楼中庭开敞座位区",
        "building_id": "1995324636303638528",
        "building_name": "南湖分馆",
        "floor_id": "1995330412514557952",
        "floor_name": "南湖分馆一楼",
    },
    "n2": {
        "id": "1995338850321743872",
        "name": "南湖分馆二楼开敞座位区",
        "building_id": "1995324636303638528",
        "building_name": "南湖分馆",
        "floor_id": "1995330565287886848",
        "floor_name": "南湖分馆二楼",
    },
}


@dataclass
class Space:
    id: str
    name: str
    building_id: str
    building_name: str
    floor_id: str
    floor_name: str
    seat_total: int = 0
    seat_free: int = 0


def spaces_body(window, floor_id):
    return {
        "beginMinute": window.start_minute,
        "currentPage": 1,
        "endMinute": window.end_minute,
        "floorId": floor_id,
        "minMinute": 0,
        "pageSize": 100,
        "power": False,
        "roomType": False,
        "sortField": "",
        "sortType": "",
        "windows": False,
    }


def spaces_path(building_id, window):
    return "/static/frontApi/res/findRoomDuration/%s/%s" % (
        urllib.parse.quote(building_id, safe=""),
        window.date_string,
    )


def parse_spaces(data, building_id, floor_id):
    data = data if isinstance(data, dict) else {}
    spaces = []
    for item in data.get("pageList") or []:
        if not isinstance(item, dict):
            continue
        spaces.append(
            Space(
                id=item.get("id") or "",
                name=item.get("name") or "",
                building_id=item.get("buildingId") or building_id,
                building_name=item.get("buildingName") or "",
                floor_id=item.get("floorId") or floor_id,
                floor_name=item.get("floorName") or "",
                seat_total=int(item.get("seatTotal") or 0),
                seat_free=int(item.get("seatFree") or 0),
            )
        )
    return spaces
