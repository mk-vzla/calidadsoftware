from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.urls import reverse
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse

from .models import Producto, Categoria, MovimientoInventario, Stock, Usuario
from django.db.models import Q


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
        # Soportar búsqueda por query string ?q=texto (por código o nombre)
        q = request.GET.get('q', '').strip()
        if q:
            productos = Producto.objects.filter(
                Q(codigo_producto__icontains=q) | Q(nombre__icontains=q)
            ).order_by('codigo_producto')
        else:
            productos = Producto.objects.all().order_by('codigo_producto')

    # También pasamos las categorías para poblar el modal de creación
    categorias = Categoria.objects.all()

    contexto = {
        'productos': productos,
        'categorias': categorias,
        'q': q if 'q' in locals() else '',
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
    # Soportar búsqueda por query string ?q=texto (por usuario o nombres)
    q = request.GET.get('q', '').strip()
    if q:
        usuarios = Usuario.objects.filter(
            Q(usuario__icontains=q) | Q(nombres__icontains=q)
        ).order_by('id_usuario')
    else:
        usuarios = Usuario.objects.all().order_by('id_usuario')

    contexto = {
        'usuarios': usuarios,
        'q': q,
    }
    return render(request, 'usuarios.html', contexto)


def _get_session_usuario(request):
    """Devuelve la instancia `Usuario` guardada en sesión (`conectado_usuario`) o None."""
    session_uid = request.session.get('conectado_usuario')
    if not session_uid:
        return None
    try:
        return Usuario.objects.get(id_usuario=session_uid)
    except Usuario.DoesNotExist:
        # limpiar sesión si el id es inválido
        try:
            request.session.flush()
        except Exception:
            pass
        return None


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
        cantidad_raw = payload.get('cantidad')
    else:
        codigo = request.POST.get('codigo_producto', '').strip().upper()
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        categoria_id = request.POST.get('categoria')
        precio_raw = request.POST.get('precio')
        cantidad_raw = request.POST.get('cantidad')

    # Validaciones básicas (incluye cantidad)
    if not (codigo and nombre and descripcion and categoria_id is not None and precio_raw is not None and cantidad_raw is not None):
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
    except (ValueError, TypeError):
        msg = 'El precio debe ser un número entero mayor o igual a 0.'
        if wants_json:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('producto-list')

    # validar cantidad
    try:
        cantidad = int(cantidad_raw)
        if cantidad < 0:
            raise ValueError
    except (ValueError, TypeError):
        msg = 'La cantidad debe ser un número entero mayor o igual a 0.'
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
        cantidad=cantidad,
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
            # Crear stock inicial con la cantidad proporcionada y registrar movimiento de ALTA
            Stock.objects.create(producto=producto, cantidad=cantidad)
            mov_usuario = _get_session_usuario(request)
            MovimientoInventario.objects.create(
                producto=producto,
                usuario_id=(mov_usuario.id_usuario if mov_usuario else None),
                cantidad=cantidad,
                tipo='ALTA',
                resumen_operacion='alta',
                producto_nombre=producto.nombre,
                producto_codigo=producto.codigo_producto,
            )
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
        # Posible condición de carrera: si otro request creó el mismo código/nombre
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
            'cantidad': producto.cantidad,
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


def obtener_producto_json(request, producto_id):
    """Devuelve los datos del producto en JSON para rellenar el modal de edición."""
    try:
        producto = Producto.objects.select_related('categoria').get(id_producto=producto_id)
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)

    data = {
        'id': producto.id_producto,
        'codigo_producto': producto.codigo_producto,
        'nombre': producto.nombre,
        'descripcion': producto.descripcion,
        'categoria': producto.categoria.id_categoria if producto.categoria else None,
        'precio': producto.precio,
        'cantidad': producto.cantidad,
    }
    return JsonResponse(data)


