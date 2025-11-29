from django.urls import path, include
from .views import index, main, usuarios_login, usuarios_logout

urlpatterns = [
    path('', index, name='home'),
    path('index', index, name='index'),
    path('main', main, name='main'),
    path('usuarios/login/', usuarios_login, name='usuarios-login'),
    path('usuarios/logout/', usuarios_logout, name='usuarios-logout'),
]
