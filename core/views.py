from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .models import Producto, Categoria


# Create your views here.
def obtener_productos(request, producto_id=None):
    """Renderiza la página `main.html` cargando todos los productos.

    Si se proporciona `producto_id`, devuelve sólo ese producto en el contexto
    (útil para una vista detalle). En caso contrario, carga todos los productos.
    """
    # Bloquear acceso directo a detalles por id: siempre devolver 404
    if producto_id:
        raise Http404('Acceso directo a detalle de producto no permitido')
    else:
        productos = Producto.objects.all()

    contexto = {
        'productos': productos
    }
    return render(request, 'main.html', contexto)


def listar_categorias(request):
    """Renderiza la página `categorias.html` cargando todas las categorías."""
    categorias = Categoria.objects.all()
    contexto = {
        'categorias': categorias
    }
    return render(request, 'categorias.html', contexto)


def listar_usuarios(request):
    """Renderiza la página `usuarios.html` cargando todos los usuarios."""
    from .models import Usuario
    usuarios = Usuario.objects.all()
    contexto = {
        'usuarios': usuarios
    }
    return render(request, 'usuarios.html', contexto)