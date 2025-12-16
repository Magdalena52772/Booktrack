from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    id: int
    name: str
    favorite_genres: List[str]
    books_read: int
    pages_per_day: float
    last_activity: Optional[datetime]
    status: str                      # "active" / "inactive"
    register_date: datetime