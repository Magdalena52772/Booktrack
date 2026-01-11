from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, QFile
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QVBoxLayout, QHeaderView, QSizePolicy

from data.repositories.genre_repo import GenresRepository
from charts.genre_chart import GenreChart

class GenresView(QWidget):
    """
    Klasa odpowiedzialna za obsługę warstwy prezentacji statystyk gatunków literackich.
    Zapewnia interakcję z danymi poprzez filtrowanie grup wiekowych oraz wizualizację wyników.
    """
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        loader = QUiLoader()
        ui_file = QFile("views/ui/GenresView.ui")
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui)
        
        # Wymuszenie na tabeli, by pożerała każde wolne miejsce
        self.ui.table_genres.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.repo = GenresRepository(conn)

        # Inicjalizacja dynamicznego wykresu (FigureCanvas)
        self.canvas = GenreChart(self.ui.chart_genres_popularity)
        layout = QVBoxLayout(self.ui.chart_genres_popularity)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.setup_connections()
        self.load_view()

    def setup_connections(self):
        """Konfiguracja połączeń między zdarzeniami interfejsu a metodami logiki."""
        self.ui.btn_refresh_genres.clicked.connect(self.load_view)
        self.ui.cb_age_group.currentTextChanged.connect(self.load_view)

    def load_view(self):
        """
        Metoda realizująca aktualizację widoku danych.
        Ustawia wyśrodkowany, panoramiczny wykres o niskim profilu.
        """
        
        try:
            self.statusMessage.emit("Updating statistics...", "info")
            
            age_group = self.ui.cb_age_group.currentText()
            genres = self.repo.get_all(age_group=age_group)
            
            # --- Wykres (Renderowanie bezpośrednie) ---
            self.canvas.update_chart(genres, age_group)

            # --- Tabela ---
            self.ui.table_genres.setSortingEnabled(False)
            self.ui.table_genres.setRowCount(len(genres))
            for row_i, genre in enumerate(genres):
                self.ui.table_genres.setItem(row_i, 0, QTableWidgetItem(genre.name))
                self.ui.table_genres.setItem(row_i, 1, QTableWidgetItem(str(genre.readers)))
                self.ui.table_genres.setItem(row_i, 2, QTableWidgetItem(f"⭐ {genre.avg_rating:.2f}"))
                self.ui.table_genres.setItem(row_i, 3, QTableWidgetItem(str(genre.books_read)))
                self.ui.table_genres.setItem(row_i, 4, QTableWidgetItem(f"{genre.percent_of_total_time:.1f}%"))
            
            self.ui.table_genres.setSortingEnabled(True)
            
            # Automatyczne rozciągnięcie kolumn do krawędzi
            self.ui.table_genres.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            self.statusMessage.emit(f"Stats loaded for: {age_group}", "success")
            
        except Exception as e:
            self.statusMessage.emit(f"Error: {str(e)}", "error")