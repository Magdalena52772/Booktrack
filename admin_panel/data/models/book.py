from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Book:
    id: int
    title: str
    author: str
    genre: str
    total_pages: int
    current_page: int
    status: str                     # "reading" / "finished"
    rating: Optional[int]
    start_date: Optional[datetime]
    finish_date: Optional[datetime]
    added_by_generator: bool