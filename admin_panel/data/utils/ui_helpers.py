from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
from PySide6.QtWidgets import QTableWidgetItem, QVBoxLayout, QProgressBar

def load_ui(widget_instance, file_path):
    """
    Uniwersalny loader dla plików .ui. 
    Wczytuje interfejs i osadza go w głównym layoucie widgetu.
    """
    loader = QUiLoader()
    ui_file = QFile(file_path)
    if not ui_file.open(QFile.ReadOnly):
        return None
    
    ui = loader.load(ui_file, widget_instance)
    ui_file.close()
    
    # Automatyczne dodanie do layoutu widoku
    layout = QVBoxLayout(widget_instance)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(ui)
    return ui

def apply_tooltips(ui_object, tooltips_dict):
    """Masowo przypisuje podpowiedzi do elementów UI na podstawie słownika."""
    for widget_name, text in tooltips_dict.items():
        widget = getattr(ui_object, widget_name, None)
        if widget:
            widget.setToolTip(text)


def create_numeric_item(value, alignment=Qt.AlignCenter):
    """Tworzy element tabeli zoptymalizowany pod sortowanie liczb."""
    item = QTableWidgetItem()
    item.setData(Qt.DisplayRole, value)
    item.setTextAlignment(alignment)
    return item

def get_progress_bar_style(chunk_color="#630D16"):
    """Zwraca spójny arkusz stylów dla pasków postępu w tabelach (genres_view)"""
    return f"""
        QProgressBar {{
            border: 1px solid #D1D1D1;
            border-radius: 4px;
            background-color: #FDFDFD;
            text-align: center;
            color: black;
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {chunk_color};
            border-radius: 3px;
        }}
    """
    
def get_rating_color(rating):
    """Zwraca kolor UI na podstawie wartości oceny (genres_view)"""
    if rating >= 4.5: return "#27ae60" # Ciemnozielony
    if rating >= 3.0: return "#2c3e50" # Standardowy
    return "#e67e22" # Pomarańczowy dla słabych ocen


def clear_layout(layout):
    """Czyści layout z widgetów, zapobiegając wyciekom pamięci i nakładaniu się elementów"""
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                clear_layout(item.layout())

# Przykład użycia w generatorze z Batchingiem
def batch_insert_books(conn, books_data):
    """Szybki zapis dzięki transakcji i executemany"""
    sql = "INSERT INTO books (user_id, title, authors, genre_id, status) VALUES (?, ?, ?, ?, ?)"
    cursor = conn.cursor()
    cursor.execute("PRAGMA synchronous = OFF") # Maksymalna prędkość
    cursor.execute("BEGIN TRANSACTION")
    cursor.executemany(sql, books_data)
    conn.commit()