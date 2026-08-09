from datetime import datetime, date


class DateHelper:
    @staticmethod
    def to_datetime(date_val):
        """Konwertuje string z SQLite lub None na obiekt datetime."""
        if not date_val:
            return None

        if isinstance(date_val, datetime):
            return date_val

        # Normalizacja: usunięcie milisekund i zamiana 'T' na spację
        clean_date = str(date_val).replace("T", " ").split(".")[0]

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def format_display(date_obj, fmt="%Y-%m-%d %H:%M", default="-"):
        """Bezpieczne formatowanie daty do wyświetlenia w tabeli UI."""
        if not date_obj:
            return default
        if isinstance(date_obj, str):
            date_obj = DateHelper.to_datetime(date_obj)

        return date_obj.strftime(fmt) if date_obj else default

    @staticmethod
    def calculate_age(birth_date):
        if not birth_date:
            return "N/A"
        try:
            if isinstance(birth_date, str):
                dt = DateHelper.to_datetime(birth_date)
                if not dt:
                    return "N/A"
                birth_date = dt.date()
            elif isinstance(birth_date, datetime):
                birth_date = birth_date.date()

            today = date.today()
            return (
                today.year
                - birth_date.year
                - ((today.month, today.day) < (birth_date.month, birth_date.day))
            )
        except Exception:
            return "N/A"
