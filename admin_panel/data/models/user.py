from datetime import datetime, date
from typing import List, Optional

class User:
    def __init__(
        self, 
        id: int, 
        name: str, 
        status: str, 
        birth_date: str,
        books_read: int, 
        pages_per_day: float, 
        last_activity: Optional[datetime], 
        register_date: Optional[datetime], 
        favorite_genres: List[str] = None
    ):
        self.id = id
        self.name = name
        self.status = status
        self.birth_date = birth_date 
        self.books_read = books_read
        self.pages_per_day = pages_per_day
        self.last_activity = last_activity
        self.register_date = register_date
        self.favorite_genres = favorite_genres or []

    @property
    def age(self) -> int:
        """Dynamicznie oblicza wiek na podstawie birth_date."""
        if not self.birth_date:
            return 0
        try:
            # Obsługa formatu YYYY-MM-DD
            b_date = datetime.strptime(self.birth_date, "%Y-%m-%d").date()
            today = date.today()
            return today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
        except:
            return 0

    def __repr__(self):
        return f"<User {self.name} (ID: {self.id})>"