from django.urls import path, include

urlpatterns = [
    path('', include('webuser.user.urls')),
]
