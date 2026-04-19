import json
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from services.db import Session
from services.music_service import MusicService
from services.waveform_service import WaveformService

from ui.track_item_widget import TrackItemWidget
from ui.waveform_widget import WaveformWidget
from ui.tag_filter import TagFilter
from ui.tag_panel import TagPanel

from models.track import Track
from models.tag import Tag
from models.setting import Setting


class PlayerWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.session = Session()
        self.music_service = MusicService(self.session)
        self.wave_service = WaveformService()

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.setAcceptDrops(True)
        self.player.mediaStatusChanged.connect(self.on_media_status)
        self.player.setAudioOutput(self.audio)

        self.active_track_id = None
        self.current_track = None
        self.is_media_ready = False

        self.volume_timer = QTimer()
        self.volume_timer.setSingleShot(True)
        self.volume_timer.timeout.connect(self.save_volume)

        self.init_ui()
        self.apply_styles()

        self.load_settings()
        self.load_all()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(200)

        # debounce поиск
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filter)

    # ---------------- UI ----------------
    def init_ui(self):
        self.setWindowTitle("Music Player")
        self.resize(1100, 700)

        root = QVBoxLayout(self)

        # ===== TOP =====
        self.title = QLabel("No track")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setFont(QFont("Arial", 16, QFont.Weight.Bold))

        self.wave = WaveformWidget(self.seek)
        self.wave.setMinimumHeight(120)

        self.time = QLabel("0:00 / 0:00")
        self.time.setAlignment(Qt.AlignmentFlag.AlignCenter)

        controls = QHBoxLayout()

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.valueChanged.connect(
            lambda: self.volume_timer.start(500)
        )

        self.prev = QPushButton("⏮")
        self.play = QPushButton("▶")
        self.next = QPushButton("⏭")

        self.play.setFixedSize(60, 60)
        self.prev.setFixedSize(40, 40)
        self.next.setFixedSize(40, 40)

        controls.addStretch()
        controls.addWidget(self.prev)
        controls.addWidget(self.play)
        controls.addWidget(self.next)
        controls.addWidget(self.volume_slider)
        controls.addStretch()

        root.addWidget(self.title)
        root.addWidget(self.wave)
        root.addWidget(self.time)
        root.addLayout(controls)

        # ===== MAIN AREA =====
        splitter = QSplitter()

        # LEFT
        left = QWidget()
        left_layout = QVBoxLayout(left)

        top_controls = QHBoxLayout()

        self.btn_folder = QPushButton("📂")
        self.btn_refresh = QPushButton("⟳")

        self.btn_folder.setToolTip("Выбрать папку")
        self.btn_refresh.setToolTip("Обновить список")

        self.btn_folder.setFixedWidth(40)
        self.btn_refresh.setFixedWidth(40)

        top_controls.addWidget(self.btn_folder)
        top_controls.addWidget(self.btn_refresh)
        top_controls.addStretch()

        left_layout.addLayout(top_controls)


        self.search = QLineEdit()
        self.search.setPlaceholderText("Search music...")

        self.filter = TagFilter(self.apply_filter)

        self.list = QListWidget()

        left_layout.addWidget(self.search)
        left_layout.addWidget(self.filter)
        left_layout.addWidget(self.list)

        # RIGHT
        self.tag_panel = TagPanel(self.session, self.reload_tags)

        splitter.addWidget(left)
        splitter.addWidget(self.tag_panel)
        splitter.setSizes([700, 300])

        root.addWidget(splitter)

        # signals
        self.play.clicked.connect(self.toggle)
        self.prev.clicked.connect(self.prev_track)
        self.next.clicked.connect(self.next_track)

        self.volume_slider.valueChanged.connect(self.on_volume_change)

        self.btn_folder.clicked.connect(self.choose_folder)
        self.btn_refresh.clicked.connect(self.refresh_tracks)

        self.list.itemClicked.connect(self.play_track)

        self.search.textChanged.connect(self.on_search_changed)

    # ---------------- STYLE ----------------
    def apply_styles(self):
        self.setStyleSheet("""
        
        QPushButton {
            background-color: #1db954;
            border-radius: 8px;
            padding: 4px;
        }
        
        QPushButton:hover {
            background-color: #1ed760;
        }
        
        QWidget {
            background-color: #121212;
            color: #ffffff;
        }

        QPushButton {
            background-color: #1db954;
            border-radius: 20px;
            color: white;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #1ed760;
        }

        QLineEdit {
            background-color: #2a2a2a;
            border-radius: 8px;
            padding: 6px;
        }

        QListWidget {
            background-color: #181818;
            border: none;
        }

        QListWidget::item:selected {
            background-color: #1db954;
        }
        """)

    def on_media_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer

        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            self.is_media_ready = True

        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.next_track()

    # ---------------- SEARCH ----------------
    def on_search_changed(self):
        self.search_timer.start(500)

    # ---------------- DATA ----------------
    def save_current_track_state(self):
        if not self.current_track:
            return

        # позиция
        self.current_track.last_position = self.player.position()

        # play count
        self.current_track.play_count = (self.current_track.play_count or 0) + 1

        # флаг
        self.current_track.last_played = True

        self.session.commit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()

        if not urls:
            return

        path = urls[0].toLocalFile()

        import os
        if not os.path.isdir(path):
            return

        # сохраняем папку
        setting = self.session.query(Setting).first()
        setting.music_dir = path
        self.session.commit()

        self.music_dir = path

        self.refresh_tracks()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку с музыкой",
            self.music_dir
        )

        if not folder:
            return

        # сохраняем в БД
        setting = self.session.query(Setting).first()
        setting.music_dir = folder
        self.session.commit()

        self.music_dir = folder

        self.refresh_tracks()

    def refresh_tracks(self):
        try:
            self.tracks = self.music_service.scan(self.music_dir)

            self.apply_filter()

            QMessageBox.information(
                self,
                "Обновлено",
                "Список треков обновлен"
            )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Ошибка",
                str(e)
            )

    def save_volume(self):
        s = self.session.query(Setting).first()
        s.volume = self.audio.volume()
        self.session.commit()

    def load_settings(self):
        s = self.session.query(Setting).first()
        if not s:
            from pathlib import Path
            s = Setting(music_dir=str(Path.home() / "Music"))
            self.session.add(s)
            self.session.commit()

        self.audio.setVolume(s.volume or 0.5)
        self.volume_slider.setValue(int((s.volume or 0.5) * 100))
        self.music_dir = s.music_dir

    def load_all(self):
        self.tracks = self.music_service.scan(self.music_dir)
        self.reload_tags()
        self.apply_filter()
        QTimer.singleShot(0, self.restore_last_track)

    def reload_tags(self):
        tags = self.session.query(Tag).all()
        self.filter.load(tags)
        self.tag_panel.load_tags(tags)

    # ---------------- FILTER ----------------
    def apply_filter(self):
        text = self.search.text().lower()
        tag_ids = self.filter.checked_ids()

        self.list.clear()

        selected_item = None

        for t in self.tracks:

            # -------------------------
            # SEARCH FILTER
            # -------------------------
            if text and text not in t.name.lower():
                continue

            # -------------------------
            # TAG FILTER
            # -------------------------
            if tag_ids:
                track_tag_ids = [tag.id for tag in t.tags]
                if not all(i in track_tag_ids for i in tag_ids):
                    continue

            # -------------------------
            # CREATE ITEM
            # -------------------------
            item = QListWidgetItem()
            widget = TrackItemWidget(t)

            item.setSizeHint(widget.sizeHint())
            item.setData(1, t.id)

            self.list.addItem(item)
            self.list.setItemWidget(item, widget)

            # -------------------------
            # RESTORE CURRENT TRACK SELECTION
            # -------------------------
            if self.current_track and t.id == self.current_track.id:
                selected_item = item

        # -------------------------
        # APPLY SELECTION AFTER BUILD
        # -------------------------
        if selected_item:
            self.list.setCurrentItem(selected_item)
            self.list.scrollToItem(selected_item)

    # ---------------- PLAY ----------------
    def play_track(self, item):
        if self.current_track:
            self.current_track.last_played = False
            self.current_track.last_position = self.player.position()
            self.session.commit()

        track_id = item.data(1)
        self.active_track_id = track_id
        self.current_track = self.session.get(Track, track_id)

        self.title.setText(self.current_track.name)
        self.is_media_ready = False
        self.player.setSource(QUrl.fromLocalFile(self.current_track.path))
        self.player.play()
        self.play.setText("⏸")

        if self.current_track.waveform:
            wf = json.loads(self.current_track.waveform)
        else:
            wf = self.wave_service.generate(self.current_track.path)
            self.current_track.waveform = json.dumps(wf)
            self.session.commit()

        self.wave.set_data(wf)
        self.tag_panel.set_track(self.current_track)

    def toggle(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.save_current_track_state()
            self.player.pause()
            self.play.setText("▶")
        else:
            self.player.play()
            self.play.setText("⏸")

    def prev_track(self):
        self.save_current_track_state()
        row = self.list.currentRow()
        if row > 0:
            self.list.setCurrentRow(row - 1)
            self.play_track(self.list.currentItem())

    def next_track(self):
        self.save_current_track_state()
        row = self.list.currentRow()
        if row < self.list.count() - 1:
            self.list.setCurrentRow(row + 1)
            self.play_track(self.list.currentItem())

    def seek(self, ratio):
        if not self.player.duration():
            return

        position = int(self.player.duration() * ratio)

        # ✔ ВАЖНО: ждём готовности
        if self.is_media_ready:
            self.player.setPosition(position)
        else:
            QTimer.singleShot(200, lambda: self.player.setPosition(position))

    def update_progress(self):
        if self.player.duration():
            pos = self.player.position()
            dur = self.player.duration()

            self.wave.set_progress(pos / dur)

            def fmt(ms):
                s = ms // 1000
                return f"{s//60}:{s%60:02d}"

            self.time.setText(f"{fmt(pos)} / {fmt(dur)}")

    def on_volume_change(self, value):
        volume = value / 100.0
        self.audio.setVolume(volume)

    def restore_last_track(self):
        track = self.session.query(Track) \
            .filter_by(last_played=True) \
            .first()

        if not track:
            return

        self.current_track = track

        self.title.setText(track.name)

        self.player.setSource(QUrl.fromLocalFile(track.path))

        # ✔ ВАЖНО: синхронизация списка
        self.select_track_in_list(track)

        def start():
            self.player.setPosition(track.last_position or 0)
            self.player.play()
            self.play.setText("⏸")

        self.player.mediaStatusChanged.connect(
            lambda s: start() if s == QMediaPlayer.MediaStatus.LoadedMedia else None
        )

        # waveform
        import json
        if track.waveform:
            self.wave.set_data(json.loads(track.waveform))

    def select_track_in_list(self, track):
        for i in range(self.list.count()):
            item = self.list.item(i)

            if item.data(1) == track.id:
                self.list.setCurrentItem(item)
                self.list.setCurrentRow(i)
                self.list.scrollToItem(item)
                break
