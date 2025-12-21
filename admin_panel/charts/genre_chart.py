import matplotlib.pyplot as plt
import os

class GenreChartGenerator:
    """
    Klasa odpowiedzialna za generowanie wizualizacji danych.
    Zoptymalizowana pod kątem czytelności i pełnego opisu osi.
    """
    @staticmethod
    def generate_popularity_chart(genres, age_group_name):
        if not genres:
            return None

        # Pobranie danych (Top 5)
        sorted_genres = sorted(genres, key=lambda x: x.readers, reverse=True)[:5]
        names = [g.name for g in sorted_genres]
        values = [g.readers for g in sorted_genres]

        # Proporcje panoramiczne
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(8.5, 3.8))
        
        # Złote słupki
        bars = ax.bar(names, values, color='#D4AF37', width=0.6)

        # Liczby nad słupkami
        ax.bar_label(bars, padding=5, color='#8B6508', fontsize=11, fontweight='bold')
        
        # Tytuł
        ax.set_title(f"Top Genres Popularity: {age_group_name}", fontsize=12, fontweight='bold', pad=20)
        
        ax.set_ylabel("Number of Readers", fontsize=11, fontweight='medium', labelpad=10)
        
        # Dolna belka - font 12
        plt.xticks(rotation=0, fontsize=12, fontweight='medium')
        
        # Przywraca lewą linię osi, żeby napis miał punkt odniesienia
        ax.spines['left'].set_visible(True)
        ax.spines['left'].set_color('#CCCCCC') # Delikatny szary kolor
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(True)
        
        # Wyłącza same liczby na osi Y
        ax.set_yticks([])

        plt.tight_layout()

        path = "charts/generated/genre_chart.png"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plt.savefig(path, transparent=True, bbox_inches='tight', dpi=110)
        plt.close()
        return path