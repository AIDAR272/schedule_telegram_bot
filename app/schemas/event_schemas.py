from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EventCreate(BaseModel):
    user_id : int
    title : str
    description : Optional[str] = None
    start_datetime : datetime
    end_datetime : Optional[datetime] = None
    status : str = "active"


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