import sqlite3

import pandas as pd


class ClusteringRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_active_users(self):
        query = """
            SELECT id, username, books_read, pages_per_day, current_streak
            FROM users
            WHERE status = 'active'
        """
        return pd.read_sql(query, con=self.conn)

    def update_cluster_groups(self, clusters) -> None:
        cursor = self.conn.cursor()
        cursor.executemany(
            "UPDATE users SET cluster_group = ? WHERE id = ?",
            [(int(cluster), int(user_id)) for user_id, cluster in clusters],
        )
