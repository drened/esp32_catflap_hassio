
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CatProfile:
    """Known cat profile mapped to a microchip ID."""

    chip_id: str
    name: str
    inside: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CatProfile":
        return cls(
            chip_id=str(data["chip_id"]),
            name=str(data["name"]),
            inside=bool(data.get("inside", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chip_id": self.chip_id,
            "name": self.name,
            "inside": self.inside,
        }


@dataclass(slots=True)
class FlapEvent:
    """Single flap event produced by RFID + direction detection."""

    chip_id: str
    direction: str
    at: str
    source: str | None = None
    cat_name: str | None = None
    known_cat: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlapEvent":
        return cls(
            chip_id=str(data["chip_id"]),
            direction=str(data["direction"]),
            at=str(data["at"]),
            source=data.get("source"),
            cat_name=data.get("cat_name"),
            known_cat=bool(data.get("known_cat", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chip_id": self.chip_id,
            "direction": self.direction,
            "at": self.at,
            "source": self.source,
            "cat_name": self.cat_name,
            "known_cat": self.known_cat,
        }
