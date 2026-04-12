"""Filtrowanie czasowe dla repozytoriów
    dla różnych zakresów czasowych (week, month, year, all).
"""
from datetime import datetime, timedelta
from data.utils.time_periods import period_start

class TimeFilterService:
    """Serwis logiki filtrowania czasowego"""

    @staticmethod
    def build_time_filter(time_filter: str = "all") -> tuple[str, list]:
        """
        Buduje klauzulę WHERE i parametry dla zapytań SQL na podstawie filtra czasowego
        """
        date_clause = ""
        params = []
        f_type = time_filter.lower()

        if f_type != "all":
            if f_type == "week":
                # Tydzień = ostatnie 6 dni + dzisiaj = 7 dni razem
                start_dt = datetime.now() - timedelta(days=6)
                date_clause = "WHERE timestamp >= ?"
                params.append(start_dt.strftime("%Y-%m-%d 00:00:00"))
            else:
                # Użycie time_periods utility dla month/year
                dt = period_start(f_type)
                if dt:
                    date_clause = "WHERE timestamp >= ?"
                    params.append(dt.strftime("%Y-%m-%d %H:%M:%S"))

        return date_clause, params