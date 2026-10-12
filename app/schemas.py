"""Pydantic models: they describe and validate the JSON going in and out of the API."""
from pydantic import BaseModel, Field


class PartBase(BaseModel):
    part_number: str = Field(min_length=1, max_length=50, examples=["PMP-4410"])
    name: str = Field(min_length=1, max_length=200, examples=["Seawater cooling pump impeller"])
    category: str = Field(min_length=1, max_length=100, examples=["Pumps"])
    quantity_on_hand: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=0, ge=0, description="Reorder when stock falls to this level")
    lead_time_days: int = Field(default=0, ge=0, description="Typical days from order to delivery")
    supplier: str | None = Field(default=None, max_length=200)


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    """Every field optional, so a PATCH can change just one thing."""
    part_number: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    quantity_on_hand: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=200)


class Part(PartBase):
    id: int


class StockAdjustment(BaseModel):
    change: int = Field(description="Positive when parts arrive, negative when parts are used")
    reason: str | None = Field(default=None, max_length=200, examples=["Used in work order WO-1182"])
