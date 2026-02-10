from django.shortcuts import render

# Strona główna aplikacji
def home(request):
    return render(request, "public/index.html")

# Widok najczęściej dodawanych książek
def most_added(request):
    return render(request, "books/most_added.html")

# Widok trendujących książek
def trending(request):
    return render(request, "books/trending.html")

# Widok konkretnego gatunku
def genres(request, genre_name):
    return render(request, "books/genres.html", {"genre": genre_name})

# Widok wyszukiwarki/eksploracji
def searching(request):
    return render(request, "books/explore.html")

# Widok powitalny (strona przed logowaniem)
def welcome(request):
    return render(request, "auth/welcome.html")