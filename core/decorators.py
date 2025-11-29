from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from .models import Usuario


def _wants_json(request):
    try:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
            return True
    except Exception:
        return False
    return False


def require_session(view_func):
    """Decorator that ensures a logged-in Usuario is present in session.

    Behavior:
    - If session contains a valid `conectado_usuario` -> proceed.
    - If not, for JSON/AJAX requests returns `JsonResponse({'error': 'No autorizado'}, status=401)`.
    - For HTML/form requests redirects to the index page.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        session_uid = request.session.get('conectado_usuario')
        if not session_uid:
            if _wants_json(request):
                return JsonResponse({'error': 'No autorizado'}, status=401)
            return redirect('index')

        try:
            Usuario.objects.get(id_usuario=session_uid)
        except Usuario.DoesNotExist:
            try:
                request.session.flush()
            except Exception:
                pass
            if _wants_json(request):
                return JsonResponse({'error': 'No autorizado'}, status=401)
            return redirect('index')

        return view_func(request, *args, **kwargs)

    return _wrapped
