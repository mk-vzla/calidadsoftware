from django.shortcuts import render, redirect
from django.http import JsonResponse
import json

from core.models import Usuario, Producto


def index(request):
	"""Renderiza la página principal `index.html` del app `system`."""
	return render(request, 'index.html')


def main(request):
	"""Renderiza la página `main.html` del app `system`."""
	# Pasar la lista de productos al template para que se muestren en /main
	q = request.GET.get('q', '').strip()
	productos_qs = Producto.objects.select_related('categoria').all()
	if q:
		productos_qs = productos_qs.filter(
			models.Q(codigo_producto__icontains=q) | models.Q(nombre__icontains=q)
		)

	productos = list(productos_qs)
	context = {
		'productos': productos,
		'q': q,
	}
	return render(request, 'main.html', context)


def usuarios_login(request):
	"""
	Endpoint JSON para login via AJAX.

	Espera POST con JSON: {"username": "...", "password": "..."}
	Si las credenciales son válidas, guarda `request.session['conectado_usuario']`.
	Devuelve JSON 200 en éxito o 400 con {'error': '...'} en fallo.
	"""
	if request.method != 'POST':
		return JsonResponse({'error': 'Método no permitido'}, status=405)

	try:
		data = json.loads(request.body.decode('utf-8'))
	except Exception:
		return JsonResponse({'error': 'JSON no válido'}, status=400)

	username = data.get('username')
	password = data.get('password')

	if not username or not password:
		return JsonResponse({'error': 'Usuario y contraseña requeridos'}, status=400)

	try:
		usuario = Usuario.objects.get(usuario=username)
	except Usuario.DoesNotExist:
		return JsonResponse({'error': 'Credenciales inválidas'}, status=400)

	if not usuario.check_password(password):
		return JsonResponse({'error': 'Credenciales inválidas'}, status=400)

	# Autenticado: guardar id en sesión para que el context processor lo lea
	request.session['conectado_usuario'] = usuario.id_usuario
	request.session.modified = True

	return JsonResponse({'mensaje': 'ok'})


def usuarios_logout(request):
	"""Cerrar sesión (flush) y redirigir a index."""
	request.session.flush()
	return redirect('index')