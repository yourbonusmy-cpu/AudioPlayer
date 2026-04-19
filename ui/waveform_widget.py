from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor

class WaveformWidget(QWidget):
    def __init__(self, seek_cb):
        super().__init__()
        self.data = []
        self.progress = 0
        self.seek_cb = seek_cb

    def set_data(self, data):
        self.data = data
        self.update()

    def set_progress(self, p):
        self.progress = p
        self.update()

    def mousePressEvent(self, e):
        if self.data:
            self.seek_cb(e.position().x()/self.width())

    def paintEvent(self, e):
        if not self.data:
            return

        p = QPainter(self)
        w, h = self.width(), self.height()

        step = w / len(self.data)
        m = max(self.data) or 1

        for i, v in enumerate(self.data):
            x = i * step
            bar = (v/m) * h

            p.setPen(QColor('#00ffaa') if i/len(self.data) < self.progress else QColor('#444'))
            p.drawLine(int(x), int(h/2-bar/2), int(x), int(h/2+bar/2))