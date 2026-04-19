from pathlib import Path
from models.track import Track
from pydub import AudioSegment
from mutagen import File as MutagenFile

#music_service.py
class MusicService:
    def __init__(self, session):
        self.session = session

    def scan_old(self, folder):
        for f in Path(folder).rglob("*.mp3"):

            if not self.session.query(Track).filter_by(path=str(f)).first():
                audio = AudioSegment.from_file(f)
                duration = self.get_duration(str(f))
                self.session.add(Track(
                    path=str(f),
                    name=f.name,
                    size=f.stat().st_size,
                    duration = duration
                ))
        self.session.commit()
        return self.session.query(Track).all()

    def get_duration(self, path):
        try:
            audio = MutagenFile(path)
            if audio and audio.info:
                return int(audio.info.length * 1000)  # в мс
        except:
            pass
        return 0