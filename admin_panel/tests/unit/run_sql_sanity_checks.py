import sys
from pathlib import Path

# Zapewnienie dostępu do katalogu głównego projektu
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.database import get_connection
from data.repositories.reports_repo import ReportsRepository


def run_checks():
    conn = get_connection()
    repo = ReportsRepository(conn)

    reports = ["Top Readers", "Books", "Activity", "Genres"]
    periods = ["week", "month", "year", "all"]

    print("ReportsView / ReportsRepository Sanity Check")
    print("===========================================")

    for report in reports:
        print(f"\n=================== REPORT: {report} ===================")

        if report == "Top Readers":
            rows = repo.get_top_readers()
            print(f"Returned rows: {len(rows)}")
            if rows:
                sample = rows[0]
                print(
                    f"Sample row: User={sample[0]}, Streak={sample[1]}, Books={sample[2]}, Pages={sample[3]}, Longest={sample[4]}, Joined={sample[5]}"
                )

        elif report == "Books":
            # get_top_books przyjmuje limit, pobiera topowe książki
            rows = repo.get_top_books()
            print(f"Returned rows: {len(rows)}")
            if rows:
                sample = rows[0]
                print(
                    f"Sample row: Title='{sample[0]}', Readers={sample[1]}, Rating={sample[2]}, Genre='{sample[3]}'"
                )

        elif report == "Activity":
            for period in periods:
                print(f"\n--- Period: {period} ---")
                summary = repo.get_activity_summary(period)
                top_reader = repo.get_top_reader(period) or ("-", 0)
                active_day = repo.get_most_active_day(period) or ("-", 0)

                rows = [
                    ("Pages read", summary[0] or 0),
                    ("Reading sessions", summary[1] or 0),
                    ("Active users", summary[2] or 0),
                    ("Average session", summary[3] or 0),
                    ("Top reader", top_reader[0]),
                    ("Top reader pages", top_reader[1]),
                    ("Most active day", active_day[0]),
                    ("Pages that day", active_day[1]),
                ]

                print(f"Metrics count: {len(rows)}")
                for metric, value in rows:
                    print(f"  - {metric}: {value}")

        elif report == "Genres":
            for period in periods:
                print(f"\n--- Period: {period} ---")
                rows = repo.get_top_genres(period)
                print(f"Returned rows: {len(rows)}")
                if rows:
                    sample = rows[0]
                    print(f"Sample row: Genre='{sample[0]}', Pages={sample[1]}")

    conn.close()


if __name__ == "__main__":
    run_checks()