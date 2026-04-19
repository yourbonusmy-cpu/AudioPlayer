from PyQt6.QtWidgets import QApplication
import sys
from ui.player_window import PlayerWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = PlayerWindow()
    win.show()
    sys.exit(app.exec())