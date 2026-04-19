from sqlalchemy import Column, Integer, String, Float
from .base import Base

class Setting(Base):
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    music_dir = Column(String)
    volume = Column(Float, default=0.5)