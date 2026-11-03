from datetime import date, timedelta

from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from pages.models import (
    Activity,
    Book,
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
            Challenge.objects.filter(user_id=user.id, status="active")
            .select_related("genre")
            .order_by("end_date", "id")[:2]
            ),
            user,
        )
        evaluate_achievements(user)
        favorite_count = UserFavoriteBook.objects.filter(user_id=user.id).count()
        to_read_count = UserReadingQueue.objects.filter(user_id=user.id).count()
    recommendations = _get_recommendations(user, limit=2)

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
        },
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
    available_years = list(range(today.year, today.year + 5))
    challenge_type = request.POST.get("challenge_type", "quantity")
    if challenge_type not in {"quantity", "genre", "streak"}:
        challenge_type = "quantity"
    target_value = request.POST.get("target_value", "")
    selected_year = request.POST.get("year", str(today.year))
    selected_genre_id = request.POST.get("genre_id", "")
    error = ""

    if request.method == "POST":
        try:
            year = int(selected_year)
            target = int(target_value)
        except (TypeError, ValueError):
            year = today.year
            target = 0
        if year not in available_years:
            error = "Wybierz dostępny rok."
        elif target < 1 or target > 1000:
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
            "available_years": available_years,
            "challenge_type": challenge_type,
            "target_value": target_value,
            "selected_year": selected_year,
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
            .order_by("status", "-start_date", "id")
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
                if pages_read or session_minutes:
                    Activity.objects.create(
                        user_id=request.user.id,
                        book_id=user_book.book_id,
                        pages_read=pages_read,
                        session_minutes=session_minutes,
                        timestamp=timezone.now(),
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
        },
    )


@login_required(login_url="login")
def library_action(request):
    if request.method != "POST":
        return redirect("library_search")
    book = get_object_or_404(Book, id=request.POST.get("book_id"))
    action = request.POST.get("action")
    if action == "favorite":
        UserFavoriteBook.objects.get_or_create(user_id=request.user.id, book_id=book.id)
        _notify(request, request.user.id, "Książka pomyślnie dodana do listy. 📚", "book")
    elif action == "unfavorite":
        UserFavoriteBook.objects.filter(user_id=request.user.id, book_id=book.id).delete()
        _notify(
            request,
            request.user.id,
            "Zmiany zapisane. Twoja biblioteka została uporządkowana. ✅",
        )
    elif action == "to_read":
        if not UserBook.objects.filter(user_id=request.user.id, book_id=book.id).exists():
            UserReadingQueue.objects.get_or_create(user_id=request.user.id, book_id=book.id)
            _notify(request, request.user.id, "Książka pomyślnie dodana do listy. 📚", "book")
    elif action == "remove_to_read":
        UserReadingQueue.objects.filter(user_id=request.user.id, book_id=book.id).delete()
        _notify(
            request,
            request.user.id,
            "Zmiany zapisane. Twoja biblioteka została uporządkowana. ✅",
        )
    elif action == "start_reading":
        UserBook.objects.get_or_create(
            user_id=request.user.id,
            book_id=book.id,
            defaults={"status": "reading", "start_date": timezone.now()},
        )
        UserReadingQueue.objects.filter(user_id=request.user.id, book_id=book.id).delete()
        _notify(request, request.user.id, "Książka pomyślnie dodana do listy. 📚", "book")
    else:
        return redirect("library_search")
    next_view = request.POST.get("next")
    if next_view not in {"library_search", "favourite_books", "to_read_books"}:
        next_view = "library_search"
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
    book_chart_period = request.GET.get("period", "year")
    if book_chart_period not in {"week", "month", "year"}:
        book_chart_period = "year"
    activity_heatmap = []
    if user:
        evaluate_achievements(user)
        user_activity = Activity.objects.filter(user_id=user.id)
        finished_books = UserBook.objects.filter(
            user_id=user.id,
            status="finished",
            finish_date__isnull=False,
        )
        activity_aggregate = user_activity.aggregate(
            total_pages=Sum("pages_read")
        )
        daily_pages = {
            row["day"]: row["pages"] or 0
            for row in user_activity.filter(
                timestamp__date__gte=today - timedelta(days=13)
            )
            .annotate(day=TruncDate("timestamp"))
            .values("day")
            .annotate(pages=Sum("pages_read"))
        }
        chart_rows = [
            {
                "label": (today - timedelta(days=offset)).strftime("%d.%m"),
                "pages": daily_pages.get(today - timedelta(days=offset), 0),
            }
            for offset in range(13, -1, -1)
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
        if book_chart_period == "week":
            book_start = today - timedelta(days=6)
            book_counts = {
                row["period"].date(): row["count"]
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
                for offset in range(7)
            ]
            book_period_label = "ostatni tydzień"
        elif book_chart_period == "month":
            book_start = today - timedelta(days=29)
            book_counts = {
                row["period"].date(): row["count"]
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
                for offset in range(30)
            ]
            book_period_label = "ostatni miesiąc"
        else:
            year_start = date(today.year, 1, 1)
            book_counts = {
                row["period"]: row["count"]
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
                    "label": date(today.year, month, 1).strftime("%b"),
                    "count": book_counts.get(
                        date(today.year, month, 1).replace(day=1), 0
                    ),
                }
                for month in range(1, 13)
                if date(today.year, month, 1) <= today
            ]
            book_period_label = f"rok {today.year}"
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
        heatmap_start = heatmap_end - timedelta(days=364)
        heatmap_start -= timedelta(days=heatmap_start.weekday())
        heatmap_dates = [
            heatmap_start + timedelta(days=offset)
            for offset in range(((heatmap_end - heatmap_start).days // 7 + 1) * 7)
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
        activity_heatmap = [
            {
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
                "month_label": month_names[day.month - 1] if day.day <= 7 else "",
            }
            for day in heatmap_dates
        ]
        stats_data = {
            "books_read": UserBook.objects.filter(
                user_id=user.id, status="finished"
            ).count(),
            "books_read_year": finished_books.filter(
                finish_date__year=today.year
            ).count(),
            "pages_total": activity_aggregate["total_pages"] or 0,
            "ppd": round(user.pages_per_day or 0.0, 1),
            "streak": user.current_streak or 0,
            "pages_today": daily_pages.get(today, 0),
            "pages_yesterday": daily_pages.get(today - timedelta(days=1), 0),
        }
    return render(
        request,
        "user/stats.html",
        {
            "selected_user": user,
            "stats": stats_data,
            "activity_chart": activity_chart,
            "activity_heatmap": activity_heatmap,
            "book_chart": book_chart,
            "book_chart_period": book_chart_period,
            "book_period_label": book_period_label if user else "",
        },
    )


@login_required(login_url="login")
def recommendations(request):
    user = _get_user(request)
    recommendations_data = _get_recommendations(user)
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


def logout(request):
    auth_logout(request)
    return redirect("home")