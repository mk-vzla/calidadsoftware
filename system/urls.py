from django.urls import path, include
from .views import index, main

urlpatterns = [
    path('', index, name='home'),
    path('index', index, name='index'),
    path('main', main, name='main'),
]
