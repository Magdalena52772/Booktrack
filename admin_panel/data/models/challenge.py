from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Challenge:
    id: int
    user_id: int
    title: str
    target_books: int
    progress_books: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: str  # "active", "finished", "failed"
