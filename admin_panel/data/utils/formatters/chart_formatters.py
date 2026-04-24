from PySide6.QtWidgets import QToolTip
from PySide6.QtGui import QCursor
import matplotlib.ticker as ticker
import matplotlib.dates as mdates

class ChartTooltipHelper:
    """Zbiór metod do interakcji i obsługi zdarzeń na wykresach"""

    @staticmethod
    def setup_hover(canvas, func_get_message):
        """
        Konfiguruje dynamiczne tooltipy dla wykresów Matplotlib w środowisku PySide6.
        Tooltip tylko gdy blisko markerów (tolerance 10px)
        """
        last_msg = [None]  # Cache message

        def on_motion(event):
            # Sprawdzenie czy kursor znajduje się wewnątrz obszaru osi
            if not event.inaxes:
                QToolTip.hideText()
                return

            # Tolerance: tylko jeśli blisko markerów (<10 pixels od danych)
            tolerance = 10
            xpixel = event.x
            ypixel = event.y

            # Transform axes to display coordinates
            ax = event.inaxes
            try:
                # Sprawdzenie czy jest blisko linii/markerów
                transform = ax.transData.transform
                if hasattr(ax, 'lines') and len(ax.lines) > 0:
                    line = ax.lines[0]
                    xdata = line.get_xdata()
                    ydata = line.get_ydata()
                    if len(xdata) > 0:
                        # Transform danych na pixel coords
                        points_px = transform(list(zip(xdata, ydata)))

                        # Sprawdzenie odległości do wszystkich markerów
                        min_dist = float('inf')
                        for px, py in points_px:
                            dist = ((xpixel - px)**2 + (ypixel - py)**2)**0.5
                            if dist < min_dist:
                                min_dist = dist

                        # Pokaz tooltip TYLKO jeśli blisko markera
                        if min_dist > tolerance:
                            QToolTip.hideText()
                            return
            except:
                pass

            # Pobiera wiadomość tylko jeśli blisko markerów
            msg = func_get_message(event)
            if msg and msg != last_msg[0]:
                last_msg[0] = msg
                global_pos = QCursor.pos()
                QToolTip.showText(global_pos, msg, canvas)
            elif not msg:
                QToolTip.hideText()
                last_msg[0] = None

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
        """Dostosowuje ticków i formatowanie osi X."""
        ax.tick_params(axis='x', rotation=30, labelsize=9)
        ax.tick_params(axis='y', labelsize=9)

        if time_filter == "week":
            # Week: każdy dzień
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%a %d'))
            ax.xaxis.set_major_locator(mdates.DayLocator())
        elif time_filter == "month":
            # Month: raz w tygodniu (co 7 dni)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        elif time_filter == "year":
            # Year: 12 ticków (co miesiąc)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        else:
            # All: co pół roku (2 ticki na rok)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))