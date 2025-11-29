from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.urls import reverse
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse

from .models import Producto, Categoria, MovimientoInventario, Stock


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

    # También pasamos las categorías para poblar el modal de creación
    categorias = Categoria.objects.all()

    contexto = {
        'productos': productos,
        'categorias': categorias,
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


def agregar_producto(request):
    """Procesa el POST del modal para crear un nuevo Producto.

    Espera los campos: codigo_producto, nombre, descripcion, categoria, precio
    """
    if request.method != 'POST':
        return redirect('producto-list')

    # Detectar si la petición espera JSON (API / AJAX)
    wants_json = False
    try:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
            wants_json = True
    except Exception:
        wants_json = False

    # Soportar envío JSON (application/json) y form-data
    if wants_json and request.content_type == 'application/json':
        import json
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}
        codigo = str(payload.get('codigo_producto', '') or '').strip().upper()
        nombre = str(payload.get('nombre', '') or '').strip()
        descripcion = str(payload.get('descripcion', '') or '').strip()
        categoria_id = payload.get('categoria')
        precio_raw = payload.get('precio')
    else:
        codigo = request.POST.get('codigo_producto', '').strip().upper()
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        categoria_id = request.POST.get('categoria')
        precio_raw = request.POST.get('precio')

    # Validaciones básicas
    if not (codigo and nombre and descripcion and categoria_id is not None and precio_raw is not None):
        msg = 'Todos los campos son obligatorios.'
        if wants_json:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('producto-list')

    try:
        categoria = Categoria.objects.get(id_categoria=categoria_id)
    except Categoria.DoesNotExist:
        msg = 'Categoría no encontrada.'
        if wants_json:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('producto-list')

    try:
        # precio_raw puede venir como string o número
        precio = int(precio_raw)
        if precio < 0:
            raise ValueError
    except ValueError:
        msg = 'El precio debe ser un número entero mayor o igual a 0.'
        if wants_json:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('producto-list')

    producto = Producto(
        codigo_producto=codigo,
        nombre=nombre,
        descripcion=descripcion,
        categoria=categoria,
        precio=precio,
    )

    # Check duplicates proactively to provide specific messages
    if Producto.objects.filter(codigo_producto=codigo).exists():
        msg = f'El código {codigo} ya existe.'
        if wants_json:
            return JsonResponse({'error': msg}, status=409)
        messages.error(request, msg)
        return redirect('producto-list')
    if Producto.objects.filter(nombre__iexact=nombre).exists():
        msg = f'Ya existe un producto con el nombre "{nombre}".'
        if wants_json:
            return JsonResponse({'error': msg}, status=409)
        messages.error(request, msg)
        return redirect('producto-list')

    try:
        # Guardar producto, stock inicial y registro de movimiento en una transacción
        with transaction.atomic():
            producto.full_clean()
            producto.save()
            # Crear stock inicial (0) y registrar movimiento de ALTA
            Stock.objects.create(producto=producto, cantidad=0)
            MovimientoInventario.objects.create(producto=producto, usuario=None, cantidad=0, tipo='ALTA')
    except ValidationError as e:
        # e.message_dict es un dict de listas
        errores = []
        if hasattr(e, 'message_dict'):
            for v in e.message_dict.values():
                errores.extend(v)
        else:
            errores = [str(e)]
        msg = 'Errores: ' + '; '.join(errores)
        if wants_json:
            return JsonResponse({'error': msg, 'details': errores}, status=400)
        messages.error(request, msg)
        return redirect('producto-list')
    except IntegrityError:
        msg = 'Error de integridad al crear el producto.'
        if wants_json:
            return JsonResponse({'error': msg}, status=500)
        messages.error(request, msg)
        return redirect('producto-list')

    # Éxito: responder 201 para API o redirect con mensaje para HTML
    success_msg = f'Producto "{producto.nombre}" creado correctamente.'
    if wants_json:
        data = {
            'id': producto.id_producto,
            'codigo_producto': producto.codigo_producto,
            'nombre': producto.nombre,
            'descripcion': producto.descripcion,
            'categoria': producto.categoria.id_categoria,
            'precio': producto.precio,
        }
        return JsonResponse(data, status=201)
    messages.success(request, success_msg)
    return redirect('producto-list')


def next_codigo(request, letter):
    """Devuelve en JSON el siguiente código secuencial para una letra dada.

    Por ejemplo, si existen M001 y M002, devuelve M003.
    """
    letter = (letter or '').upper()
    if not letter or not letter.isalpha() or len(letter) != 1:
        return JsonResponse({'error': 'Letra inválida'}, status=400)

    # Contar productos cuyo codigo comienza con la letra (A-Z)
    # Los códigos tienen formato LNNN (ej: M001)
    existentes = Producto.objects.filter(codigo_producto__startswith=letter).values_list('codigo_producto', flat=True)
    max_seq = 0
    for c in existentes:
        try:
            seq = int(c[1:])
            if seq > max_seq:
                max_seq = seq
        except Exception:
            continue

    siguiente = max_seq + 1
    siguiente_str = str(siguiente).zfill(3)
    next_code = f"{letter}{siguiente_str}"
    return JsonResponse({'next_code': next_code, 'next_seq': siguiente_str})