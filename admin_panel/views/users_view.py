from PySide6.QtGui import QColor, Qt
from PySide6.QtCore import QEvent, Signal
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QFrame, QHeaderView, QPushButton, QLineEdit, QComboBox, QSpinBox

from data.utils.status_manager import StatusMsg
from data.repositories.statistics_repo import StatsRepository
from data.repositories.user_repo import UserRepository
from data.utils.helpers.ui_helpers import load_ui, apply_tooltips
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
            "input_search_user": "Search users by nickname, email, or full name.",
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
        table.setColumnWidth(3, 70)   # Books
        table.setColumnWidth(4, 180)  # Genres
        table.setColumnWidth(5, 70)   # PPD
        table.setColumnWidth(6, 150)  # Activity
        table.setColumnWidth(7, 90)   # Status
        table.setColumnWidth(8, 110)  # Date Joined

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
            
            # Pobranie średniej systemowej
            system_avg = self.stats_repo.get_system_wide_ppd(current_filter)

            # Metryki wydajnościowe (Zależne od filtra)
            user_ppd = profile.get("ppd", 0.0) 
            diff = user_ppd - system_avg
            
            # Kolor i status dla Current Performance
            if diff > 1.0:
                perf_status = "<b style='color: #27ae60;'>▲ ABOVE AVG</b>"
                ppd_color = "#27ae60"
            elif diff < -1.0:
                perf_status = "<b style='color: #e67e22;'>▼ BELOW AVG</b>"
                ppd_color = "#e67e22"
            else:
                perf_status = "<b style='color: #3498db;'>≈ ON PAR</b>"
                ppd_color = "#3498db"

            # Inne metryki (Niezależne od filtra)
            reading_potential = profile["active_ppd"]
            progress = profile['avg_progress']
            total_pages = profile['total_pages']
            reading_str = ", ".join(profile["reading_now"]) if profile["reading_now"] else "None"
            
            # Formatowanie wskaźnika streak
            streak = profile["streak"]
            streak_text = f"🔥 {streak} DAYS" if streak > 0 else "❄️ NO STREAK"
            streak_color = "#e67e22" if streak > 0 else "#95a5a6"

            filter_label = f"({current_filter.upper()})" if current_filter.lower() != "all" else "(ALL TIME)"

            # SZABLON HTML
            info_text = (
                f"<div style='font-family: Segoe UI, sans-serif; padding: 10px; color: #2c3e50;'>"
                f"  <div style='border-bottom: 2px solid #2c3e50; padding-bottom: 5px; margin-bottom: 15px;'>"
                f"      <table width='100%'><tr>"
                f"          <td>"
                f"              <span style='font-size: 18px;'><b>{full_name.upper()}</b></span> "
                f"              <span style='color: #7f8c8d; font-size: 13px; margin-left: 5px;'>(@{username})</span>"
                f"          </td>"
                f"          <td align='right' style='font-size: 13px; color: #7f8c8d;'>"
                f"              <b>EXT-ID: {profile['ext_id']}</b> &nbsp;|&nbsp; "
                f"              <b style='color: {streak_color};'>{streak_text}</b>"
                f"          </td>"
                f"      </tr></table>"
                f"  </div>"
                f"  <table width='100%' style='margin-bottom: 20px;' cellpadding='0' cellspacing='0'><tr>"
                f"      <td width='30%' style='vertical-align: top; border-right: 1px dotted #dcdfe3; padding-right: 15px;'>"
                f"          <div style='color: #7f8c8d; font-size: 10px; margin-bottom: 5px;'>ACCOUNT INFO</div>"
                f"          <div style='font-size: 12px; line-height: 1.6;'>"
                f"              👤 <b>AGE:</b> {profile['age']}<br>"
                f"              📅 <b>JOINED:</b> {profile['date_joined'][:10]}<br>"
                f"              🕒 <b>LAST ACTIVITY:</b> {profile['last_activity'][:16] if profile['last_activity'] else 'Never'}"
                f"          </div>"
                f"      </td>"
                f"      <td width='35%' style='vertical-align: top; border-right: 1px dotted #dcdfe3; padding-left: 15px; padding-right: 15px;' align='center'>"
                f"          <div style='color: #7f8c8d; font-size: 11px; margin-bottom: 5px;'>CURRENT PERFORMANCE {filter_label}</div>"
                f"          <div style='font-size: 28px; color: {ppd_color};'><b>{user_ppd:.1f}</b> <small style='font-size: 14px;'>PPD</small></div>"
                f"          <div style='font-size: 12px; margin-top: 4px;'>{perf_status} <span style='color: #95a5a6;'>(AVG: {system_avg:.1f})</span></div>"
                f"      </td>"
                f"      <td width='35%' style='vertical-align: top; padding-left: 15px;' align='center'>"
                f"          <div style='color: #7f8c8d; font-size: 11px; margin-bottom: 5px;'>CHALLENGE PROGRESS & POTENTIAL</div>"
                f"          <div style='font-size: 28px; color: #3498db;'><b>{progress}%</b></div>"
                f"          <div style='font-size: 12px; margin-top: 4px; color: #2c3e50;'>"
                f"              <b>Potential:</b> {reading_potential:.1f} active ppd<br>"
                f"              <b>Total Pages Read:</b> {total_pages}"
                f"          </div>"
                f"      </td>"
                f"  </tr></table>"
                f"  <div style='background-color: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #e9ecef;'>"
                f"      <div style='font-size: 12px; color: #2c3e50; margin-bottom: 8px;'>📚 <b>CURRENTLY READING:</b> <span style='color: #27ae60; font-weight: bold;'>{reading_str.upper()}</span></div>"
                f"      <div style='border-top: 1px solid #dee2e6; padding-top: 6px; color: #7f8c8d; font-size: 10px; line-height: 1.4;'>"
                f"          <b>Reading Potential:</b> The average pages per day calculated ONLY from days with logged activity.<br>"
                f"          <b>Performance {filter_label}:</b> Rolling average pages per day in the selected period."
                f"      </div>"
                f"  </div>"
                f"</div>"
            )
            
            self.ui.lbl_info.setText(info_text)
            self.statusMessage.emit(*StatusMsg.get("USER_DETAILS", full_name))
            
        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))