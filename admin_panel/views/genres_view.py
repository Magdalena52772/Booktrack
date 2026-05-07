from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QVBoxLayout, QHeaderView, QSizePolicy, QProgressBar
from PySide6.QtGui import QColor

from data.utils.status_manager import StatusMsg
from data.utils.helpers.ui_helpers import create_numeric_item, get_progress_bar_style, load_ui, apply_tooltips
from data.services.rating_service import RatingService
from data.repositories.genre_repo import GenresRepository
from charts.genre_chart import GenreChart

class GenresView(QWidget):
    """
    Klasa obsługująca warstwę prezentacji statystyk gatunków literackich.
    Umożliwia interakcję z danymi poprzez filtrowanie grup wiekowych oraz wizualizację wyników.
    """
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Inicjalizacja interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/GenresView.ui")
        if not self.ui:
            return
        
        self.ui.table_genres.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.repo = GenresRepository(conn)
        
        # Flaga sterująca mechanizmem opóźnionego ładowania (Lazy Loading)
        self.initialized = False

        # Konfiguracja kontenera dla wykresu dynamicznego
        self.canvas = GenreChart(self.ui.chart_genres_popularity)
        layout = QVBoxLayout(self.ui.chart_genres_popularity)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.setup_tooltips()
        self.setup_connections()
        
        # Wywołanie ładowania danych zostaje odroczone do momentu pierwszego wyświetlenia widgetu.

    def showEvent(self, event):
        """
        Obsługa zdarzenia wyświetlenia widgetu. 
        Inicjuje ładowanie danych przy pierwszej zmianie widoczności na aktywną.
        """
        super().showEvent(event)
        if not self.initialized:
            self.load_view()
            self.initialized = True

    def setup_tooltips(self):
        """Konfiguracja opisów pomocniczych (tooltips) dla elementów interfejsu."""
        tooltips = {
            "cb_age_group": "Filter statistics by reader age category.",
            "btn_refresh_genres": "Force refresh of genre statistics and popularity chart.",
            "table_genres": "Summary of reader engagement and ratings per genre.",
            "frame_stats_box": "Quick summary of user-declared preferences.",
            "lbl_total_declarations": "Total number of users who chose their favorite genres.",
            "lbl_most_declared": "The current leading genre based on user profile settings."
        }
        apply_tooltips(self.ui, tooltips)

    def setup_connections(self):
        """Definicja połączeń między sygnałami interfejsu a metodami logiki."""
        self.ui.btn_refresh_genres.clicked.connect(self.load_view)
        self.ui.cb_age_group.currentTextChanged.connect(self.load_view)

    def load_view(self):
        """
        Aktualizacja zawartości widoku. 
        Pobiera dane z repozytorium, odświeża wykres oraz wypełnia tabelę statystyk.
        """
        age_group = self.ui.cb_age_group.currentText()
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", f"Genres ({age_group})"))
        
        try:
            # Pobieranie danych z warstwy repozytorium
            genres = self.repo.get_all(age_group=age_group)

            # Sortowanie po procencie przed wypełnieniem tabeli
            genres = sorted(genres, key=lambda x: x.percent_of_total_time, reverse=True)

            # Tymczasowe zablokowanie sortowania na czas wypełniania tabeli
            self.ui.table_genres.setSortingEnabled(False)
            self.ui.table_genres.setRowCount(0)

            if not genres:
                self.canvas.update_chart([], age_group)
                self.ui.lbl_total_declarations.setText("Total picks: 0")
                self.ui.lbl_most_declared.setText("Favorite: None")
                self.statusMessage.emit(*StatusMsg.get("NO_DATA", age_group))
                return

            # Aktualizacja komponentu wykresu
            self.canvas.update_chart(genres, age_group)

            # Obliczanie sumarycznych statystyk deklaratywnych
            total_users_declared = sum(g.readers for g in genres)
            total_unique_users = self.repo.count_users_by_age_group(age_group)
            top_genre = max(genres, key=lambda x: x.readers)

            self.ui.lbl_total_declarations.setText(f"Total picks: {total_users_declared}\nUsers: {total_unique_users}")
            self.ui.lbl_most_declared.setText(f"Favorite: {top_genre.name}")

            # Wypełnianie tabeli danymi o realnej aktywności
            self.ui.table_genres.setRowCount(len(genres))
            for row, genre in enumerate(genres):
                # Nazwa
                self.ui.table_genres.setItem(row, 0, QTableWidgetItem(genre.name))
                
                # Czytelnicy
                self.ui.table_genres.setItem(row, 1, create_numeric_item(genre.readers))
                
                # Formatowanie oceny z uwzględnieniem koloru i ikony
                display_rating = f"⭐ {genre.avg_rating:.2f}" if genre.avg_rating > 0 else "N/A"
                rating_item = QTableWidgetItem(display_rating)
                rating_item.setTextAlignment(Qt.AlignCenter)
                # Wykorzystanie serwisu kolorów ocen
                rating_item.setForeground(QColor(RatingService.get_rating_color(genre.avg_rating)))
                self.ui.table_genres.setItem(row, 2, rating_item)
                
                # Książki
                self.ui.table_genres.setItem(row, 3, create_numeric_item(genre.books_read))
                
                # Integracja paska postępu odzwierciedlającego udział w czasie czytania
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

            # Przywrócenie sortowania i dopasowanie rozmiaru kolumn
            self.ui.table_genres.setSortingEnabled(True)
            self.ui.table_genres.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            
            self.statusMessage.emit(*StatusMsg.get("LOAD_SUCCESS", f"Genres for {age_group}"))

        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))