from core.models import Usuario

def session_data(request):
    """
    Context processor to add user session data to templates.
    """
    conectado_usuario = request.session.get('conectado_usuario', None)
    if conectado_usuario:
        try:
            usuario = Usuario.objects.get(id_usuario=conectado_usuario)
            return {
                'session_user_is_authenticated': True,
                'session_usuario_id': usuario.id_usuario,
                'session_usuario_nombre': usuario.nombres,
                'session_usuario_username': usuario.usuario,
                'session_usuario_email': usuario.email,
            }
        except Usuario.DoesNotExist:
            request.session.flush()
    return {
        'session_user_is_authenticated': False,
        'session_usuario_id': None,
        'session_usuario_nombre': None,
        'session_usuario_username': None,
        'session_usuario_email': None,
    }