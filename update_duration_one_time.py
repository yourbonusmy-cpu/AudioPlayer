from services.db import Session
from models.track import Track
from pydub import AudioSegment

session = Session()

for track in session.query(Track).all():
    if not track.duration:
        try:
            audio = AudioSegment.from_file(track.path)
            track.duration = len(audio)
            print("Updated:", track.name)
        except:
            track.duration = 0

session.commit()