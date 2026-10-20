from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Q, Sum
from django.db.models.functions import TruncDate
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
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
    UserReadingQueue,
)


def _get_user(request):
    return request.user


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


@login_required(login_url="login")
def dashboard(request):
    user = _get_user(request)
    reading_rows = []
    books_read = 0
    active_challenges = []
    favorite_count = 0
    to_read_count = 0
    if user:
        books_read = (
            UserBook.objects.filter(user_id=user.id, status="finished").count()
        )
        reading_rows = list(
            UserBook.objects.filter(user_id=user.id, status="reading")
            .select_related("book")
            .order_by("-start_date", "id")[:2]
        )
        active_challenges = list(
            Challenge.objects.filter(user_id=user.id, status="active")
            .select_related("genre")
            .order_by("end_date", "id")[:2]
        )
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
    elif action == "unfavorite":
        UserFavoriteBook.objects.filter(user_id=request.user.id, book_id=book.id).delete()
    elif action == "to_read":
        if not UserBook.objects.filter(user_id=request.user.id, book_id=book.id).exists():
            UserReadingQueue.objects.get_or_create(user_id=request.user.id, book_id=book.id)
    elif action == "remove_to_read":
        UserReadingQueue.objects.filter(user_id=request.user.id, book_id=book.id).delete()
    elif action == "start_reading":
        UserBook.objects.get_or_create(
            user_id=request.user.id,
            book_id=book.id,
            defaults={"status": "reading", "start_date": timezone.now()},
        )
        UserReadingQueue.objects.filter(user_id=request.user.id, book_id=book.id).delete()
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
        "pages_total": 0,
        "ppd": 0.0,
        "streak": 0,
        "pages_today": 0,
        "pages_yesterday": 0,
    }
    activity_chart = []
    activity_heatmap = []
    if user:
        user_activity = Activity.objects.filter(user_id=user.id)
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
        },
    )


def logout(request):
    auth_logout(request)
    return redirect("home")