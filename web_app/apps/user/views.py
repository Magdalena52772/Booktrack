from datetime import date, datetime, timedelta
from math import cos, radians, sin

from django.db import transaction
from django.db.models import Avg, Case, Count, Q, Sum, When
from django.db.models.functions import TruncDate, TruncMonth
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponseRedirect
from urllib.parse import urlencode

from pages.models import (
    Activity,
    Book,
    BooktrackUser,
    Challenge,
    Genre,
    UserBook,
    UserBookReview,
    UserFavoriteBook,
    UserFavoriteGenre,
    UserNotification,
    UserReadingQueue,
)
from pages.achievements import achievement_cards, evaluate_achievements


def _get_user(request):
    return request.user


def _touch_last_activity(user_id, timestamp=None):
    timestamp = timestamp or timezone.now()
    BooktrackUser.objects.filter(id=user_id).update(last_activity=timestamp)
    return timestamp


def _record_activity(user_id, book_id, pages_read=0, session_minutes=0, timestamp=None):
    timestamp = _touch_last_activity(user_id, timestamp)
    Activity.objects.create(
        user_id=user_id,
        book_id=book_id,
        pages_read=pages_read,
        session_minutes=session_minutes,
        timestamp=timestamp,
    )
    return timestamp


def _notify(request, user_id, message, notification_type="info"):
    notification = UserNotification.objects.create(
        user_id=user_id,
        message=message,
        notification_type=notification_type,
    )
    messages.success(request, message)
    return notification


def _get_recommendations(user, limit=10):
    if not user:
        return []

    favorite_genre_ids = UserFavoriteGenre.objects.filter(
        user_id=user.id
    ).values_list("genre_id", flat=True)
    already_assigned = UserBook.objects.filter(user_id=user.id).values_list(
        "book_id", flat=True
    )
    return list(
        Book.objects.filter(genre_id__in=favorite_genre_ids)
        .exclude(openlibrary_id__isnull=True)
        .exclude(id__in=already_assigned)
        .order_by("title")[:limit]
    )


def _add_library_status(books, user):
    book_ids = [book.id for book in books]
    favorite_ids = set(
        UserFavoriteBook.objects.filter(
            user_id=user.id, book_id__in=book_ids
        ).values_list("book_id", flat=True)
    )
    queue_ids = set(
        UserReadingQueue.objects.filter(
            user_id=user.id, book_id__in=book_ids
        ).values_list("book_id", flat=True)
    )
    user_books = {
        row.book_id: row.status
        for row in UserBook.objects.filter(user_id=user.id, book_id__in=book_ids)
    }
    for book in books:
        book.is_favorite = book.id in favorite_ids
        book.is_queued = book.id in queue_ids
        book.reading_status = user_books.get(book.id, "")
    return books


def _challenge_progress(challenge, user):
    start_date = challenge.start_date or date(challenge.end_date.year, 1, 1)
    end_date = challenge.end_date
    if challenge.type == "quantity":
        value = UserBook.objects.filter(
            user_id=user.id,
            status="finished",
            finish_date__date__gte=start_date,
            finish_date__date__lte=end_date,
        ).count()
    elif challenge.type == "genre":
        value = UserBook.objects.filter(
            user_id=user.id,
            status="finished",
            book__genre_id=challenge.genre_id,
            finish_date__date__gte=start_date,
            finish_date__date__lte=end_date,
        ).count()
    else:
        activity_dates = set(
            Activity.objects.filter(
                user_id=user.id,
                pages_read__gt=0,
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date,
            ).values_list("timestamp__date", flat=True)
        )
        login_dates = set(
            UserNotification.objects.filter(
                user_id=user.id,
                notification_type="daily_login",
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            ).values_list("created_at__date", flat=True)
        )
        activity_dates.update(login_dates)
        value = 0
        current_streak = 0
        day = start_date
        while day <= end_date:
            if day in activity_dates:
                current_streak += 1
                value = max(value, current_streak)
            else:
                current_streak = 0
            day += timedelta(days=1)
    return min(value, challenge.target_value)


