from django.urls import path

from .views import db

urlpatterns = [
    path("", db.urls, name="db"),
]
