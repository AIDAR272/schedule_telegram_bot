from fastapi import HTTPException

from app.repositories.event_repository import EventRepository
from app.schemas.event_schemas import EventCreate, EventUpdate
from app.models.models import Event

class EventService:
    def __init__(self, repository: EventRepository):
        self.repository = repository

    def create_event(self, dto: EventCreate) -> Event:
        if self.repository.get_user_by_id(dto.user_id) is None:
            raise HTTPException(status_code=404, detail="User doesn't exist")
        return self.repository.create_event(dto)

    def get_event(self, event_id: int) -> Event | None:
        return self.repository.get_event(event_id)

    def get_user_events(self, user_id: int):
        return self.repository.get_events_by_user(user_id)

    def update_event(self, event_id: int, dto: EventUpdate) -> Event | None:
        return self.repository.update_event(event_id, dto)

    def delete_event(self, event_id: int) -> bool:
        return self.repository.delete_event(event_id)