def _prepare_challenges(challenges, user):
    prepared = []
    today = timezone.localdate()
    for challenge in challenges:
        if challenge.status == "active" and challenge.end_date < today:
            challenge.status = "failed"
            Challenge.objects.filter(id=challenge.id, user_id=user.id).update(status="failed")
            continue
        challenge.current_value = _challenge_progress(challenge, user)
        if challenge.status == "active" and challenge.current_value >= challenge.target_value:
            challenge.status = "finished"
            Challenge.objects.filter(id=challenge.id, user_id=user.id).update(
                current_value=challenge.current_value,
                status="finished",
            )
        elif challenge.status == "active":
            Challenge.objects.filter(id=challenge.id, user_id=user.id).update(
                current_value=challenge.current_value
            )
        prepared.append(challenge)
    return prepared


@login_required(login_url="login")
def dashboard(request):
    user = _get_user(request)
    reading_rows = []
    books_read = 0
    active_challenges = []
    favorite_count = 0
    to_read_count = 0
    account_age_days = 0
    favorite_genres = []
    if user:
        evaluate_achievements(user)
        books_read = (
            UserBook.objects.filter(user_id=user.id, status="finished").count()
        )
        reading_rows = list(
            UserBook.objects.filter(user_id=user.id, status="reading")
            .select_related("book")
            .order_by("-start_date", "id")[:2]
        )
        active_challenges = _prepare_challenges(
            list(
                Challenge.objects.filter(
                    user_id=user.id,
                    status__in={"active", "finished"},
                    end_date__year=timezone.localdate().year,
                )
                .select_related("genre")
                .order_by(
                    Case(When(status="active", then=0), default=1),
                    "end_date",
                    "id",
                )[:3]
            ),
            user,
        )
        evaluate_achievements(user)
        achievements = achievement_cards(user)
        favorite_count = UserFavoriteBook.objects.filter(user_id=user.id).count()
        to_read_count = UserReadingQueue.objects.filter(user_id=user.id).count()
        account_age_days = max(
            1,
            (timezone.localdate() - timezone.localtime(user.date_joined).date()).days + 1,
        )
        favorite_genres = list(
            UserFavoriteGenre.objects.filter(user_id=user.id)
            .select_related("genre")
            .order_by("genre__name")
            .values_list("genre__name", flat=True)
        )
    recommendations = _add_library_status(
        _get_recommendations(user, limit=4), user
    )

    return render(
        request,
        "user/user_dashboard.html",
        {
            "books_read": books_read,
            "selected_user": user,
            "reading_books": reading_rows,
            "recommendations": recommendations,
            "active_challenges": active_challenges,
            "favorite_count": favorite_count,
            "to_read_count": to_read_count,
            "account_age_days": account_age_days,
            "favorite_genres": favorite_genres,
            "recent_achievements": sorted(
                (achievement for achievement in achievements if achievement["earned"]),
                key=lambda achievement: achievement["earned_at"],
                reverse=True,
            )[:4],
        },
    )


@login_required(login_url="login")
def challenges(request):
    user = _get_user(request)
    challenge_rows = _prepare_challenges(
        list(
            Challenge.objects.filter(user_id=user.id)
            .select_related("genre")
            .order_by(
                Case(When(status="active", then=0), default=1),
                "-end_date",
                "id",
            )
        ),
        user,
    )
    return render(
        request,
        "user/challenges.html",
        {"selected_user": user, "challenges": challenge_rows},
    )


@login_required(login_url="login")
def notifications(request):
    user_notifications = list(
        UserNotification.objects.filter(user_id=request.user.id)[:10]
    )
    UserNotification.objects.filter(
        user_id=request.user.id, is_read=False
    ).update(is_read=True)
    return render(
        request,
        "user/notifications.html",
        {"selected_user": request.user, "notifications": user_notifications},
    )


