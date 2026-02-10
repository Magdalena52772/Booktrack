from django.shortcuts import render, redirect

# Wyświetlanie panelu użytkownika
def dashboard(request):
    stats = {"total_hours": "12h", "books_read": 7}
    return render(request, "user/user_dashboard.html", {"stats": stats})

# Lista lektur użytkownika
def reading_list(request):
    books = ["Duna", "Wiedźmin", "Harry Potter"]
    return render(request, "user/reading_list.html", {"books": books})

# Ulubione książki
def favourite_books(request):
    favs = ["Duna", "Imię róży"]
    return render(request, "user/favourite_books.html", {"favs": favs})

# Listy użytkownika
def lists(request):
    user_lists = ["Moje 10", "Do przeczytania 2025"]
    return render(request, "user/lists.html", {"lists": user_lists})

# Statystyki czytelnictwa
def stats(request):
    stats_data = {"total_hours": "12h", "books_read": 7}
    return render(request, "user/stats.html", {"stats": stats_data})

# Rekomendacje dla użytkownika
def recommendations(request):
    recs = ["Książka A", "Książka B"]
    return render(request, "user/recommendations.html", {"recs": recs})

# Profil użytkownika
def profile(request):
    return render(request, "user/profile.html")

# Wylogowanie użytkownika
def logout(request):
    # request.session.flush() # Odpowiednik session.clear()
    return redirect('home') # 'home' to nazwa z urls.py w apps/main