from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QCheckBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt


class TagFilter(QWidget):
    def __init__(self, on_change):
        super().__init__()

        self.on_change = on_change
        self.checks = {}

        layout = QVBoxLayout(self)

        self.button = QPushButton("Tags ▼")
        layout.addWidget(self.button)

        self.popup = QFrame()
        self.popup.setWindowFlags(Qt.WindowType.Popup)

        popup_layout = QVBoxLayout(self.popup)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)

        scroll.setWidget(self.container)
        popup_layout.addWidget(scroll)

        self.button.clicked.connect(self.toggle_popup)

    def toggle_popup(self):
        if self.popup.isVisible():
            self.popup.hide()
        else:
            pos = self.button.mapToGlobal(self.button.rect().bottomLeft())
            self.popup.move(pos)
            self.popup.resize(220, 260)
            self.popup.show()

    def load(self, tags):
        for i in reversed(range(self.container_layout.count())):
            w = self.container_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        self.checks = {}

        for tag in tags:
            cb = QCheckBox(tag.name)

            cb.stateChanged.connect(
                lambda state, t=tag: self.toggle_tag(t, state)
            )

            self.container_layout.addWidget(cb)
            self.checks[tag.id] = cb

    def toggle_tag(self, tag, state):
        self.on_change()

    def checked_ids(self):
        return [
            tag_id for tag_id, cb in self.checks.items()
            if cb.isChecked()
        ]