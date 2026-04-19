from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

track_tag = Table(
    'track_tag', Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    tracks = relationship("Track", secondary=track_tag, back_populates="tags")