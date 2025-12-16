"""
BookTrack Admin Panel — entry point
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from views.main_window import MainWindow
from data.database import initialize_database, get_connection


# poprawia skalowanie bez używania usuniętych flag Qt5
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from data.database import initialize_database, get_connection

def main():
    initialize_database()
    conn = get_connection()

    app = QApplication(sys.argv)

    window = MainWindow(conn)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()