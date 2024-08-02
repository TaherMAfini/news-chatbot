import os

from django import get_version
from django.conf import settings
from django.shortcuts import render
import ninja


def home(request):
    context = {
        "debug": settings.DEBUG,
        "django_ver": get_version(),
        "python_ver": os.environ["PYTHON_VERSION"],
        "ninja_ver": ninja.__version__,
    }

    return render(request, "pages/home.html", context)

def latest(request):
    return render(request, "pages/latest.html")

def summary(request):
    return render(request, "pages/summary.html")

def chat(request):
    return render(request, "pages/chat.html")