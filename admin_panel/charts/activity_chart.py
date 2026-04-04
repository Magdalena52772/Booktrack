import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from datetime import datetime
import bisect

class ActivityChart(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.line = None
        self.current_filter = "week"
        self._create_annot()
        self.fig.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def _create_annot(self):
        self.annot = self.axes.annotate("", xy=(0,0), xytext=(15,15),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="#ffffff", ec="#daa520", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color='#daa520'))
        self.annot.set_visible(False)
        self.annot.set_zorder(10)

    def on_hover(self, event):
        if event.inaxes != self.axes or self.line is None:
            if self.annot.get_visible():
                self.annot.set_visible(False)
                self.draw_idle()
            return

        x_data = self.line.get_xdata()
        y_data = self.line.get_ydata()
        if len(x_data) == 0: return

        x_mouse = event.xdata
        idx = bisect.bisect_left(x_data, x_mouse)
        
        if idx == 0: best_idx = 0
        elif idx >= len(x_data): best_idx = len(x_data) - 1
        else:
            d1 = x_mouse - x_data[idx-1]
            d2 = x_data[idx] - x_mouse
            best_idx = idx if d2 < d1 else idx - 1

        x, y = x_data[best_idx], y_data[best_idx]
        
        x_lim = self.axes.get_xlim()
        if (x - x_lim[0]) / (x_lim[1] - x_lim[0]) > 0.75:
            self.annot.set_position((-15, 15))
            self.annot.set_ha('right')
        else:
            self.annot.set_position((15, 15))
            self.annot.set_ha('left')

        self.annot.xy = (x, y)
        dt = mdates.num2date(x)
        date_str = dt.strftime("%A, %d.%m") if self.current_filter != "all" else dt.strftime("%B %Y")
        text = f"{date_str}\n{int(y)} pages"

        if text != self.annot.get_text() or not self.annot.get_visible():
            self.annot.set_text(text)
            self.annot.set_visible(True)
            self.draw_idle()

    def plot_data(self, dates_str, values, time_filter="week"):
        self.current_filter = str(time_filter).lower()
        self.axes.clear()
        
        if not dates_str:
            self.line = None
            self.draw()
            return

        # Konwersja dat
        dates = [mdates.date2num(datetime.strptime(d, "%Y-%m-%d") if len(d)>7 
                 else datetime.strptime(d, "%Y-%m")) for d in dates_str]
        
        # wypełnienie
        self.axes.fill_between(dates, values, color='#daa520', alpha=0.3, zorder=1)

        # Linia
        m_style = 'o' if self.current_filter in ["week", "month"] else None
        self.line, = self.axes.plot(dates, values, marker=m_style, linestyle='-', 
                                    color='#daa520', linewidth=2.5, markersize=5, zorder=2)
        
        # Oś X
        if self.current_filter == "week":
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%a %d'))
            self.axes.xaxis.set_major_locator(mdates.DayLocator())
        elif self.current_filter == "month":
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(8))
        else:
            self.axes.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
            self.axes.xaxis.set_major_locator(ticker.MaxNLocator(6))

        # Marginesy (góra dla tooltipa i zero po bokach)
        if values:
            v_max = max(values)
            self.axes.set_ylim(bottom=0, top=v_max * 1.3)
        
        self.axes.set_xmargin(0)
        
        self.axes.tick_params(axis='x', rotation=30, labelsize=8)
        self.axes.grid(True, linestyle=':', alpha=0.3, zorder=0)
        
        # Odświeżenie annotacji
        self._create_annot()
        
        for spine in ['top', 'right']:
            self.axes.spines[spine].set_visible(False)
            
        # Dopasowanie, żeby wykres był duży i czytelny
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.2)
        self.draw()