@login_required(login_url="login")
def create_challenge(request):
    today = timezone.localdate()
    challenge_type = request.POST.get("challenge_type", "quantity")
    if challenge_type not in {"quantity", "genre", "streak"}:
        challenge_type = "quantity"
    target_value = request.POST.get("target_value", "")
    selected_genre_id = request.POST.get("genre_id", "")
    error = ""

    if request.method == "POST":
        try:
            target = int(target_value)
        except (TypeError, ValueError):
            target = 0
        year = today.year
        if target < 1 or target > 1000:
            error = "Cel musi być liczbą od 1 do 1000."
        elif challenge_type == "genre" and not Genre.objects.filter(id=selected_genre_id).exists():
            error = "Wybierz gatunek."
        if not error:
            genre = (
                Genre.objects.get(id=selected_genre_id)
                if challenge_type == "genre"
                else None
            )
            if challenge_type == "quantity":
                title = f"Przeczytam {target} książek w {year} roku"
            elif challenge_type == "genre":
                title = f"Odkrywca: {target} książek z gatunku {genre.name}"
            else:
                title = f"Nawyk: czytam przez {target} dni z rzędu"
            Challenge.objects.create(
                user_id=request.user.id,
                title=title,
                type=challenge_type,
                target_value=target,
                current_value=0,
                genre_id=genre.id if genre else None,
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31),
                status="active",
            )
            _touch_last_activity(request.user.id)
            _notify(
                request,
                request.user.id,
                "Zmiany zapisane. Twoja biblioteka została uporządkowana. ✅",
            )
            return redirect("dashboard")

    return render(
        request,
        "user/challenge_form.html",
        {
            "selected_user": request.user,
            "genres": Genre.objects.order_by("name"),
            "challenge_type": challenge_type,
            "target_value": target_value,
            "current_year": today.year,
            "selected_genre_id": str(selected_genre_id),
            "error": error,
        },
    )


@login_required(login_url="login")
def reading_list(request):
    user = _get_user(request)
    rows = []
    if user:
        rows = list(
            UserBook.objects.filter(user_id=user.id)
            .select_related("book")
            .prefetch_related("review")
            .order_by(
                Case(When(status="reading", then=0), default=1),
                "-start_date",
                "id",
            )
        )
    return render(
        request,
        "user/reading_list.html",
        {"selected_user": user, "reading_books": rows},
    )


@login_required(login_url="login")
def user_book_detail(request, user_book_id):
    user_book = get_object_or_404(
        UserBook.objects.select_related("book"),
        id=user_book_id,
        user_id=request.user.id,
    )
    review = UserBookReview.objects.filter(user_book_id=user_book.id).first()
    reading_sessions = list(
        Activity.objects.filter(
            user_id=request.user.id,
            book_id=user_book.book_id,
        ).order_by("-timestamp")[:10]
    )
    error = None

    if request.method == "POST":
        is_finished = user_book.status == "finished"
        pages_raw = request.POST.get("pages_read", "0").strip()
        minutes_raw = request.POST.get("session_minutes", "0").strip()
        rating_raw = request.POST.get("rating", "").strip()
        comment = request.POST.get("comment", "").strip()
        mark_finished = request.POST.get("mark_finished") == "on"

        if is_finished:
            pages_read = session_minutes = 0
        else:
            try:
                pages_read = int(pages_raw or 0)
                session_minutes = int(minutes_raw or 0)
            except ValueError:
                pages_read = session_minutes = -1

        if pages_read < 0 or pages_read > 1000:
            error = "Liczba stron w sesji musi wynosić od 0 do 1000."
        elif session_minutes < 0:
            error = "Czas sesji nie może być ujemny."
        elif user_book.book.total_pages and (
            user_book.current_page + pages_read > user_book.book.total_pages
        ):
            error = "Liczba stron przekroczyłaby całkowitą liczbę stron książki."

        rating = None
        if rating_raw:
            try:
                rating = int(rating_raw)
            except ValueError:
                rating = None
            if rating is None or rating not in range(1, 6):
                error = "Ocena musi być wybrana w skali od 1 do 5."

        should_finish = is_finished or mark_finished or (
            user_book.book.total_pages
            and user_book.current_page + pages_read >= user_book.book.total_pages
        )
        if should_finish and rating is None:
            rating = user_book.rating
        if should_finish and rating is None:
            error = "Po oznaczeniu książki jako przeczytanej wybierz ocenę od 1 do 5."
        elif not should_finish and rating is not None:
            error = "Ocenę można dodać dopiero po oznaczeniu książki jako przeczytanej."

        if not error:
            with transaction.atomic():
                activity_timestamp = _record_activity(
                    request.user.id,
                    user_book.book_id,
                    pages_read=pages_read,
                    session_minutes=session_minutes,
                )

                if not is_finished:
                    user_book.current_page += pages_read
                if should_finish:
                    user_book.status = "finished"
                    user_book.finish_date = timezone.now()
                    user_book.current_page = (
                        user_book.book.total_pages or user_book.current_page
                    )
                    user_book.rating = rating
                user_book.save(
                    update_fields=[
                        "current_page",
                        "status",
                        "finish_date",
                        "rating",
                    ]
                )
                request.user.last_activity = activity_timestamp

                if should_finish or comment:
                    UserBookReview.objects.update_or_create(
                        user_book_id=user_book.id,
                        defaults={"comment": comment},
                    )
                if should_finish and not is_finished:
                    evaluate_achievements(request.user)
                    _notify(
                        request,
                        request.user.id,
                        "Kolejna historia za Tobą! Twoja półka rośnie. 📚",
                        "book",
                    )
                elif pages_read or session_minutes:
                    evaluate_achievements(request.user)
                    _notify(
                        request,
                        request.user.id,
                        "Super! Twój postęp został zapisany! 📖",
                    )
            return redirect("user_book_detail", user_book_id=user_book.id)

    return render(
        request,
        "user/user_book_detail.html",
        {
            "user_book": user_book,
            "review": review,
            "reading_sessions": reading_sessions,
            "error": error,
        },
    )


