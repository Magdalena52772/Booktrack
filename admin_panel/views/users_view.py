from PySide6.QtGui import QColor, Qt
from PySide6.QtCore import QEvent, Signal
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QFrame, QHeaderView, QPushButton, QLineEdit, QComboBox, QSpinBox

from data.utils.status_manager import StatusMsg
from data.repositories.statistics_repo import StatsRepository
from data.repositories.user_repo import UserRepository
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips
from data.utils.formatters.user_profile_formatter import UserProfileFormatter
from data.services.user_performance_service import UserPerformanceService

class UsersView(QWidget):
    # Sygnał do przesyłania wiadomości do paska statusu w oknie głównym
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        
        # Ładowanie interfejsu z pliku .ui
        self.ui = load_ui(self, "views/ui/UsersView.ui")
        
        if not self.ui:
            print("Błąd ładowania UI!")
            return
        

        # Usunięcie ramki z głównego kontenera
        if hasattr(self.ui, "setFrameShape"):
            self.ui.setFrameShape(QFrame.Shape.NoFrame)

        # Rejestrujemy filtr dla głównego widgetu i kontenerów
        self.installEventFilter(self)
        self.ui.installEventFilter(self)
        
        # Jeśli w .ui masz ramkę o nazwie main_container, ona też musi filtrować:
        if hasattr(self.ui, 'main_container'):
             self.ui.main_container.installEventFilter(self)
        
        self.conn = conn
        self.repo = UserRepository(conn)
        self.stats_repo = StatsRepository(conn)

        # Parametry paginacji
        self.current_page = 1
        self.page_size = 50 

        self.setup_table_ui()
        self.setup_tooltips()
        self.setup_connections()
        self.load_view()

    def setup_tooltips(self):
        """Konfiguracja opisów pomocniczych dla panelu zarządzania użytkownikami."""
        tooltips = {
            "input_search_user": "Search users by nickname, email, full name, ID, or status.",
            "cb_time": "Filter user statistics (Pages/Day, Last Activity) by selected period.",
            "btn_reset": "Clear all search filters and return to default view.",
            "table_users": "Click a row to see detailed reading profile and engagement metrics.",
            "spin_page": "Jump directly to a specific page of the results.",
            "btn_first": "Go to the very first page.",
            "btn_last": "Go to the last available page.",
            "btn_next": "Show the next 50 users.",
            "btn_prev": "Go back to the previous page."
        }
        apply_tooltips(self.ui, tooltips)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            # Pobieramy widget bezpośrednio pod myszką
            child = self.childAt(event.pos())
            
            # 1. Sprawdzamy, czy kliknięcie trafiło w viewport tabeli (obszar z danymi)
            # Jeśli tak - NIE resetujemy (bo chcemy zaznaczyć wiersz)
            if child == self.ui.table_users.viewport():
                return super().eventFilter(obj, event)

            # 2. Sprawdzamy, czy kliknięty obiekt to interaktywny widget
            # (przyciski, inputy, nagłówki tabeli)
            interactive_widgets = (QPushButton, QLineEdit, QComboBox, QSpinBox, QHeaderView)
            
            # Jeśli kliknięto w coś, co nie jest interaktywne (np. tło, ramka, label informacyjny)
            # lub kliknięto w "pustkę" (child is None)
            if child is None or not isinstance(child, interactive_widgets):
                # Dodatkowy check: czy to nie jest wnętrze nagłówka tabeli?
                if child != self.ui.table_users.horizontalHeader().viewport():
                    self.reset_details_selection()

        return super().eventFilter(obj, event)

    def reset_details_selection(self):
        self.ui.table_users.clearSelection()
        self.ui.lbl_info.setText("💡 Click on a user to view details...")

    def setup_table_ui(self):
        """
        USTAWIENIA SZEROKOŚCI - TRYB FIXED WYMUSZA WARTOŚCI PIKSELOWE.
        """
        table = self.ui.table_users
        header = table.horizontalHeader()
        header.setStretchLastSection(False)

        # Mapowanie trybów (0:ID, 1:Nick, 2:Email, 3:Books, 4:Genres, 5:PPD, 6:Act, 7:Stat, 8:Date)
        # Nick i Email się rozciągają, reszta ma sztywne wymiary
        modes = {
            0: QHeaderView.ResizeMode.ResizeToContents,
            1: QHeaderView.ResizeMode.Stretch,
            2: QHeaderView.ResizeMode.Stretch,
            3: QHeaderView.ResizeMode.Fixed,
            4: QHeaderView.ResizeMode.Fixed,
            5: QHeaderView.ResizeMode.Fixed,
            6: QHeaderView.ResizeMode.Fixed,
            7: QHeaderView.ResizeMode.Fixed,
            8: QHeaderView.ResizeMode.Fixed
        }

        for col, mode in modes.items():
            header.setSectionResizeMode(col, mode)

        # TUTAJ USTALASZ SZEROKOŚCI W PIKSELACH
        table.setColumnWidth(3, 90)    # Books Read
        table.setColumnWidth(4, 180)   # Genres
        table.setColumnWidth(5, 100)   # Pages/Day
        table.setColumnWidth(6, 150)   # Activity
        table.setColumnWidth(7, 90)    # Status
        table.setColumnWidth(8, 110)   # Date Joined

    def setup_connections(self):
        """Łączy zdarzenia interfejsu."""
        self.ui.cb_time.currentTextChanged.connect(self.reset_pagination_and_load)
        self.ui.input_search_user.textChanged.connect(self.reset_pagination_and_load)
        self.ui.btn_reset.clicked.connect(self.reset_filters)

        # Obsługa kliknięcia w komórkę tabeli
        self.ui.table_users.cellClicked.connect(self.display_user_details)

        # Obsługa paginacji
        self.ui.btn_first.clicked.connect(self.first_page)
        self.ui.btn_prev.clicked.connect(self.prev_page)
        self.ui.btn_next.clicked.connect(self.next_page)
        self.ui.btn_last.clicked.connect(self.last_page)
        self.ui.spin_page.valueChanged.connect(self.go_to_page)

    # --- METODY PAGINACJI ---

    # --- METODY PAGINACJI ---
    def reset_pagination_and_load(self):
        """Resetowanie strony i czyszczenie detali przy zmianie filtrów."""
        self.ui.lbl_info.setText("💡 Click on a user to view details...")
        self.current_page = 1
        self.load_view()

    def first_page(self):
        self.current_page = 1
        self.load_view()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_view()

    def next_page(self):
        self.current_page += 1
        self.load_view()

    def last_page(self):
        search = self.ui.input_search_user.text().strip()
        total_users = self.repo.count_users(search_term=search)
        self.current_page = max(1, (total_users + self.page_size - 1) // self.page_size)
        self.load_view()

    def go_to_page(self, page):
        if page != self.current_page:
            self.current_page = page
            self.load_view()

    def reset_filters(self):
        """Przywrócenie ustawień domyślnych filtrów."""
        self.ui.input_search_user.clear()
        self.ui.cb_time.setCurrentIndex(0) 
        self.current_page = 1
        
        self.reset_details_selection() 
        
        self.load_view()

    def load_view(self):
        """Pobieranie danych i aktualizacja tabeli."""
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", "Users"))
        
        # INICJALIZACJA ZMIENNYCH
        total_pages = 1
        total_count = 0
        
        # Blokada odświeżania interfejsu i sygnałów w celu optymalizacji wydajności
        self.ui.table_users.setUpdatesEnabled(False)
        self.ui.table_users.setSortingEnabled(False)
        self.ui.table_users.blockSignals(True)

        try:
            # Pobranie parametrów filtrowania oraz obliczenie przesunięcia (offset)
            period = self.ui.cb_time.currentText()
            search_term = self.ui.input_search_user.text().strip()
            offset = (self.current_page - 1) * self.page_size

            # Pobranie zestawu danych z repozytorium
            users = self.repo.get_all(
                period=period,
                search_term=search_term,
                limit=self.page_size,
                offset=offset
            )
            
            # Wyznaczenie łącznej liczby rekordów i stron dla celów paginacji
            total_count = self.repo.count_users(search_term=search_term)
            total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)

            self.ui.table_users.setRowCount(len(users))

            # Iteracja po wynikach i wypełnianie komórek tabeli danymi
            for row_idx, user in enumerate(users):
                # ID
                id_item = QTableWidgetItem()
                id_item.setData(Qt.ItemDataRole.DisplayRole, int(user.id))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.table_users.setItem(row_idx, 0, id_item)
                
                # Nickname
                nick_item = QTableWidgetItem(user.username)
                nick_item.setData(Qt.ItemDataRole.UserRole, user.name)
                nick_item.setToolTip(user.username)
                self.ui.table_users.setItem(row_idx, 1, nick_item)
                
                # Email
                email_raw = user.email if user.email else "-"
                email_item = QTableWidgetItem(email_raw)
                email_item.setForeground(QColor("#5d6d7e"))
                email_item.setToolTip(email_raw)
                self.ui.table_users.setItem(row_idx, 2, email_item)
                
                # Books Read
                books_item = QTableWidgetItem(str(user.books_read))
                books_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.table_users.setItem(row_idx, 3, books_item)
                
                # Genres
                genres_list = user.favorite_genres if user.favorite_genres else []
                genres_str = ", ".join(genres_list) if genres_list else "-"
                genres_item = QTableWidgetItem(genres_str)
                if genres_list:
                    tooltip_html = "<b>Favourite genres:</b><br>• " + "<br>• ".join(genres_list)
                    genres_item.setToolTip(tooltip_html)
                self.ui.table_users.setItem(row_idx, 4, genres_item)

                # Pages/day
                pages = f"{user.pages_per_day:.1f}" if user.pages_per_day is not None else "0.0"
                pages_item = QTableWidgetItem(pages)
                pages_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.table_users.setItem(row_idx, 5, pages_item)

                # Last Activity
                last_act = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "-"
                last_act_item = QTableWidgetItem(last_act)
                last_act_item.setToolTip(last_act)
                self.ui.table_users.setItem(row_idx, 6, last_act_item)

                # Status
                status_item = QTableWidgetItem(user.status)
                if user.status == "active":
                    status_item.setBackground(QColor("#d4edda")) 
                    status_item.setForeground(QColor("#155724")) 
                else:
                    status_item.setBackground(QColor("#f8d7da")) 
                    status_item.setForeground(QColor("#721c24")) 
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.table_users.setItem(row_idx, 7, status_item)
                
                # Reg Date
                reg_date = user.date_joined.strftime("%Y-%m-%d") if user.date_joined else "-"
                reg_item = QTableWidgetItem(reg_date)
                reg_item.setToolTip(reg_date)
                self.ui.table_users.setItem(row_idx, 8, reg_item)

            # Aktualizacja liczników stron i stanu przycisków nawigacyjnych
            self.ui.lbl_page_info.setText(f"z {total_pages}")
            self.ui.btn_first.setEnabled(self.current_page > 1)
            self.ui.btn_prev.setEnabled(self.current_page > 1)
            self.ui.btn_next.setEnabled(self.current_page < total_pages)
            self.ui.btn_last.setEnabled(self.current_page < total_pages)

        except Exception as e:
            # Emisja komunikatu o błędzie do paska statusu
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))
        
        finally:
            # Przywrócenie interakcji z tabelą i odświeżania widoku
            self.ui.table_users.setSortingEnabled(True)
            self.ui.table_users.blockSignals(False)
            self.ui.table_users.setUpdatesEnabled(True)
            
            # Synchronizacja kontrolki wyboru strony bez wyzwalania sygnałów
            self.ui.spin_page.blockSignals(True)
            self.ui.spin_page.setMaximum(total_pages)
            self.ui.spin_page.setValue(self.current_page)
            self.ui.spin_page.blockSignals(False)
            
            self.statusMessage.emit(*StatusMsg.get("VIEW_LOADED_COUNT", f"Users total: {total_count}"))

    def display_user_details(self, row, column):
        """Pobieranie i wyświetlanie profilu użytkownika"""
        try:
            # Pobranie danych identyfikacyjnych z zaznaczonego wiersza
            user_id_item = self.ui.table_users.item(row, 0)
            if not user_id_item: 
                return
            
            user_id = int(user_id_item.text())
            full_name = self.ui.table_users.item(row, 1).data(Qt.ItemDataRole.UserRole) or "Unknown Name"
            username = self.ui.table_users.item(row, 1).text()
            current_filter = self.ui.cb_time.currentText()

            # Pobranie przetworzonych danych profilowych z repozytorium
            profile = self.repo.get_detailed_user_profile(user_id)
            if not profile:
                return

            # Pobranie średniej systemowej (zawsze ostatnie 30 dni - SSOT benchmark)
            system_avg = self.stats_repo.get_system_wide_ppd("month")

            # Metryki wydajnościowe użytkownika (zależą od wybranego filtra)
            user_ppd = UserPerformanceService.calculate_systematic_ppd(user_id, self.conn, current_filter)

            # Formatowanie profilu HTML
            info_text = UserProfileFormatter.format_profile(profile, user_ppd, system_avg, current_filter)
            
            self.ui.lbl_info.setText(info_text)
            self.statusMessage.emit(*StatusMsg.get("USER_DETAILS", full_name))
            
        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))