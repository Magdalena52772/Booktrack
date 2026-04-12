import sys
import os
import time
import cProfile
import pstats
from PySide6.QtWidgets import QApplication

# Ścieżka projektu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importuje poszczególne części zamiast całego main()
from data.database import get_connection, initialize_database
from views.main_window import MainWindow

def diagnoza_bez_blokady():
    print("--- START DIAGNOZY (BEZ BLOKADY MAIN) ---")
    
    # Inicjalizacja bazy i UI
    initialize_database()
    conn = get_connection()
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(conn)
    window.show()

    # Uruchamia profiler, który będzie mierzył czas wykonywania kodu
    profiler = cProfile.Profile()
    profiler.enable()
    
    print("[DIAG] Odpalam ciężką logikę... Zaraz zobaczysz biały ekran. Czekaj.")
    
    
    from data.services.maintenance_service import update_genre_stats
    
    # Testuje konkretne podejrzane funkcje przez 5 sekund
    start = time.perf_counter()
    while time.perf_counter() - start < 5:
        print(f"[DIAG] Mielę dane... ({time.perf_counter()-start:.1f}s)")
        update_genre_stats(conn)
        app.processEvents()

    profiler.disable()
    
    # Wyświetlanie wyników w konsoli
    print("\n" + "="*50)
    print("WYNIKI (PATRZ NA CUMTIME):")
    print("="*50)
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    stats.print_stats(20)
    
    window.close()
    print("\n[DIAG] Gotowe")

if __name__ == "__main__":
    diagnoza_bez_blokady()