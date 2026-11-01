from django.urls import path
from . import views

urlpatterns = [
    path('', views.auth_welcome, name='auth_welcome'),
    path('login/', views.login_view, name='login'),
    path('register/step1/', views.register_st1, name='register_st1'),
    path('register/step2/', views.register_st2, name='register_st2'),
    path('register/step3/', views.register_st3, name='register_st3'),
]