def eliminar_producto(request, producto_id):
    """Elimina un producto identificado por `producto_id`.

    Acepta sólo POST. Redirige a la lista con un mensaje.
    """
    if request.method != 'POST':
        return redirect('producto-list')

    producto = get_object_or_404(Producto, id_producto=producto_id)
    nombre = producto.nombre

    # Antes de eliminar, registrar en MovimientoInventario un movimiento de tipo BAJA
    # Usar la cantidad desde Stock si existe, si no usar el campo cantidad del producto
    try:
        stock = Stock.objects.get(producto=producto)
        baja_cantidad = int(stock.cantidad or 0)
    except Stock.DoesNotExist:
        baja_cantidad = int(producto.cantidad or 0)

    try:
        with transaction.atomic():
            # Registrar movimiento de BAJA (guardar también nombre y código para auditoría)
            mov_usuario = _get_session_usuario(request)
            MovimientoInventario.objects.create(
                producto=producto,
                usuario_id=(mov_usuario.id_usuario if mov_usuario else None),
                cantidad=baja_cantidad,
                tipo='BAJA',
                resumen_operacion=f'baja {producto.codigo_producto}',
                producto_nombre=producto.nombre,
                producto_codigo=producto.codigo_producto,
            )
            # Borrar el producto (esto también eliminará Stock y relaciones por cascade)
            producto.delete()
    except Exception:
        messages.error(request, f'No se pudo eliminar el producto "{nombre}".')
        return redirect('producto-list')

    messages.success(request, f'Producto "{nombre}" eliminado correctamente y movimiento BAJA registrado.')
    return redirect('producto-list')


