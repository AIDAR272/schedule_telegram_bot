from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Date, Time, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta, date, time

from app.database.database import Base


UTC6 = timezone(timedelta(hours=6))

def get_utc6_now():
    """Returns the current time in UTC+6."""
    return datetime.now(UTC6)


class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    first_name = Column(String(50))
    username = Column(String(50))

    events = relationship("Event", back_populates="user")


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"))
    title = Column(String(255), nullable=False)
    date = Column(Date, default=lambda: get_utc6_now().date())
    time = Column(Time, default=lambda: get_utc6_now().time().replace(second=0, microsecond=0))
    created_at = Column(
        DateTime,
        default=get_utc6_now,
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=get_utc6_now,
        onupdate=get_utc6_now,
        nullable=False
    )

    user = relationship("User", back_populates="events")
