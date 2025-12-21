import os
from PyQt6 import uic
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QWidget, QTableWidgetItem

from data.repositories.genre_repo import GenresRepository
from charts.genre_chart import GenreChartGenerator

class GenresView(QWidget):
    """
    Klasa odpowiedzialna za obsługę warstwy prezentacji statystyk gatunków literackich.
    Zapewnia interakcję z danymi poprzez filtrowanie grup wiekowych oraz wizualizację wyników.
    """
    statusMessage = pyqtSignal(str, str)

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        uic.loadUi("views/ui/GenresView.ui", self)
        self.repo = GenresRepository(conn)

        # Constraints for the chart display to prevent horizontal stretching
        self.chart_genres_popularity.setMinimumHeight(400)
        self.chart_genres_popularity.setMaximumWidth(450) # To ograniczy szerokość grafiki
        self.chart_genres_popularity.setAlignment(Qt.AlignmentFlag.AlignCenter) # Wycentrowanie

        self.setup_connections()
        self.load_view()

        # Ustalenie minimalnej wysokości dla pola wykresu w celu zapewnienia czytelności
        self.chart_genres_popularity.setMinimumHeight(380)
        self.chart_genres_popularity.setScaledContents(True)

        self.setup_connections()
        self.load_view()

    def setup_connections(self):
        """Konfiguracja połączeń między zdarzeniami interfejsu a metodami logiki."""
        self.btn_refresh_genres.clicked.connect(self.load_view)
        self.cb_age_group.currentTextChanged.connect(self.load_view)

    def load_view(self):
        """
        Metoda realizująca aktualizację widoku danych.
        Ustawia wyśrodkowany, panoramiczny wykres o niskim profilu.
        """
        
        try:
            self.statusMessage.emit("Updating statistics...", "info")
            
            age_group = self.cb_age_group.currentText()
            genres = self.repo.get_all(age_group=age_group)
            
            # --- Tabela (kod bez zmian) ---
            self.table_genres.setSortingEnabled(False)
            self.table_genres.setRowCount(len(genres))
            for row_i, genre in enumerate(genres):
                self.table_genres.setItem(row_i, 0, QTableWidgetItem(genre.name))
                self.table_genres.setItem(row_i, 1, QTableWidgetItem(str(genre.readers)))
                rating_item = QTableWidgetItem(f"⭐ {genre.avg_rating:.2f}")
                self.table_genres.setItem(row_i, 2, rating_item)
                self.table_genres.setItem(row_i, 3, QTableWidgetItem(str(genre.books_read)))
                self.table_genres.setItem(row_i, 4, QTableWidgetItem(f"{genre.percent_of_total_time:.1f}%"))
            self.table_genres.setSortingEnabled(True)
            self.table_genres.resizeColumnsToContents()
            self.table_genres.horizontalHeader().setStretchLastSection(True)

            # --- Wykres ---
            chart_path = GenreChartGenerator.generate_popularity_chart(genres, age_group)
            
            if chart_path and os.path.exists(chart_path):
                pixmap = QPixmap(chart_path)
                
                self.chart_genres_popularity.setMinimumHeight(300)
                self.chart_genres_popularity.setMaximumWidth(800)
                self.chart_genres_popularity.setAlignment(Qt.AlignmentFlag.AlignCenter)

                self.chart_genres_popularity.setPixmap(pixmap.scaled(
                    self.chart_genres_popularity.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            
            self.statusMessage.emit(f"Stats loaded for: {age_group}", "success")
            
        except Exception as e:
            self.statusMessage.emit(f"Error: {str(e)}", "error")