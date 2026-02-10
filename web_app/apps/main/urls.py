from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('welcome/', views.welcome, name='welcome'),
    
    path('books/most_added/', views.most_added, name='most_added'),
    path('books/trending/', views.trending, name='trending'),
    
    # Wyszukiwarka i gatunki
    path('books/explore/', views.searching, name='searching'),
    path('genres/<str:genre_name>/', views.genres, name='genres'),
]