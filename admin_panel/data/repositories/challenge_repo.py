import sqlite3


class ChallengeRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def count_active(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM challenges WHERE status = 'active'")
        return cursor.fetchone()[0]
