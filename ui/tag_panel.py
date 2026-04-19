from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QCheckBox,
    QScrollArea, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt


class TagPanel(QWidget):
    def __init__(self, session, on_change):
        super().__init__()

        self.session = session
        self.on_change = on_change
        self.current_track = None

        layout = QVBoxLayout(self)

        # ===== TOP (фиксированный) =====
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)

        self.input = QLineEdit()
        self.input.setPlaceholderText("New tag...")

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedWidth(40)

        top_layout.addWidget(self.input)
        top_layout.addWidget(self.add_btn)

        layout.addWidget(top_widget)

        # ===== SCROLL AREA =====
        self.container_layout = QVBoxLayout()
        self.container_layout.setSpacing(4)

        container = QWidget()
        container.setLayout(self.container_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        layout.addWidget(scroll)

        self.checkboxes = {}

        # signals
        self.add_btn.clicked.connect(self.create_tag)

    # ================= LOAD =================
    def load_tags(self, tags):
        # очистка
        for i in reversed(range(self.container_layout.count())):
            w = self.container_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        self.checkboxes = {}

        for tag in tags:
            row_layout = QHBoxLayout()

            cb = QCheckBox(tag.name)

            cb.stateChanged.connect(
                lambda state, t=tag: self.toggle_tag(t, state)
            )

            # кнопка удаления
            delete_btn = QPushButton("🗑")
            delete_btn.setFixedWidth(30)

            delete_btn.clicked.connect(
                lambda _, t=tag: self.delete_tag(t)
            )

            row_layout.addWidget(cb)
            row_layout.addStretch()
            row_layout.addWidget(delete_btn)

            row_widget = QWidget()
            row_widget.setLayout(row_layout)

            self.container_layout.addWidget(row_widget)

            self.checkboxes[tag.id] = cb

    # ================= TRACK =================
    def set_track(self, track):
        self.current_track = track
        self.sync()

    def sync(self):
        if not self.current_track:
            return

        for tag_id, cb in self.checkboxes.items():
            cb.setChecked(
                any(t.id == tag_id for t in self.current_track.tags)
            )

    # ================= CREATE =================
    def create_tag(self):
        from models.tag import Tag

        name = self.input.text().strip()
        if not name:
            return

        if not self.session.query(Tag).filter_by(name=name).first():
            self.session.add(Tag(name=name))
            self.session.commit()

        self.input.clear()
        self.on_change()

    # ================= TOGGLE =================
    def toggle_tag(self, tag, state):
        if not self.current_track:
            return

        if state == Qt.CheckState.Checked.value:
            if tag not in self.current_track.tags:
                self.current_track.tags.append(tag)
        else:
            if tag in self.current_track.tags:
                self.current_track.tags.remove(tag)

        self.session.commit()

    # ================= DELETE =================
    def delete_tag(self, tag):
        # подтверждение
        msg = QMessageBox(self)
        msg.setWindowTitle("Удаление тега")
        msg.setText(f"Вы точно хотите удалить тег:\n{tag.name}")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )

        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        # ввод названия
        text, ok = QInputDialog.getText(
            self,
            "Подтверждение удаления",
            f"Введите название тега для удаления:\n{tag.name}"
        )

        if not ok:
            return

        if text != tag.name:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Название тега не совпадает"
            )
            return

        # удаление
        self.session.delete(tag)
        self.session.commit()

        self.on_change()