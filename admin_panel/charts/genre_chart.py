import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class GenreChart(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8.5, 3.8), dpi=100)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def update_chart(self, genres, age_group_name):
        self.axes.clear()
        if not genres:
            self.draw()
            return

        sorted_genres = sorted(genres, key=lambda x: x.readers, reverse=True)[:5]
        names = [g.name for g in sorted_genres]
        values = [g.readers for g in sorted_genres]

        bars = self.axes.bar(names, values, color='#D4AF37', width=0.6)
        self.axes.bar_label(bars, padding=5, color='#8B6508', fontsize=11, fontweight='bold')
        
        self.axes.set_title(f"Top Genres Popularity: {age_group_name}", fontsize=12, fontweight='bold', pad=20)
        self.axes.set_ylabel("Number of Readers", fontsize=11, fontweight='medium')
        
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.set_yticks([])
        
        self.fig.tight_layout()
        self.draw()