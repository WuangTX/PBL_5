from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Thêm đường dẫn gốc
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
]