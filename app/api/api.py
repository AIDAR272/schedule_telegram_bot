from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.event_service import EventService
from app.repositories.event_repository import EventRepository
from app.schemas.event_schemas import EventCreate, EventRead, EventUpdate

app = FastAPI()


def get_event_service(db: Session = Depends(get_db)):
    repo = EventRepository(db)
    service = EventService(repo)
    return service


@app.post("/events", response_model=EventRead)
def create_event(event_dto: EventCreate, service: EventService = Depends(get_event_service)):
    return service.create_event(event_dto)


@app.get("/events/{event_id}", response_model=EventRead)
def get_event(event_id: int, service: EventService = Depends(get_event_service)):
    event = service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.get("/users/{user_id}/events", response_model=list[EventRead])
def get_user_events(user_id: int, service: EventService = Depends(get_event_service)):
    return service.get_user_events(user_id)


@app.put("/events/{event_id}", response_model=EventRead)
def update_event(event_id: int, update_dto: EventUpdate, service: EventService = Depends(get_event_service)):
    event = service.update_event(event_id, update_dto)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.delete("/events/{event_id}")
def delete_event(event_id: int, service: EventService = Depends(get_event_service)):
    success = service.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"detail": "Event deleted successfully"}
