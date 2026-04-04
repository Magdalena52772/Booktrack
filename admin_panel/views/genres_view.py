from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QVBoxLayout, QHeaderView, QSizePolicy, QProgressBar

from data.utils.status_manager import StatusMsg
from data.utils.ui_helpers import create_numeric_item, get_progress_bar_style, get_rating_color, load_ui, apply_tooltips
from data.repositories.genre_repo import GenresRepository
from charts.genre_chart import GenreChart
from PySide6.QtGui import QColor

class GenresView(QWidget):
    """
    Klasa odpowiedzialna za obsługę warstwy prezentacji statystyk gatunków literackich.
    Zapewnia interakcję z danymi poprzez filtrowanie grup wiekowych oraz wizualizację wyników.
    """
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Ładowanie interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/GenresView.ui")
        
        if not self.ui:
            print("Błąd ładowania UI!")
            return
        
        self.ui.table_genres.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.repo = GenresRepository(conn)

        # Inicjalizacja dynamicznego wykresu (FigureCanvas)
        self.canvas = GenreChart(self.ui.chart_genres_popularity)
        layout = QVBoxLayout(self.ui.chart_genres_popularity)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        # Inicjalizacja podpowiedzi i połączeń
        self.setup_tooltips()
        self.setup_connections()
        self.load_view()

    def setup_tooltips(self):
        """Konfiguracja opisów pomocniczych dla modułu gatunków przy użyciu helpera."""
        tooltips = {
            "cb_age_group": "Filter statistics by reader age category.",
            "btn_refresh_genres": "Force refresh of genre statistics and popularity chart.",
            "table_genres": "Summary of reader engagement and ratings per genre.",
            "chart_genres_popularity": "Visual representation of most read genres for the selected group."
        }
        apply_tooltips(self.ui, tooltips)

    def setup_connections(self):
        """Konfiguracja połączeń między zdarzeniami interfejsu a metodami logiki."""
        self.ui.btn_refresh_genres.clicked.connect(self.load_view)
        self.ui.cb_age_group.currentTextChanged.connect(self.load_view)

    def load_view(self):
        """Aktualizacja widoku z wykorzystaniem helperów UI."""
        age_group = self.ui.cb_age_group.currentText()
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", f"Genres ({age_group})"))
        
        try:
            genres = self.repo.get_all(age_group=age_group)
            
            # Resetowanie tabeli
            self.ui.table_genres.setSortingEnabled(False)
            self.ui.table_genres.setRowCount(0)

            if not genres:
                self.canvas.update_chart([], age_group)
                self.statusMessage.emit(*StatusMsg.get("NO_DATA", age_group))
                return

            self.canvas.update_chart(genres, age_group)
            self.ui.table_genres.setRowCount(len(genres))
            
            for row, genre in enumerate(genres):
                # Nazwa
                self.ui.table_genres.setItem(row, 0, QTableWidgetItem(genre.name))
                
                # Czytelnicy
                self.ui.table_genres.setItem(row, 1, create_numeric_item(genre.readers))
                
                # Ocena
                display_rating = f"⭐ {genre.avg_rating:.2f}" if genre.avg_rating > 0 else "N/A"
                rating_item = QTableWidgetItem(display_rating)
                rating_item.setTextAlignment(Qt.AlignCenter)
                # Wykorzystanie helpera kolorów
                rating_item.setForeground(QColor(get_rating_color(genre.avg_rating)))
                self.ui.table_genres.setItem(row, 2, rating_item)
                
                # Książki
                self.ui.table_genres.setItem(row, 3, create_numeric_item(genre.books_read))
                
                # Pasek postępu
                progress = QProgressBar()
                progress.setRange(0, 100)
                progress.setValue(int(genre.percent_of_total_time))
                progress.setFormat(f"{genre.percent_of_total_time}%")
                progress.setTextVisible(True)
                # Wykorzystanie helpera stylów
                progress.setStyleSheet(get_progress_bar_style()) 
                
                # Dodanie tooltipa bezpośrednio do widgetu paska postępu w tabeli
                progress.setToolTip(f"This genre accounts for {genre.percent_of_total_time}% of total reading time.")
                
                self.ui.table_genres.setCellWidget(row, 4, progress)

            # Finalizacja widoku
            self.ui.table_genres.setSortingEnabled(True)
            self.ui.table_genres.sortByColumn(3, Qt.DescendingOrder)
            self.ui.table_genres.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", f"Genres for {age_group}"))

        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))