@login_required(login_url="login")
def favourite_books(request):
    user = _get_user(request)
    books = list(
        Book.objects.filter(favorite_book_links__user_id=user.id)
        .order_by("title")
    )
    return render(
        request,
        "user/library.html",
        {"selected_user": user, "books": books, "list_type": "favourites"},
    )


@login_required(login_url="login")
def to_read_books(request):
    books = list(
        Book.objects.filter(reading_queue_links__user_id=request.user.id)
        .order_by("title")
    )
    return render(
        request,
        "user/library.html",
        {"selected_user": request.user, "books": books, "list_type": "to_read"},
    )


@login_required(login_url="login")
def library_search(request):
    query = (request.GET.get("query") or "").strip()
    books = []
    query_error = ""
    if len(query) > 100:
        query_error = "Wyszukiwana fraza może mieć maksymalnie 100 znaków."
        query = ""
    if query:
        books = list(
            Book.objects.filter(
                Q(title__icontains=query) | Q(authors__icontains=query)
            ).order_by("title")[:30]
        )
    favorite_ids = set(
        UserFavoriteBook.objects.filter(user_id=request.user.id).values_list("book_id", flat=True)
    )
    queue_ids = set(
        UserReadingQueue.objects.filter(user_id=request.user.id).values_list("book_id", flat=True)
    )
    reading_ids = set(
        UserBook.objects.filter(
            user_id=request.user.id, status="reading"
        ).values_list("book_id", flat=True)
    )
    finished_ids = set(
        UserBook.objects.filter(
            user_id=request.user.id, status="finished"
        ).values_list("book_id", flat=True)
    )
    return render(
        request,
        "user/library_search.html",
        {
            "query": query,
            "books": books,
            "query_error": query_error,
            "favorite_ids": favorite_ids,
            "queue_ids": queue_ids,
            "reading_ids": reading_ids,
            "finished_ids": finished_ids,
        },
    )


