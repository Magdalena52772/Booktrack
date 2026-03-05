from datetime import datetime, date
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QColor, Qt
from PySide6.QtCore import Signal, QFile
from PySide6.QtWidgets import QWidget, QTableWidgetItem, QVBoxLayout, QFrame, QHeaderView

from data.utils.status_manager import StatusMsg

from data.repositories.user_repo import UserRepository

class UsersView(QWidget):
    # Sygnał do przesyłania wiadomości do paska statusu w oknie głównym
    statusMessage = Signal(str, str)

    def __init__(self, conn):
        super().__init__()
        # Ładowanie pliku interfejsu
        loader = QUiLoader()
        ui_file = QFile("views/ui/UsersView.ui")
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self) 
        ui_file.close()

        # Usunięcie ramki z głównego kontenera
        if hasattr(self.ui, "setFrameShape"):
            self.ui.setFrameShape(QFrame.Shape.NoFrame)

        # Ustawienie głównego układu
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui)
        
        self.conn = conn
        self.repo = UserRepository(conn)

        # Parametry paginacji
        self.current_page = 1
        self.page_size = 50 

        self.setup_table_ui()
        self.setup_connections()
        self.load_view()

    def mousePressEvent(self, event):
        """Obsługa kliknięcia poza tabelę w celu schowania detali."""
        focused_widget = self.childAt(event.pos())
        # Jeśli kliknięto w puste miejsce (nie w tabelę i nie w jej zawartość)
        if focused_widget is not self.ui.table_users and \
           focused_widget is not self.ui.table_users.viewport():
            self.ui.table_users.clearSelection()
            self.ui.lbl_info.setText("💡 Click on a user to view details...")
        super().mousePressEvent(event)

    def setup_table_ui(self):
        """Optymalizacja szerokości kolumn: liczby wąsko, tekst szeroko."""
        table = self.ui.table_users
        table.setFrameShape(QFrame.Shape.NoFrame)
        header = table.horizontalHeader()
        
        # Ustawienie trybu dopasowania do zawartości dla ID, Books, PPD i Statusu
        for col in [0, 3, 5, 7]:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            
        # Rozsądne szerokości dla dat i gatunków
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive) # Genres
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive) # Last Act
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Interactive) # Reg Date
        table.setColumnWidth(4, 120)
        table.setColumnWidth(6, 130)
        table.setColumnWidth(8, 100)

        # Rozciąganie dla Nazwy i Maila (podzielą się resztą miejsca)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Username
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Email
        
        header.setStretchLastSection(False)

    def setup_connections(self):
        """Łączy zdarzenia interfejsu."""
        self.ui.cb_time.currentTextChanged.connect(self.reset_pagination_and_load)
        self.ui.input_search_user.textChanged.connect(self.reset_pagination_and_load)
        self.ui.btn_reset.clicked.connect(self.reset_filters)
        self.ui.table_users.itemSelectionChanged.connect(self.display_user_details)
        
        # Obsługa paginacji
        self.ui.btn_first.clicked.connect(self.first_page)
        self.ui.btn_prev.clicked.connect(self.prev_page)
        self.ui.btn_next.clicked.connect(self.next_page)
        self.ui.btn_last.clicked.connect(self.last_page)
        self.ui.spin_page.valueChanged.connect(self.go_to_page)


    # --- METODY PAGINACJI ---
    def reset_pagination_and_load(self):
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
        self.ui.input_search_user.clear()
        self.ui.cb_time.setCurrentIndex(0) # 'all'
        self.current_page = 1
        self.load_view()

    def load_view(self):
        """Pobieranie danych użytkowników i aktualizacja tabeli interfejsu."""
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
                # 0. ID
                id_item = QTableWidgetItem()
                id_item.setData(Qt.ItemDataRole.DisplayRole, int(user.id))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.table_users.setItem(row_idx, 0, id_item)
                
                # 1. Nickname + Tooltip
                nick_item = QTableWidgetItem(user.username)
                nick_item.setData(Qt.ItemDataRole.UserRole, user.name)
                nick_item.setToolTip(user.username)
                self.ui.table_users.setItem(row_idx, 1, nick_item)
                
                # 2. Email + Tooltip
                email_raw = user.email if user.email else "-"
                email_item = QTableWidgetItem(email_raw)
                email_item.setForeground(QColor("#5d6d7e"))
                email_item.setToolTip(email_raw)
                self.ui.table_users.setItem(row_idx, 2, email_item)
                
                # 3. Books Read
                books_item = QTableWidgetItem(str(user.books_read))
                books_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.table_users.setItem(row_idx, 3, books_item)
                
                # 4. Genres + Tooltip HTML
                genres_list = user.favorite_genres if user.favorite_genres else []
                genres_str = ", ".join(genres_list) if genres_list else "-"
                genres_item = QTableWidgetItem(genres_str)
                if genres_list:
                    tooltip_html = "<b>Favourite genres:</b><br>• " + "<br>• ".join(genres_list)
                    genres_item.setToolTip(tooltip_html)
                self.ui.table_users.setItem(row_idx, 4, genres_item)

                # 5. Pages/day
                pages = f"{user.pages_per_day:.1f}" if user.pages_per_day is not None else "0.0"
                pages_item = QTableWidgetItem(pages)
                pages_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.table_users.setItem(row_idx, 5, pages_item)

                # 6. Last Activity + Tooltip
                last_act = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "-"
                last_act_item = QTableWidgetItem(last_act)
                last_act_item.setToolTip(last_act)
                self.ui.table_users.setItem(row_idx, 6, last_act_item)

                # 7. Status
                status_item = QTableWidgetItem(user.status)
                if user.status == "active":
                    status_item.setBackground(QColor("#d4edda")) 
                    status_item.setForeground(QColor("#155724")) 
                else:
                    status_item.setBackground(QColor("#f8d7da")) 
                    status_item.setForeground(QColor("#721c24")) 
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.table_users.setItem(row_idx, 7, status_item)
                
                # 8. Reg Date + Tooltip
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

    def display_user_details(self):
        """Pobieranie i wyświetlanie rozszerzonych danych o zaznaczonym użytkowniku."""
        try:
            selected_items = self.ui.table_users.selectedItems()
            if not selected_items:
                self.ui.lbl_info.setText("💡 Click on a user to view details...")
                return

            # Pobranie danych z widoku
            current_row = selected_items[0].row()
            user_id_raw = self.ui.table_users.item(current_row, 0).text()
            user_id = int(user_id_raw)
            nick_item = self.ui.table_users.item(current_row, 1)
            full_name = nick_item.data(Qt.ItemDataRole.UserRole) or "Unknown"
            
            # Pobranie statystyk bazowych
            streak = self.repo.get_user_streak(user_id)
            global_avg = self.repo.get_global_avg_ppd()
            table_ppd = float(self.ui.table_users.item(current_row, 5).text())

            # Zapytania dodatkowe
            cursor = self.conn.cursor()
            try:
                # 1. Obecnie czytane
                cursor.execute("SELECT title FROM books WHERE user_id = ? AND status = 'reading' LIMIT 3", (user_id,))
                reading_now = [r[0] for r in cursor.fetchall()]
                reading_str = ", ".join(reading_now) if reading_now else "None"

                # Dane profilowe i suma stron
                cursor.execute("""
                    SELECT 
                        u.external_id, u.birth_date, u.last_activity, u.date_joined,
                        (SELECT SUM(pages_read) FROM activity WHERE user_id = u.id) as total_pages,
                        AVG(CAST(c.progress_books AS FLOAT) / c.target_books * 100)
                    FROM users u
                    LEFT JOIN challenges c ON u.id = c.user_id AND c.status = 'active'
                    WHERE u.id = ? GROUP BY u.id
                """, (user_id,))
                u_data = cursor.fetchone()
            finally:
                cursor.close()

            if not u_data: return

            ext_id, birth_date_str, last_act_raw, reg_date_raw, total_pages_sum, avg_progress = u_data
            total_pages_sum = total_pages_sum or 0
            progress_str = f"{int(avg_progress)}%" if avg_progress else "0%"

            # --- OBLICZENIA POTENCJAŁU ---
            real_active_days = self.repo.get_active_reading_days(user_id)
            active_ppd = total_pages_sum / real_active_days

            # Wiek i Last Seen
            age = "N/A"
            if birth_date_str:
                try:
                    b_date = datetime.strptime(birth_date_str[:10], "%Y-%m-%d").date()
                    today = date.today()
                    age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
                except: pass

            last_seen_text, last_seen_color = "Never", "#95a5a6"
            if last_act_raw:
                last_date = datetime.strptime(last_act_raw[:10], "%Y-%m-%d").date()
                days_ago = (date.today() - last_date).days
                last_seen_text = "Today" if days_ago == 0 else f"{days_ago} day(s) ago"
                last_seen_color = "#2ecc71" if days_ago <= 7 else "#f1c40f" if days_ago <= 30 else "#e74c3c"

            # Renderowanie statusu potencjału
            diff = active_ppd - global_avg 
            ppd_status = "<b style='color: #27ae60;'>ABOVE AVG</b>" if diff > 0 else "<b style='color: #e67e22;'>BELOW AVG</b>"

            # --- RENDEROWANIE FINALNEGO HTML ---
            streak_html = f"<span style='color: #e67e22;'>🔥 <b>{streak} days</b></span>" if streak > 0 else "<span style='color: #95a5a6;'>❄️ No streak</span>"

            info_text = (
                f"<div style='font-family: Segoe UI, sans-serif; line-height: 140%;'>"
                f"  <div style='border-bottom: 1px solid #eee; margin-bottom: 6px; padding-bottom: 2px;'>"
                f"      <b style='color: #2c3e50; font-size: 13px;'>USER PROFILE DETAILS</b> "
                f"      <span style='color: #7f8c8d; font-size: 11px;'>(EXT-ID: {ext_id})</span>"
                f"      <span style='float: right; font-size: 12px;'>{streak_html}</span>"
                f"  </div>"
                f"  <div style='font-size: 12px; margin-bottom: 8px;'>"
                f"      <b style='color: #2c3e50; font-size: 13px;'>{full_name.upper()}</b><br>"
                f"      👤 <b>Age:</b> {age} &nbsp;|&nbsp; "
                f"      🏆 <b>Challenge:</b> <span style='color: #3498db;'>{progress_str}</span> &nbsp;|&nbsp; "
                f"      🕒 <b>Seen:</b> <span style='color: {last_seen_color}; font-weight: bold;'>{last_seen_text.upper()}</span>"
                f"  </div>"
                f"  <div style='background-color: #f0f7ff; padding: 8px; border-left: 4px solid #3498db; margin-bottom: 8px; font-size: 12px;'>"
                f"      <div style='margin-bottom: 3px;'>"
                f"          <b style='color: #2c3e50;'>READING POTENTIAL:</b> <span style='font-size: 14px;'><b>{active_ppd:.1f}</b></span> <small>pg/day</small>"
                f"          <span style='margin-left: 15px;'>{ppd_status}</span>"
                f"      </div>"
                f"      <div style='color: #555;'>"
                f"          <small>System Average (current filter): <b>{table_ppd:.1f}</b> | Global benchmark: {global_avg:.1f}</small><br>"
                f"          <small style='color: #888;'>Potential is based only on days with recorded activity.</small>"
                f"      </div>"
                f"  </div>"
                f"  <div style='font-size: 12px;'>📚 <b>Currently reading:</b> <span style='color: #2ecc71; font-weight: bold;'>{reading_str}</span></div>"
                f"</div>"
            )
            
            self.ui.lbl_info.setText(info_text)
            self.statusMessage.emit(*StatusMsg.get("USER_DETAILS", full_name))
        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))