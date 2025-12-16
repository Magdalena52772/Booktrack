from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QTableWidgetItem
from data.repositories.genre_repo import GenresRepository

class GenresView(QWidget):
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        uic.loadUi("views/ui/GenresView.ui", self)
        self.repo = GenresRepository(conn)

        # podpięcie przycisku Refresh
        self.btn_refresh_genres.clicked.connect(self.load_view)

    def load_view(self):
        genres = self.repo.get_all()
        table = self.table_genres
        table.setRowCount(len(genres))

        for row_i, genre in enumerate(genres):
            table.setItem(row_i, 0, QTableWidgetItem(genre.name))
            table.setItem(row_i, 1, QTableWidgetItem(str(genre.readers)))
            table.setItem(row_i, 2, QTableWidgetItem(f"{genre.avg_rating:.2f}"))
            table.setItem(row_i, 3, QTableWidgetItem(str(genre.books_read)))
            table.setItem(row_i, 4, QTableWidgetItem(f"{genre.percent_of_total_time:.2f}"))

        self.statusMessage.emit("Genres list loaded.", "info")