@login_required(login_url="login")
def library_action(request):
    if request.method != "POST":
        return redirect("library_search")
    book = get_object_or_404(Book, id=request.POST.get("book_id"))
    action = request.POST.get("action")
    activity_recorded = False
    if action == "favorite":
        UserFavoriteBook.objects.get_or_create(user_id=request.user.id, book_id=book.id)
        activity_recorded = True
        _notify(request, request.user.id, "Książka pomyślnie dodana do listy. 📚", "book")
    elif action == "unfavorite":
        deleted, _ = UserFavoriteBook.objects.filter(
            user_id=request.user.id, book_id=book.id
        ).delete()
        activity_recorded = deleted > 0
        _notify(
            request,
            request.user.id,
            "Zmiany zapisane. Twoja biblioteka została uporządkowana. ✅",
        )
    elif action == "to_read":
        if not UserBook.objects.filter(user_id=request.user.id, book_id=book.id).exists():
            UserReadingQueue.objects.get_or_create(user_id=request.user.id, book_id=book.id)
            activity_recorded = True
            _notify(request, request.user.id, "Książka pomyślnie dodana do listy. 📚", "book")
    elif action == "remove_to_read":
        deleted, _ = UserReadingQueue.objects.filter(
            user_id=request.user.id, book_id=book.id
        ).delete()
        activity_recorded = deleted > 0
        _notify(
            request,
            request.user.id,
            "Zmiany zapisane. Twoja biblioteka została uporządkowana. ✅",
        )
    elif action == "start_reading":
        user_book, created = UserBook.objects.get_or_create(
            user_id=request.user.id,
            book_id=book.id,
            defaults={"status": "reading", "start_date": timezone.now()},
        )
        deleted, _ = UserReadingQueue.objects.filter(
            user_id=request.user.id, book_id=book.id
        ).delete()
        activity_recorded = created or deleted > 0
        _notify(request, request.user.id, "Książka pomyślnie dodana do listy. 📚", "book")
    else:
        return redirect("library_search")
    if activity_recorded:
        _record_activity(request.user.id, book.id)
    else:
        _touch_last_activity(request.user.id)
    next_view = request.POST.get("next")
    if next_view not in {
        "library_search",
        "favourite_books",
        "to_read_books",
        "recommendations",
        "book_detail",
    }:
        next_view = "library_search"
    if next_view == "book_detail":
        return redirect("book_detail", book_id=book.id)
    if next_view == "library_search":
        query = (request.POST.get("query") or "").strip()
        if query:
            return HttpResponseRedirect(
                f"{reverse('library_search')}?{urlencode({'query': query})}"
            )
    return redirect(next_view)
