from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('reading-list/', views.reading_list, name='reading_list'),
    path('favourites/', views.favourite_books, name='favourite_books'),
    path('lists/', views.lists, name='lists'),
    path('stats/', views.stats, name='stats'),
    path('recommendations/', views.recommendations, name='recommendations'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout, name='logout'),
]