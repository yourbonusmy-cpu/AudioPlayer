from pathlib import Path
from models.track import Track
from mutagen import File as MutagenFile


class MusicService:
    def __init__(self, session):
        self.session = session

    def scan(self, folder):
        folder_path = Path(folder)

        # ✔ только текущая папка (рекурсивно)
        files = {str(f) for f in folder_path.rglob("*.mp3")}

        # ✔ ВАЖНО: только треки ЭТОЙ папки
        db_tracks = self.session.query(Track).filter(
            Track.path.like(f"{folder_path}%")
        ).all()

        db_map = {t.path: t for t in db_tracks}

        # ======================
        # ADD NEW FILES
        # ======================
        for path in files:
            if path not in db_map:
                self.session.add(Track(
                    path=path,
                    name=Path(path).name,
                    size=Path(path).stat().st_size,
                    duration=self.get_duration(path),
                    is_missing=False
                ))
            else:
                db_map[path].is_missing = False

        # ======================
        # MARK MISSING (ТОЛЬКО В ЭТОЙ ПАПКЕ)
        # ======================
        for path, track in db_map.items():
            if path not in files:
                track.is_missing = True

        self.session.commit()

        # ✔ возвращаем только текущую папку
        return self.session.query(Track).filter(
            Track.path.like(f"{folder_path}%")
        ).all()

    def get_duration(self, path):
        try:
            audio = MutagenFile(path)
            if audio and audio.info:
                return int(audio.info.length * 1000)
        except:
            pass
        return 0