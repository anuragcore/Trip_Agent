from typing import List, Optional
from pydantic import BaseModel, field_validator


class MemberInput(BaseModel):
    budget: int
    preferences: str

    @field_validator("budget")
    @classmethod
    def budget_positive(cls, v):
        if v <= 0:
            raise ValueError("Budget must be positive")
        return v


class TripRequest(BaseModel):
    from_city: str
    start_date: str          # ISO date string, e.g. "2026-12-20"  — Phase 1
    end_date: str            # ISO date string, e.g. "2026-12-25"  — Phase 1
    destinations: List[str]
    budget: Optional[int] = None
    members: Optional[List[MemberInput]] = None

    @field_validator("destinations")
    @classmethod
    def at_least_one_destination(cls, v):
        if not v:
            raise ValueError("At least one destination is required")
        return v


# ── Response models (documentation only — actual responses are plain dicts) ──

class BudgetBreakdown(BaseModel):
    travel: float
    hotel: float
    food: float
    activities: float
    total: float


class WeatherDay(BaseModel):
    date: str
    temp_max: float
    temp_min: float
    rain_chance: int
    condition: str


class PackingSuggestion(BaseModel):
    category: str
    items: List[str]


class ItineraryDay(BaseModel):
    day: int
    title: str
    activities: List[str]


class DestinationScore(BaseModel):
    destination: str
    cost: float
    score: float
    mode: str
    within_budget: bool


class TripResult(BaseModel):
    trip_id: str
    destination: str
    cost: float
    travel: str
    hotel: str
    itinerary: List[ItineraryDay]
    reasoning: str
    budget_breakdown: BudgetBreakdown
    weather: List[WeatherDay]
    packing: List[PackingSuggestion]
    all_scores: List[DestinationScore]
    meta: dict
    created_at: str


class HealthResponse(BaseModel):
    status: str
    llm_available: bool
    version: str
