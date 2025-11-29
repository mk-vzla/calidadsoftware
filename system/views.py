from django.shortcuts import render

# Create your views here.

def index(request):
	"""Renderiza la página principal `index.html` del app `system`."""
	return render(request, 'index.html')

def main(request):
    """Renderiza la página `main.html` del app `system`."""
    return render(request, 'main.html')