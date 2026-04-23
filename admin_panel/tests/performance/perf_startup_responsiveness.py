""" Test poprawności i responsywności podczas uruchamiania aplikacji.

Mierzy rzeczywiste czasy:
- UI ready: moment po MainWindow.__init__() ale przed show()
- First paint: moment gdy Qt event loop przejął UI
- Dashboard render: moment gdy wykresy się wyrenderują
"""
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
print("STARTUP RESPONSIVENESS TEST")
print("="*70)

start_time = time.perf_counter()

try:
    t = time.perf_counter()
    from data.database import initialize_database, get_connection
    print(f"[IMPORT] database module: {(time.perf_counter()-t)*1000:.0f}ms")

    t = time.perf_counter()
    from views.main_window import MainWindow
    print(f"[IMPORT] MainWindow module: {(time.perf_counter()-t)*1000:.0f}ms")

    t = time.perf_counter()
    initialize_database()
    print(f"[INIT] Database: {(time.perf_counter()-t)*1000:.0f}ms")

    t = time.perf_counter()
    conn = get_connection()
    print(f"[INIT] get_connection(): {(time.perf_counter()-t)*1000:.0f}ms")

    t = time.perf_counter()
    app = QApplication.instance() or QApplication(sys.argv)
    print(f"[INIT] QApplication: {(time.perf_counter()-t)*1000:.0f}ms")

    t = time.perf_counter()
    window = MainWindow(conn)
    print(f"[CREATE] MainWindow instance: {(time.perf_counter()-t)*1000:.0f}ms")

    t = time.perf_counter()
    t_before_show = time.perf_counter()
    window.setWindowState(__import__('PySide6.QtCore', fromlist=['Qt']).Qt.WindowMaximized)
    print(f"[SETUP] setWindowState: {(time.perf_counter()-t)*1000:.0f}ms")

    t = time.perf_counter()
    window.show()
    t_after_show = time.perf_counter()
    print(f"[SHOW] window.show(): {(time.perf_counter()-t)*1000:.0f}ms")

    # moment kiedy UI trafia do event loop
    test_state = {"first_paint_time": None, "dashboard_render_time": None}

    def after_first_paint():
        t_callback = time.perf_counter()
        test_state["first_paint_time"] = (t_callback - t_after_show) * 1000
        print(f"[UI] First paint (from show): {test_state['first_paint_time']:.0f}ms")

        # Podłącz się do renderingFinished sygnału DashboardView
        dashboard_view = window.view_config[window.ui.btn_dashboard]["instance"]
        if dashboard_view and hasattr(dashboard_view, "renderingFinished"):
            dashboard_view.renderingFinished.connect(on_dashboard_rendered)
            print(f"[CONNECT] Listening for dashboard renderingFinished signal...")
        else:
            print(f"[WARNING] Could not connect to renderingFinished signal")
            finish()

    def on_dashboard_rendered():
        """Callback kiedy wykresy się wyrenderują"""
        if test_state["dashboard_render_time"] is None:
            test_state["dashboard_render_time"] = (time.perf_counter() - start_time) * 1000
            print(f"[DASHBOARD] Charts rendered at {test_state['dashboard_render_time']:.0f}ms")
            finish()

    def finish():
        total_time = (time.perf_counter() - start_time)
        ui_ready_time = (t_before_show - start_time) * 1000
        dashboard_ready_time = test_state["dashboard_render_time"] or (time.perf_counter() - start_time) * 1000

        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"UI ready:        {ui_ready_time:.0f}ms")
        print(f"First paint:     {test_state['first_paint_time']:.0f}ms")
        print(f"Dashboard ready: {dashboard_ready_time:.0f}ms")
        print(f"Total time:      {total_time:.2f}s")

        # Checks vs targets
        targets = {"UI ready": 500, "First paint": 800}
        if ui_ready_time <= targets["UI ready"]:
            print(f"[OK] UI ready < {targets['UI ready']}ms")
        else:
            print(f"[SLOW] UI ready {ui_ready_time:.0f}ms > {targets['UI ready']}ms target")

        if test_state['first_paint_time'] <= targets["First paint"]:
            print(f"[OK] First paint < {targets['First paint']}ms")
        else:
            print(f"[SLOW] First paint {test_state['first_paint_time']:.0f}ms > {targets['First paint']}ms target")

        print("="*70 + "\n")

        window.close()
        app.quit()

    # Startuje callback po pierwszym paint
    QTimer.singleShot(0, after_first_paint)

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    if 'app' in locals():
        app.quit()

finally:
    # Startuje event loop
    if 'app' in locals():
        sys.exit(app.exec())