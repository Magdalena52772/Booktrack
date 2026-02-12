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
        """Konfiguruje wygląd tabeli. Zoptymalizowano tryby zmiany rozmiaru kolumn."""
        table = self.ui.table_users
        table.setFrameShape(QFrame.Shape.NoFrame)
        header = table.horizontalHeader()
        
        # Wymuszenie trybu Interactive dla wszystkich kolumn (usuwa ALERT testu diagnostycznego)
        for i in range(header.count()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            
        # Ustawienie rozciągania dla kluczowych kolumn tekstowych
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Name
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Genres
        
        # Wyłączenie automatycznego rozciągania ostatniej sekcji
        header.setStretchLastSection(False)

    def setup_connections(self):
        """Łączy zdarzenia interfejsu."""
        self.ui.cb_time.currentTextChanged.connect(self.reset_pagination_and_load)
        self.ui.input_search_user.textChanged.connect(self.reset_pagination_and_load)
        self.ui.btn_reset.clicked.connect(self.reset_filters)
        self.ui.table_users.itemSelectionChanged.connect(self.display_user_details)
        self.ui.btn_prev.clicked.connect(self.prev_page)
        self.ui.btn_next.clicked.connect(self.next_page)

    def reset_pagination_and_load(self):
        self.current_page = 1
        self.load_view()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_view()

    def next_page(self):
        self.current_page += 1
        self.load_view()

    def reset_filters(self):
        self.ui.input_search_user.clear()
        self.ui.cb_time.setCurrentIndex(2)
        self.current_page = 1
        self.load_view()

    def load_view(self):
        """Pobiera dane użytkowników i aktualizuje tabelę w interfejsie."""
        self.statusMessage.emit(*StatusMsg.get("LOAD_START", "Users"))
        
        # Tymczasowe wyłączenie odświeżania tabeli w celu zwiększenia wydajności
        self.ui.table_users.setUpdatesEnabled(False)
        self.ui.table_users.setSortingEnabled(False)
        self.ui.table_users.blockSignals(True)

        try:
            period = self.ui.cb_time.currentText()
            search_term = self.ui.input_search_user.text().strip()
            offset = (self.current_page - 1) * self.page_size

            users = self.repo.get_all(
                period=period,
                search_term=search_term,
                limit=self.page_size,
                offset=offset
            )

            self.ui.table_users.setRowCount(len(users))

            for row_idx, user in enumerate(users):
                id_item = QTableWidgetItem()
                id_item.setData(Qt.ItemDataRole.DisplayRole, int(user.id))
                
                self.ui.table_users.setItem(row_idx, 0, id_item)
                self.ui.table_users.setItem(row_idx, 1, QTableWidgetItem(user.name))
                self.ui.table_users.setItem(row_idx, 2, QTableWidgetItem(str(user.age)))
                self.ui.table_users.setItem(row_idx, 3, QTableWidgetItem(str(user.books_read)))
                
                genres_str = ", ".join(user.favorite_genres) if user.favorite_genres else "-"
                self.ui.table_users.setItem(row_idx, 4, QTableWidgetItem(genres_str))

                pages = f"{user.pages_per_day:.1f}" if user.pages_per_day is not None else "0.0"
                self.ui.table_users.setItem(row_idx, 5, QTableWidgetItem(pages))

                last_act = user.last_activity.strftime("%Y-%m-%d %H:%M") if user.last_activity else "-"
                self.ui.table_users.setItem(row_idx, 6, QTableWidgetItem(last_act))

                # Status konta
                status_item = QTableWidgetItem(user.status)
                if user.status == "active":
                    status_item.setBackground(QColor("#d4edda")) 
                    status_item.setForeground(QColor("#155724")) 
                else:
                    status_item.setBackground(QColor("#f8d7da")) 
                    status_item.setForeground(QColor("#721c24")) 
                self.ui.table_users.setItem(row_idx, 7, status_item)
                
                reg_date = user.register_date.strftime("%Y-%m-%d") if user.register_date else "-"
                self.ui.table_users.setItem(row_idx, 8, QTableWidgetItem(reg_date))

            # Aktualizacja UI nawigacji
            self.ui.lbl_page_info.setText(f"Page: {self.current_page}")
            self.ui.btn_prev.setEnabled(self.current_page > 1)
            self.ui.btn_next.setEnabled(len(users) == self.page_size)
            
            filter_info = f"{period}" + (f", Search: {search_term}" if search_term else "")
            display_text = f"Users, {len(users)} record(s) ({filter_info})"

            if not users:
                self.statusMessage.emit(*StatusMsg.get("NO_DATA", filter_info))
            else:
                self.statusMessage.emit(*StatusMsg.get("VIEW_LOADED_COUNT", display_text))

        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))
        
        finally:
            # Przywrócenie standardowego działania tabeli i odświeżenie widoku
            self.ui.table_users.setSortingEnabled(True)
            self.ui.table_users.blockSignals(False)
            self.ui.table_users.setUpdatesEnabled(True)
            self.ui.table_users.sortByColumn(8, Qt.SortOrder.DescendingOrder)
            self.ui.table_users.viewport().update()

    def display_user_details(self):
        """Pobiera i wyświetla rozszerzone dane o zaznaczonym użytkowniku."""
        try:
            selected_items = self.ui.table_users.selectedItems()
            if not selected_items:
                self.ui.lbl_info.setText("💡 Click on a user to view details...")
                return

            # Pobranie podstawowych informacji z wiersza
            row = selected_items[0].row()
            user_id = self.ui.table_users.item(row, 0).text()
            user_name = self.ui.table_users.item(row, 1).text()
            
            cursor = self.conn.cursor()

            # Pobranie książek w trakcie czytania
            cursor.execute("""
                SELECT title FROM books 
                WHERE user_id = ? AND status = 'reading' 
                LIMIT 3
            """, (user_id,))
            reading_now = [r[0] for r in cursor.fetchall()]
            reading_str = ", ".join(reading_now) if reading_now else "None"

            # Pobranie postępu wyzwań
            cursor.execute("""
                SELECT AVG(CAST(progress_books AS FLOAT) / target_books * 100) 
                FROM challenges 
                WHERE user_id = ? AND status = 'active'
            """, (user_id,))
            avg_progress = cursor.fetchone()[0]
            progress_str = f"{int(avg_progress)}%" if avg_progress is not None else "0%"

            # Pobranie danych profilu i Last Activity
            cursor.execute("""
                SELECT external_id, birth_date, last_activity 
                FROM users 
                WHERE id = ?
            """, (user_id,))
            u_data = cursor.fetchone()
            
            ext_id = u_data[0] if u_data else "N/A"
            birth_date_str = u_data[1] if u_data else None
            last_act_raw = u_data[2] if u_data else None
            
            # Obliczanie wieku
            age = "N/A"
            if birth_date_str:
                try:
                    # SQLite DATE format: YYYY-MM-DD
                    b_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
                    today = date.today()
                    age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
                except:
                    age = "N/A"

            # Logika LAST SEEN z kolorowaniem
            last_seen_text = "Never"
            last_seen_color = "#95a5a6"

            if last_act_raw:
                try:
                    # Obsługa formatu TIMESTAMP (YYYY-MM-DD HH:MM:SS)
                    last_date_str = last_act_raw.split(" ")[0]
                    last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                    days_ago = (date.today() - last_date).days
                    
                    if days_ago == 0:
                        last_seen_text = "Today"
                    else:
                        last_seen_text = f"{days_ago} day(s) ago"
                    
                    # Ramy czasowe
                    if days_ago <= 7:
                        last_seen_color = "#2ecc71"
                    elif days_ago <= 30:
                        last_seen_color = "#f1c40f"
                    else:
                        last_seen_color = "#e74c3c"
                except:
                    last_seen_text = "Check Activity"

            # Budowanie widoku HTML
            info_text = (
                f"<div style='line-height: 150%;'>"
                f"<b>User Profile Details</b> (Ext-ID: {ext_id})<br>"
                f"👤 <b>Age:</b> {age} | 📚 <b>Currently reading:</b> <span style='color: #2ecc71;'>{reading_str}</span><br>"
                f"🏆 <b>Avg Challenge Progress:</b> <span style='color: #3498db;'>{progress_str}</span> | "
                f"🕒 <b>Last Activity:</b> <span style='color: {last_seen_color}; font-weight: bold;'>{last_seen_text}</span>"
                f"</div>"
            )
            self.ui.lbl_info.setText(info_text)
            self.statusMessage.emit(*StatusMsg.get("USER_DETAILS", user_name))
                
        except Exception as e:
            self.statusMessage.emit(*StatusMsg.get("DB_ERROR", str(e)))