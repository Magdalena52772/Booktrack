from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import (
    Activity,
    Challenge,
    UserAchievement,
    UserBook,
    UserNotification,
)


ACHIEVEMENTS = (
    ("books_bronze", "Początkujący Czytelnik", "books_bronze.svg", "Przeczytana 1 książka"),
    ("books_silver", "Biblioteczka", "books_silver.svg", "Przeczytanych 5 książek"),
    ("books_gold", "Mól Książkowy", "books_gold.svg", "Przeczytanych 20 książek"),
    ("pages_bronze", "Sprint", "pages_bronze.svg", "Przeczytanych 100 stron"),
    ("pages_silver", "Maratończyk", "pages_silver.svg", "Przeczytanych 1000 stron"),
    ("pages_gold", "Niestrudzony", "pages_gold.svg", "Przeczytanych 5000 stron"),
    ("strike_bronze", "Rozgrzewka", "strike_bronze.svg", "Aktywność przez 3 dni z rzędu"),
    ("strike_silver", "Tydzień Mocy", "strike_silver.svg", "Aktywność przez 7 dni z rzędu"),
    ("strike_gold", "Mistrz Rutyny", "strike_gold.svg", "Aktywność przez 30 dni w danym roku"),
    ("challenge_bronze", "Nowicjusz Wyzwań", "challenge_bronze.svg", "Ukończone 1 wyzwanie"),
    ("challenge_silver", "Strateg", "challenge_silver.svg", "Ukończone 3 wyzwania"),
    ("challenge_gold", "Mistrz Wyzwań", "challenge_gold.svg", "Ukończone 5 wyzwań"),
)


def _longest_streak(dates):
    longest = current = 0
    previous = None
    for day in sorted(dates):
        if previous and day == previous + timedelta(days=1):
            current += 1
        else:
            current = 1
        longest = max(longest, current)
        previous = day
    return longest


def evaluate_achievements(user):
    finished_books = UserBook.objects.filter(user_id=user.id, status="finished").count()
    total_pages = (
        Activity.objects.filter(user_id=user.id).aggregate(total=Sum("pages_read"))["total"]
        or 0
    )
    activity_dates = set(
        Activity.objects.filter(user_id=user.id, pages_read__gt=0).values_list(
            "timestamp__date", flat=True
        )
    )
    current_year = timezone.localdate().year
    year_dates = {day for day in activity_dates if day.year == current_year}
    finished_challenges = Challenge.objects.filter(
        user_id=user.id, status="finished"
    ).count()
    values = {
        "books_bronze": finished_books >= 1,
        "books_silver": finished_books >= 5,
        "books_gold": finished_books >= 20,
        "pages_bronze": total_pages >= 100,
        "pages_silver": total_pages >= 1000,
        "pages_gold": total_pages >= 5000,
        "strike_bronze": _longest_streak(activity_dates) >= 3,
        "strike_silver": _longest_streak(activity_dates) >= 7,
        "strike_gold": _longest_streak(year_dates) >= 30,
        "challenge_bronze": finished_challenges >= 1,
        "challenge_silver": finished_challenges >= 3,
        "challenge_gold": finished_challenges >= 5,
    }
    metadata = {key: (name, description) for key, name, icon, description in ACHIEVEMENTS}
    newly_earned = []
    for key, earned in values.items():
        if earned:
            _, created = UserAchievement.objects.get_or_create(
                user_id=user.id,
                key=key,
            )
            if not created:
                continue
            name, description = metadata[key]
            UserNotification.objects.create(
                user_id=user.id,
                message=f"Gratulacje! Właśnie otrzymano nową odznakę: {name}! Sprawdź swój profil! 🏆",
                notification_type="achievement",
            )
            newly_earned.append(key)
    return newly_earned


def achievement_cards(user):
    earned = set(
        UserAchievement.objects.filter(user_id=user.id).values_list("key", flat=True)
    )
    return [
        {
            "key": key,
            "name": name,
            "icon": icon,
            "description": description,
            "earned": key in earned,
        }
        for key, name, icon, description in ACHIEVEMENTS
    ]
