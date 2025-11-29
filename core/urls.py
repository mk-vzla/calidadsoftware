from django.urls import path
from . import views


urlpatterns = [
    # Ruta principal del core: lista de productos (main.html)
    path('', views.obtener_productos, name='core-main'),
    # Lista completa de productos en /core/producto/
    path('producto/', views.obtener_productos, name='producto-list'),
    # Endpoint para crear un producto desde el modal
    path('producto/add/', views.agregar_producto, name='producto-add'),
    # Endpoint JSON para obtener siguiente código por letra
    path('producto/next_code/<str:letter>/', views.next_codigo, name='producto-next-code'),
    # Lista de categorías en /core/categorias/
    path('categorias/', views.listar_categorias, name='categoria-list'),
    # Lista de usuarios en /core/usuarios/
    path('usuarios/', views.listar_usuarios, name='usuario-list'),
    # Ruta para detalle de producto por id
    path('producto/<int:producto_id>/', views.obtener_productos, name='producto-detalle'),
]