@login_required(login_url="login")
def stats(request):
    user = _get_user(request)
    today = timezone.localdate()
    stats_data = {
        "books_read": 0,
        "books_read_year": 0,
        "current_year": today.year,
        "pages_total": 0,
        "ppd": 0.0,
        "streak": 0,
        "pages_today": 0,
        "pages_yesterday": 0,
    }
    activity_chart = []
    book_chart = []
    genre_chart = []
    genre_pie_style = ""
    book_chart_period = request.GET.get("period", "year")
    if book_chart_period not in {"14", "30", "year"}:
        book_chart_period = "year"
    activity_heatmap = []
    month_names_short = (
        "sty", "lut", "mar", "kwi", "maj", "cze",
        "lip", "sie", "wrz", "paź", "lis", "gru",
    )
    if user:
        evaluate_achievements(user)
        user_activity = Activity.objects.filter(user_id=user.id)
        finished_books = UserBook.objects.filter(
            user_id=user.id,
            status="finished",
            finish_date__isnull=False,
        )
        year_activity = user_activity.filter(
            timestamp__date__gte=date(today.year, 1, 1),
            timestamp__date__lte=today,
        )
        activity_aggregate = year_activity.aggregate(total_pages=Sum("pages_read"))
        account_start = (
            timezone.localtime(user.date_joined).date()
            if user.date_joined
            else today
        )
        account_age_days = max(1, (today - account_start).days + 1)
        activity_dates = set(
            user_activity.annotate(day=TruncDate("timestamp")).values_list(
                "day", flat=True
            )
        )
        if user.last_activity:
            activity_dates.add(timezone.localtime(user.last_activity).date())
        calculated_streak = 0
        streak_day = today
        while streak_day in activity_dates:
            calculated_streak += 1
            streak_day -= timedelta(days=1)
        period_days = {"14": 14, "30": 30}.get(book_chart_period)
        period_start = today - timedelta(days=period_days - 1) if period_days else date(today.year, 1, 1)
        daily_pages = {
            row["day"]: row["pages"] or 0
            for row in user_activity.filter(
                timestamp__date__gte=period_start,
                timestamp__date__lte=today,
            )
            .annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(pages=Sum("pages_read"))
        }
        if period_days:
            chart_rows = [
                {
                    "label": (today - timedelta(days=offset)).strftime("%d.%m"),
                    "pages": daily_pages.get(today - timedelta(days=offset), 0),
                }
                for offset in range(period_days - 1, -1, -1)
            ]
        else:
            monthly_pages = {
                (
                    row["month"].date()
                    if hasattr(row["month"], "date")
                    else row["month"]
                ): row["pages"] or 0
                for row in year_activity.annotate(month=TruncMonth("timestamp"))
                .values("month")
                .annotate(pages=Sum("pages_read"))
            }
            chart_rows = [
                {
                    "label": month_names_short[month - 1],
                    "pages": monthly_pages.get(date(today.year, month, 1), 0),
                }
                for month in range(1, today.month + 1)
            ]
        max_pages = max((row["pages"] for row in chart_rows), default=0)
        activity_chart = [
            {
                **row,
                "bar_height": round((row["pages"] / max_pages) * 110)
                if max_pages
                else 0,
            }
            for row in chart_rows
        ]
        if book_chart_period in {"14", "30"}:
            book_start = period_start
            book_counts = {
                (
                    row["period"].date()
                    if isinstance(row["period"], datetime)
                    else row["period"]
                ): row["count"]
                for row in finished_books.filter(
                    finish_date__date__gte=book_start,
                    finish_date__date__lte=today,
                )
                .annotate(period=TruncDate("finish_date"))
                .values("period")
                .annotate(count=Count("id"))
            }
            book_rows = [
                {
                    "label": (book_start + timedelta(days=offset)).strftime("%d.%m"),
                    "count": book_counts.get(book_start + timedelta(days=offset), 0),
                }
                for offset in range(period_days)
            ]
            book_period_label = f"ostatnie {period_days} dni"
        else:
            year_start = date(today.year, 1, 1)
            book_counts = {
                (
                    row["period"].date()
                    if isinstance(row["period"], datetime)
                    else row["period"]
                ): row["count"]
                for row in finished_books.filter(
                    finish_date__date__gte=year_start,
                    finish_date__date__lte=today,
                )
                .annotate(period=TruncMonth("finish_date"))
                .values("period")
                .annotate(count=Count("id"))
            }
            book_rows = [
                {
                    "label": month_names_short[month - 1],
                    "count": book_counts.get(
                        date(today.year, month, 1).replace(day=1), 0
                    ),
                }
                for month in range(1, 13)
                if date(today.year, month, 1) <= today
            ]
            book_period_label = f"rok {today.year}"
        genre_period_books = finished_books
        genre_counts = list(
            genre_period_books.values("book__genre__name")
            .annotate(count=Count("id"))
            .order_by("-count", "book__genre__name")
        )
        genre_total = sum(row["count"] for row in genre_counts)
        genre_colors = ("#774936", "#936044", "#b08968", "#d7b99e", "#c9b7a8")
        genre_offset = 0
        for index, row in enumerate(genre_counts):
            count = row["count"]
            percentage = round(count / genre_total * 100, 1) if genre_total else 0
            genre_name = row["book__genre__name"] or "Bez gatunku"
            genre_books = list(
                genre_period_books.filter(
                    book__genre__name=row["book__genre__name"]
                ).values_list("book__title", flat=True)
            )
            start_angle = genre_offset * 3.6 - 90
            end_angle = (genre_offset + percentage) * 3.6 - 90
            start_point = (
                100 + 100 * cos(radians(start_angle)),
                100 + 100 * sin(radians(start_angle)),
            )
            end_point = (
                100 + 100 * cos(radians(end_angle)),
                100 + 100 * sin(radians(end_angle)),
            )
            path = (
                "M 100 100 L 100 0 A 100 100 0 1 1 100 200 "
                "A 100 100 0 1 1 100 0 Z"
                if percentage >= 99.9
                else (
                    f"M 100 100 L {start_point[0]:.3f} {start_point[1]:.3f} "
                    f"A 100 100 0 {'1' if percentage > 50 else '0'} 1 "
                    f"{end_point[0]:.3f} {end_point[1]:.3f} Z"
                )
            )
            genre_chart.append(
                {
                    "name": genre_name,
                    "count": count,
                    "percentage": percentage,
                    "color": genre_colors[index % len(genre_colors)],
                    "path": path,
                    "titles": ", ".join(genre_books),
                }
            )
            genre_offset += percentage
        max_books = max((row["count"] for row in book_rows), default=0)
        book_chart = [
            {
                **row,
                "bar_height": round((row["count"] / max_books) * 110)
                if max_books
                else 0,
            }
            for row in book_rows
        ]
        heatmap_end = today
        heatmap_start = (
            period_start
            if period_days
            else today - timedelta(days=364)
        )
        heatmap_dates = [
            heatmap_start + timedelta(days=offset)
            for offset in range((heatmap_end - heatmap_start).days + 1)
        ]
        heatmap_pages = {
            row["day"]: row["pages"] or 0
            for row in user_activity.filter(
                timestamp__date__gte=heatmap_start,
                timestamp__date__lte=heatmap_end,
            )
            .annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(pages=Sum("pages_read"))
        }
        heatmap_max = max(heatmap_pages.values(), default=0)
        month_names = (
            "sty",
            "lut",
            "mar",
            "kwi",
            "maj",
            "cze",
            "lip",
            "sie",
            "wrz",
            "paź",
            "lis",
            "gru",
        )
        seen_months = set()
        activity_heatmap_months = []
        activity_heatmap = []
        for index, day in enumerate(heatmap_dates):
            month_key = (day.year, day.month)
            if month_key not in seen_months and day <= heatmap_end:
                activity_heatmap_months.append(
                    {
                        "label": month_names[day.month - 1],
                        "column": index // 7 + 1,
                    }
                )
                seen_months.add(month_key)
            activity_heatmap.append({
                "date": day,
                "label": day.strftime("%d.%m.%Y"),
                "pages": heatmap_pages.get(day, 0),
                "level": (
                    1
                    if heatmap_pages.get(day, 0) > 0 and heatmap_max < 4
                    else min(4, max(1, round(heatmap_pages.get(day, 0) / heatmap_max * 4)))
                    if heatmap_pages.get(day, 0)
                    else 0
                ),
            })
        stats_data = {
            "books_read": UserBook.objects.filter(
                user_id=user.id, status="finished"
            ).count(),
            "books_read_year": finished_books.filter(
                finish_date__year=today.year
            ).count(),
            "pages_total": activity_aggregate["total_pages"] or 0,
            "ppd": round(
                ((activity_aggregate["total_pages"] or 0) / account_age_days)
                if activity_aggregate["total_pages"]
                else 0.0,
                1,
            ),
            "streak": calculated_streak,
            "pages_today": daily_pages.get(today, 0),
            "pages_yesterday": daily_pages.get(today - timedelta(days=1), 0),
            "pages_year": activity_aggregate["total_pages"] or 0,
            "active_days_year": len(
                set(
                    year_activity.annotate(day=TruncDate("timestamp")).values_list(
                        "day", flat=True
                    )
                )
            ),
        }
    return render(
        request,
        "user/stats.html",
        {
            "selected_user": user,
            "stats": stats_data,
            "activity_chart": activity_chart,
            "activity_heatmap": activity_heatmap,
            "activity_heatmap_months": activity_heatmap_months,
            "book_chart": book_chart,
            "genre_chart": genre_chart,
            "genre_pie_style": genre_pie_style,
            "book_chart_period": book_chart_period,
            "book_period_label": book_period_label if user else "",
        },
    )


