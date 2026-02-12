from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, QFile, Qt
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QVBoxLayout, QHeaderView, QSizePolicy, QProgressBar

from data.utils.status_manager import StatusMsg

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
        Aktualizuje wykres popularności oraz tabelę szczegółową dla wybranej grupy wiekowej."""
        age_group = self.ui.cb_age_group.currentText()
        
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", f"Genres ({age_group})"))
        
        try:
            BURGUNDY = "#630D16"
            
            genres = self.repo.get_all(age_group=age_group)
            
            # Zapewnienie równej szerokości kolumn przy każdym odświeżeniu
            header = self.ui.table_genres.horizontalHeader()
            for i in range(self.ui.table_genres.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.Stretch)

            if not genres:
                self.ui.table_genres.setRowCount(0)
                self.canvas.update_chart([], age_group)
                self.statusMessage.emit(*StatusMsg.get("NO_DATA", age_group))
                return

            self.canvas.update_chart(genres, age_group)
            self.ui.table_genres.setSortingEnabled(False)
            self.ui.table_genres.setRowCount(len(genres))
            
            for row, genre in enumerate(genres):
                # Mapowanie danych do komórek
                self.ui.table_genres.setItem(row, 0, QTableWidgetItem(genre.name))
                
                readers_item = QTableWidgetItem(str(genre.readers))
                readers_item.setTextAlignment(Qt.AlignCenter)
                self.ui.table_genres.setItem(row, 1, readers_item)
                
                rating_item = QTableWidgetItem(f"⭐ {genre.avg_rating:.2f}")
                rating_item.setTextAlignment(Qt.AlignCenter)
                self.ui.table_genres.setItem(row, 2, rating_item)
                
                books_item = QTableWidgetItem(str(genre.books_read))
                books_item.setTextAlignment(Qt.AlignCenter)
                self.ui.table_genres.setItem(row, 3, books_item)
                
                # Implementacja paska postępu
                progress = QProgressBar()
                progress.setRange(0, 100)
                val = int(genre.percent_of_total_time)
                progress.setValue(val)
                progress.setTextVisible(True)
                progress.setFormat(f"{genre.percent_of_total_time}%")
                
                # Zastosowanie stylu paska postępu
                progress.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid #D1D1D1;
                        border-radius: 4px;
                        background-color: #FDFDFD;
                        text-align: center;
                        color: black;
                        font-weight: bold;
                        height: 20px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {BURGUNDY};
                        border-radius: 3px;
                        border: none;
                    }}
                """)
                
                self.ui.table_genres.setCellWidget(row, 4, progress)

            self.ui.table_genres.setSortingEnabled(True)
            self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", f"Genres for {age_group}"))

        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))