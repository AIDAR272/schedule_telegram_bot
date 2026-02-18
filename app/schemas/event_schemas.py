from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class EventCreate(BaseModel):
    user_id : int
    title: str
    date: str  # Format: DD.MM.YYYY
    time: str  # Format: HH:MM

    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        try:
            # Check if it matches DD.MM.YYYY
            datetime.strptime(v, "%d.%m.%Y")
            return v
        except ValueError:
            raise ValueError("Date must be in format DD.MM.YYYY")

    @field_validator('time')
    @classmethod
    def validate_time(cls, v):
        try:
            # Check if it matches HH:MM
            datetime.strptime(v, "%H:%M")
            return v
        except ValueError:
            raise ValueError("Time must be in format HH:MM")


class EventUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    status: Optional[str]


class EventRead(EventCreate):
    id : int
    created_at : datetime
    updated_at : datetime

    class Config:
        from_attributes = True