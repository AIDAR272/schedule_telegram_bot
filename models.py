from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


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
    day = Column(String(50))
    time = Column(String(50))
    event = Column(String(50))

    user = relationship("User", back_populates="events")