@login_required(login_url="login")
def recommendations(request):
    user = _get_user(request)
    recommendations_data = _add_library_status(_get_recommendations(user), user)
    return render(
        request,
        "user/recommendations.html",
        {"selected_user": user, "recommendations": recommendations_data},
    )


@login_required(login_url="login")
def profile(request):
    user = _get_user(request)
    favorite_genres = []
    avg_rating = 0.0
    active_challenges = 0
    if user:
        evaluate_achievements(user)
        favorite_genres = list(
            Genre.objects.filter(user_links__user_id=user.id).values_list("name", flat=True)
        )

        ratings = UserBook.objects.filter(user_id=user.id, rating__isnull=False).aggregate(
            avg=Avg("rating")
        )
        avg_rating = round(float(ratings["avg"] or 0.0), 2)
        active_challenges = Challenge.objects.filter(
            user_id=user.id, status="active"
        ).count()

    return render(
        request,
        "user/profile.html",
        {
            "selected_user": user,
            "favorite_genres": favorite_genres,
            "avg_rating": avg_rating,
            "active_challenges": active_challenges,
            "achievements": achievement_cards(user) if user else [],
        },
    )


@login_required(login_url="login")
def achievements(request):
    user = _get_user(request)
    evaluate_achievements(user)
    cards = achievement_cards(user)
    earned = [card for card in cards if card["earned"]]
    return render(
        request,
        "user/achievements.html",
        {
            "selected_user": user,
            "achievements": earned + [card for card in cards if not card["earned"]],
        },
    )


def logout(request):
    auth_logout(request)
    return redirect("home")