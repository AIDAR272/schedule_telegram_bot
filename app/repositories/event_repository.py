from http.client import HTTPException
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Event, User
from app.schemas.event_schemas import EventCreate, EventUpdate

class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: int):
        return self.db.query(User).filter(User.user_id == user_id).first()


    def create_event(self, event_dto: EventCreate) -> Event:
        data = event_dto.model_dump()
        data['date'] = datetime.strptime(event_dto.date, "%d.%m.%Y").date()
        data['time'] = datetime.strptime(event_dto.time, "%H:%M").time()
        event = Event(**data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_event(self, event_id: int) -> Event | None:
        return self.db.query(Event).filter(Event.id == event_id).first()

    def get_events_by_user(self, user_id: int):
        return self.db.query(Event).filter(Event.user_id == user_id).all()

    def update_event(self, event_id: int, update_dto: EventUpdate) -> Event | None:
        event = self.get_event(event_id)
        if not event:
            return None
        for key, value in update_dto.model_dump(exclude_unset=True).items():
            setattr(event, key, value)
        self.db.commit()
        self.db.refresh(event)
        return event

    def delete_event(self, event_id: int) -> bool:
        event = self.get_event(event_id)
        if not event:
            return False
        self.db.delete(event)
        self.db.commit()
        return True
