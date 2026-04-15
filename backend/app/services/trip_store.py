from __future__ import annotations
import uuid
from datetime import datetime


class TripStore:
    def __init__(self):
        self._trips: dict = {}

    def save(self, trip_data: dict) -> str:
        trip_id = uuid.uuid4().hex[:8]
        trip_data["trip_id"] = trip_id
        trip_data["created_at"] = datetime.now().isoformat()
        self._trips[trip_id] = trip_data
        return trip_id

    def reserve(self) -> str:
        """Phase 4: reserve a trip_id before the pipeline starts."""
        trip_id = uuid.uuid4().hex[:8]
        self._trips[trip_id] = {
            "trip_id": trip_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        return trip_id

    def update(self, trip_id: str, trip_data: dict) -> None:
        """Phase 4: update an existing record once the pipeline finishes."""
        existing = self._trips.get(trip_id, {})
        trip_data["trip_id"]    = trip_id
        trip_data["created_at"] = existing.get("created_at", datetime.now().isoformat())
        self._trips[trip_id]    = trip_data

    def get(self, trip_id: str) -> dict | None:
        return self._trips.get(trip_id)

    def is_ready(self, trip_id: str) -> bool:
        """True once the pipeline has finished and a full result is stored."""
        t = self._trips.get(trip_id, {})
        return "destination" in t   # result has a destination key only when complete

    def list_recent(self, limit: int = 20) -> list:
        sorted_trips = sorted(
            [t for t in self._trips.values() if "destination" in t],
            key=lambda t: t.get("created_at", ""),
            reverse=True,
        )
        return sorted_trips[:limit]

    def count(self) -> int:
        return sum(1 for t in self._trips.values() if "destination" in t)


trip_store = TripStore()
