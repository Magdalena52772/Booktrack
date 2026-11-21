import sqlite3


class MaintenanceRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def sync_books_read(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET books_read = (
                SELECT COUNT(*)
                FROM user_books
                WHERE user_books.user_id = users.id
                  AND user_books.status = 'finished'
            )
            """)

    def sync_pages_per_day(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users
            SET pages_per_day = COALESCE(
                (
                    SELECT AVG(daily_sum)
                    FROM (
                        SELECT SUM(pages_read) AS daily_sum
                        FROM activity
                        WHERE activity.user_id = users.id
                          AND timestamp > date('now', '-30 days')
                        GROUP BY date(timestamp)
                    )
                ),
                0.0
            )
            WHERE status != 'inactive'
            """)
        cursor.execute("UPDATE users SET pages_per_day = 0.0 WHERE status = 'inactive'")

    def sync_challenges(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE challenges
            SET current_value = (
                SELECT COUNT(*)
                FROM user_books
                WHERE user_books.user_id = challenges.user_id
                  AND user_books.status = 'finished'
                  AND user_books.finish_date BETWEEN challenges.start_date
                  AND challenges.end_date
            )
            WHERE status = 'active' AND type = 'quantity'
            """)
        cursor.execute("""
            UPDATE challenges
            SET status = 'finished'
            WHERE status = 'active' AND current_value >= target_value
            """)
        cursor.execute("""
            UPDATE challenges
            SET status = 'failed'
            WHERE status = 'active' AND end_date < datetime('now')
            """)

    def get_genre_stats(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                g.id,
                COUNT(DISTINCT ub.user_id) AS readers,
                ROUND(
                    IFNULL(
                        AVG(
                            CASE WHEN ub.status = 'finished' THEN ub.rating END
                        ),
                        0.0
                    ),
                    2
                ) AS avg_rating,
                COUNT(CASE WHEN ub.status = 'finished' THEN 1 END) AS books_read
            FROM genres g
            LEFT JOIN books b ON g.id = b.genre_id
            LEFT JOIN user_books ub ON b.id = ub.book_id
            GROUP BY g.id
            """)
        return cursor.fetchall()

    def update_genre_stats(self, updates: list) -> None:
        cursor = self.conn.cursor()
        cursor.executemany(
            """
            UPDATE genres
            SET readers = ?, avg_rating = ?, books_read = ?,
                reading_time_share = ?
            WHERE id = ?
            """,
            updates,
        )

    def get_users_and_activity_dates(self) -> tuple[list, dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, date_joined FROM users")
        users = cursor.fetchall()
        activity_dates = {}
        for user in users:
            cursor.execute(
                """
                SELECT DISTINCT date(timestamp) AS activity_date
                FROM activity
                WHERE user_id = ?
                ORDER BY activity_date DESC
                LIMIT 100
                """,
                (user["id"],),
            )
            activity_dates[user["id"]] = cursor.fetchall()
        return users, activity_dates

    def update_user_streaks(self, streak_updates: list) -> None:
        cursor = self.conn.cursor()
        cursor.executemany(
            "UPDATE users SET current_streak = ? WHERE id = ?",
            streak_updates,
        )

    def update_user_ppd(self, user_id: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                SUM(pages_read) AS total_pages,
                COUNT(DISTINCT strftime('%Y-%m-%d', timestamp)) AS active_days
            FROM activity
            WHERE user_id = ?
            """,
            (user_id,),
        )
        result = cursor.fetchone()
        if result and result[1] > 0:
            cursor.execute(
                "UPDATE users SET pages_per_day = ? WHERE id = ?",
                (round(result[0] / result[1], 1), user_id),
            )
