from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base
from .tag import track_tag

class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True)
    name = Column(String)
    is_missing = Column(Boolean, default=False)
    size = Column(Integer)
    waveform = Column(Text)
    duration = Column(Integer)
    play_count = Column(Integer, default=0)
    last_position = Column(Integer, default=0)
    last_played = Column(Boolean, default=False)

    tags = relationship("Tag", secondary=track_tag, back_populates="tracks")