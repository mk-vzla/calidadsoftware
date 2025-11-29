from django.test import TestCase, Client
from django.urls import reverse
from core.models import Producto, Categoria, Stock, MovimientoInventario, Usuario


class ProductoTests(TestCase):
    def setUp(self):
        # crear categoría y usuario de prueba
        self.cat = Categoria.objects.create(nombre='Herramientas')
        self.user = Usuario.objects.create(nombres='Test', usuario='tester', email='t@test.local')
        self.user.set_password('pass123')
        self.user.save()
        # client con sesión simulada (las vistas usan request.session['conectado_usuario'])
        self.client = Client()
        session = self.client.session
        session['conectado_usuario'] = self.user.id_usuario
        session.save()

    def test_p_ut_01_alta_basica_returns_201_and_crea_producto(self):
        url = reverse('producto-add')  # /core/producto/add/
        data = {
            'codigo_producto': 'M001',
            'nombre': 'Martillo',
            'descripcion': 'Martillo de prueba',
            'categoria': str(self.cat.id_categoria),
            'precio': '1500',
            'cantidad': '3',
        }
        resp = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # La vista debería devolver 201 y JSON con el producto creado
        self.assertEqual(resp.status_code, 201)
        # comprobar creado en DB
        p = Producto.objects.get(codigo_producto='M001')
        self.assertEqual(p.nombre, 'Martillo')
        self.assertEqual(p.precio, 1500)
        self.assertEqual(p.categoria.id_categoria, self.cat.id_categoria)
        # stock creado y movimiento ALTA
        s = Stock.objects.get(producto=p)
        self.assertEqual(s.cantidad, 3)
        mov = MovimientoInventario.objects.filter(producto=p, tipo='ALTA').first()
        self.assertIsNotNone(mov)
