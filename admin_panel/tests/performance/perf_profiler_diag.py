import sys
import os
import time
import cProfile
import pstats
import logging
from PySide6.QtWidgets import QApplication

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)

log = logging.getLogger(__name__)

# Ścieżka projektu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Importy
from data.database import get_connection, initialize_database
from views.main_window import MainWindow


# ================= PROFILER TABLE =================
def log_top_stats(stats, limit=15):
    log.info("=" * 80)
    log.info(f"{'FUNKCJA':45} | {'CALLS':>6} | {'TOTAL(s)':>9} | {'CUM(s)':>9}")
    log.info("=" * 80)

    # sortuje ręcznie po cumulative time
    sorted_stats = sorted(stats.stats.items(), key=lambda x: x[1][3], reverse=True)

    for func, stat in sorted_stats[:limit]:
        filename, line, name = func
        cc, nc, tt, ct, callers = stat

        func_name = f"{name} ({os.path.basename(filename)}:{line})"

        log.info(
            f"{func_name[:45]:45} | {nc:6} | {tt:9.3f} | {ct:9.3f}"
        )


# ================= MAIN =================
def diagnoza_bez_blokady():
    log.info("=== START DIAGNOZY (BEZ BLOKADY MAIN) ===")

    # Inicjalizacja
    log.info("Inicjalizacja bazy danych i UI...")
    initialize_database()
    conn = get_connection()

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(conn)
    window.show()

    profiler = cProfile.Profile()
    profiler.enable()

    log.info("[BATCH] Start aktualizacji statystyk (UI może chwilowo zwolnić)")

    from data.services.maintenance_service import update_genre_stats

    start = time.perf_counter()
    last_log = 0

    while time.perf_counter() - start < 5:
        elapsed = time.perf_counter() - start

        # log co 1 sekundę
        if elapsed - last_log >= 1:
            log.info(f"[BATCH] Aktualizacja statystyk... {elapsed:.1f}s")
            last_log = elapsed

        update_genre_stats(conn)
        app.processEvents()

    profiler.disable()

    log.info("=== WYNIKI PROFILERA (TOP CUMULATIVE TIME) ===")
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    log_top_stats(stats, 15)

    window.close()
    log.info("Diagnoza zakończona ✔")


if __name__ == "__main__":
    diagnoza_bez_blokady()