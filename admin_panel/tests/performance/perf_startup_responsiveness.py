#!/usr/bin/env python
""" Test poprawności i responsywności podczas uruchamiania aplikacji."""
import sys
import time
from pathlib import Path

current_file = Path(__file__).resolve()
root_path = next((p for p in current_file.parents if (p / "data").exists()), current_file.parent.parent.parent)
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

print("\n" + "="*70)
print("🚀 STARTUP RESPONSIVENESS TEST")
print("="*70)

start_time = time.perf_counter()

try:
    from data.database import initialize_database, get_connection
    from views.main_window import MainWindow

    initialize_database()
    conn = get_connection()
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow(conn)
    window.setWindowState(__import__('PySide6.QtCore', fromlist=['Qt']).Qt.WindowMaximized)
    window.show()

    ui_time = (time.perf_counter() - start_time) * 1000

    print(f"[UI] Window shown in: {ui_time:.0f}ms")
    print(f"[UI] Current view: {window.ui.ContentArea.currentWidget().__class__.__name__}")

    print("[STARTUP] Background work running...")
    for i in range(20):
        app.processEvents()
        time.sleep(0.1)

    total_time = (time.perf_counter() - start_time)

    print("\n" + "="*70)
    print("📊 RESULTS")
    print("="*70)
    print(f"UI shown:        {ui_time:.0f}ms")
    print(f"Total time:      {total_time:.2f}s")
    print(f"✅ Startup complete")
    print("="*70 + "\n")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    def close_app():
        if 'window' in locals():
            window.close()
        app.quit()

    QTimer.singleShot(500, close_app)
    sys.exit(app.exec())
