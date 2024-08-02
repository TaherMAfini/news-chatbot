from django.urls import path

from pages import views

urlpatterns = [
    path("", views.home, name="home"),
    path("latest", views.latest, name="latest"),
    path("summarize", views.summary, name="summary"),
    path("chat", views.chat, name="chat"),
]
