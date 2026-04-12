from PySide6.QtWidgets import QToolTip
from PySide6.QtGui import QCursor
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

class ChartTooltipHelper:
    """Zbiór metod do interakcji i obsługi zdarzeń na wykresach"""

    @staticmethod
    def setup_hover(canvas, func_get_message):
        """
        Konfiguruje dynamiczne tooltipy dla wykresów Matplotlib w środowisku PySide6
        """
        def on_motion(event):
            # Sprawdzenie czy kursor znajduje się wewnątrz obszaru osi
            if event.inaxes:
                # Pobiera wiadomość (xdata dla liniowego lub wedge dla kołowego)
                msg = func_get_message(event) 
                if msg:
                    # Mapowanie pozycji myszy na współrzędne globalne ekranu
                    global_pos = QCursor.pos()
                    QToolTip.showText(global_pos, msg, canvas)
                    return
            
            # Jeśli nie ma komunikatu lub poza osią, chowa tooltip
            QToolTip.hideText()

        # Łączenie zdarzenia ruchu myszy Matplotlib z funkcją on_motion
        canvas.figure.canvas.mpl_connect('motion_notify_event', on_motion)


class ChartStyler:
    """Zbiór metod do ujednolicania wyglądu i estetyki wykresów"""

    @staticmethod
    def apply_clean_layout(ax):
        """
        Usuwa zbędne elementy obramowania (góra i prawa strona) 
        oraz konfiguruje delikatną, kropkowaną siatkę
        """
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        ax.grid(True, linestyle=':', alpha=0.3, zorder=0)

    @staticmethod
    def set_date_axis(ax, time_filter="week"):
        """
        Automatycznie dostosowuje formatowanie i zagęszczenie etykiet osi X
        w zależności od wybranego zakresu czasu (tydzień, miesiąc, rok, all).
        """
        ax.tick_params(axis='x', rotation=30, labelsize=8)

        if time_filter == "week":
            # Pokazuje skrót dnia i numer (np. "Mon 01") - 7 dni
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%a %d'))
            ax.xaxis.set_major_locator(mdates.DayLocator())
        elif time_filter == "month":
            # Pokazuje dzień i miesiąc - 30 dni, pokazuje ~15 etykiet
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            ax.xaxis.set_major_locator(ticker.MaxNLocator(15))
        else:
            # "year" i "all" - miesiące/tygodnie, pokazuje ~12 etykiet
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
            ax.xaxis.set_major_locator(ticker.MaxNLocator(12))