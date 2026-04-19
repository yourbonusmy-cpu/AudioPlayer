from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel


def format_time(ms):
    s = ms // 1000
    return f"{s//60}:{s%60:02d}"


def format_size(size):
    return f"{size / (1024*1024):.1f} MB"


class TrackItemWidget(QWidget):
    def __init__(self, track):
        super().__init__()

        layout = QHBoxLayout(self)

        self.name = QLabel(track.name)
        self.time = QLabel(format_time(track.duration or 0))
        self.size = QLabel(format_size(track.size or 0))

        layout.addWidget(self.name)
        layout.addStretch()
        layout.addWidget(self.time)
        layout.addWidget(self.size)