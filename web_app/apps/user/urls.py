from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('notifications/', views.notifications, name='notifications'),
    path('challenges/new/', views.create_challenge, name='create_challenge'),
    path('reading-list/', views.reading_list, name='reading_list'),
    path('books/<int:user_book_id>/', views.user_book_detail, name='user_book_detail'),
    path('favourites/', views.favourite_books, name='favourite_books'),
    path('to-read/', views.to_read_books, name='to_read_books'),
    path('library/search/', views.library_search, name='library_search'),
    path('library/action/', views.library_action, name='library_action'),
    path('stats/', views.stats, name='stats'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout, name='logout'),
]