def actualizar_producto(request, producto_id):
    """Actualiza un producto a partir de POST (desde modal de edición).

    Si la `cantidad` cambia, registra un MovimientoInventario de tipo `MODI`.
    """
    if request.method != 'POST':
        return redirect('producto-list')

    # Soportar form-data y JSON similar a agregar_producto
    wants_json = False
    try:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
            wants_json = True
    except Exception:
        wants_json = False

    if wants_json and request.content_type == 'application/json':
        import json
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}
        nombre = str(payload.get('nombre', '') or '').strip()
        descripcion = str(payload.get('descripcion', '') or '').strip()
        categoria_id = payload.get('categoria')
        precio_raw = payload.get('precio')
        cantidad_raw = payload.get('cantidad')
    else:
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        categoria_id = request.POST.get('categoria')
        precio_raw = request.POST.get('precio')
        cantidad_raw = request.POST.get('cantidad')

    producto = get_object_or_404(Producto, id_producto=producto_id)

    # Validaciones básicas
    if not (nombre and descripcion and categoria_id is not None and precio_raw is not None and cantidad_raw is not None):
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
        precio = int(precio_raw)
        if precio < 0:
            raise ValueError
    except (ValueError, TypeError):
        msg = 'El precio debe ser un número entero mayor o igual a 0.'
        if wants_json:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('producto-list')

    try:
        cantidad = int(cantidad_raw)
        if cantidad < 0:
            raise ValueError
    except (ValueError, TypeError):
        msg = 'La cantidad debe ser un número entero mayor o igual a 0.'
        if wants_json:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('producto-list')

    # Detección de duplicados: nombre (otro producto con mismo nombre)
    if Producto.objects.filter(nombre__iexact=nombre).exclude(id_producto=producto.id_producto).exists():
        msg = f'Ya existe otro producto con el nombre "{nombre}".'
        if wants_json:
            return JsonResponse({'error': msg}, status=409)
        messages.error(request, msg)
        return redirect('producto-list')

    # Guardar cambios y gestionar stock/movimientos en transacción
    try:
        with transaction.atomic():
            # Registrar valores previos
            try:
                stock = Stock.objects.get(producto=producto)
                prev_stock = int(stock.cantidad or 0)
            except Stock.DoesNotExist:
                stock = None
                prev_stock = None

            # Capturar valores previos de otros campos para detectar modificaciones
            prev_nombre = producto.nombre
            prev_descripcion = producto.descripcion
            prev_categoria_id = producto.categoria.id_categoria if producto.categoria else None
            prev_precio = producto.precio

            # Valores previos y entrantes (debug removido)

            # Actualizar campos del producto
            producto.nombre = nombre
            producto.descripcion = descripcion
            producto.categoria = categoria
            producto.precio = precio
            producto.cantidad = cantidad

            producto.full_clean()
            producto.save()

            # Actualizar / crear stock
            mov_created = False
            if stock is None:
                # crear stock nuevo
                stock = Stock.objects.create(producto=producto, cantidad=cantidad)
                # Si cantidad > 0, registrar movimiento MODI (ajuste)
                if cantidad and cantidad != 0:
                    mov_usuario = _get_session_usuario(request)
                    MovimientoInventario.objects.create(
                        producto=producto,
                        usuario_id=(mov_usuario.id_usuario if mov_usuario else None),
                        cantidad=abs(cantidad),
                        tipo='MODI',
                        resumen_operacion=f'stock establecido {abs(cantidad)}',
                        producto_nombre=producto.nombre,
                        producto_codigo=producto.codigo_producto,
                    )
                    mov_created = True
            else:
                # calcular diferencia
                diff = cantidad - prev_stock
                # cálculo de diferencia (debug removido)
                if diff != 0:
                    # Bloquear si el nuevo stock sería negativo (no permitir dejar stock < 0)
                    if cantidad < 0:
                        msg = 'No se puede establecer una cantidad negativa en stock.'
                        if wants_json:
                            return JsonResponse({'error': msg}, status=400)
                        messages.error(request, msg)
                        return redirect('producto-list')

                    # crear movimiento MODI con la cantidad absoluta del cambio
                    mov_usuario = _get_session_usuario(request)
                    # construir resumen según aumento/disminución
                    if diff > 0:
                        resumen = f'stock aumentado {abs(diff)}'
                    else:
                        resumen = f'stock disminuido {abs(diff)}'
                    MovimientoInventario.objects.create(
                        producto=producto,
                        usuario_id=(mov_usuario.id_usuario if mov_usuario else None),
                        cantidad=abs(diff),
                        tipo='MODI',
                        resumen_operacion=resumen,
                        producto_nombre=producto.nombre,
                        producto_codigo=producto.codigo_producto,
                    )
                    mov_created = True
                # actualizar stock al nuevo valor
                stock.cantidad = cantidad
                stock.save()

            # Si no creamos movimiento por cambio de cantidad, pero sí cambiaron otros campos,
            # registrar un movimiento MODI con cantidad=0 para auditar la modificación.
            other_changed = (
                prev_nombre != nombre or
                prev_descripcion != descripcion or
                prev_categoria_id != (categoria.id_categoria if categoria else None) or
                prev_precio != precio
            )
            if not mov_created and other_changed:
                mov_usuario = _get_session_usuario(request)
                # construir resumen para otros cambios
                cambios = []
                try:
                    if prev_precio != precio:
                        dp = precio - (prev_precio or 0)
                        if dp > 0:
                            cambios.append(f'precio aumentado {dp}')
                        else:
                            cambios.append(f'precio disminuido {abs(dp)}')
                except Exception:
                    pass
                try:
                    if prev_nombre != nombre:
                        cambios.append('nombre modificado')
                except Exception:
                    pass
                try:
                    if prev_descripcion != descripcion:
                        cambios.append('descripcion modificada')
                except Exception:
                    pass
                try:
                    if prev_categoria_id != (categoria.id_categoria if categoria else None):
                        cambios.append('categoria modificada')
                except Exception:
                    pass
                resumen = '; '.join(cambios) if cambios else 'modificación'
                MovimientoInventario.objects.create(
                    producto=producto,
                    usuario_id=(mov_usuario.id_usuario if mov_usuario else None),
                    cantidad=0,
                    tipo='MODI',
                    resumen_operacion=resumen,
                    producto_nombre=producto.nombre,
                    producto_codigo=producto.codigo_producto,
                )

    except ValidationError as e:
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
        msg = 'Error de integridad al actualizar el producto.'
        if wants_json:
            return JsonResponse({'error': msg}, status=500)
        messages.error(request, msg)
        return redirect('producto-list')

    success_msg = f'Producto "{producto.nombre}" actualizado correctamente.'
    if wants_json:
        return JsonResponse({'id': producto.id_producto, 'nombre': producto.nombre}, status=200)
    messages.success(request, success_msg)
    return redirect('producto-list')