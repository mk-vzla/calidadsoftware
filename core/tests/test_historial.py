from django.urls import reverse
from .test_logger import LoggedTestCase

from core.models import Usuario, Categoria, Producto, MovimientoInventario, Stock


class HistorialTests(LoggedTestCase):
    def setUp(self):
        # usuario que realizará las acciones
        self.user = Usuario.objects.create(nombres='Hist', usuario='hist1', email='hist1@example.test')
        self.user.set_password('p')
        self.user.save()

        # categoría inicial
        self.cat1 = Categoria.objects.create(nombre='CatHist1')
        self.cat2 = Categoria.objects.create(nombre='CatHist2')

    def _login_session(self):
        # Simular sesión guardando conectado_usuario en la sesión del cliente
        session = self.client.session
        session['conectado_usuario'] = self.user.id_usuario
        session.save()

    def test_h_ut_01_alta_crea_registro(self):
        """H-UT-01: Al crear un producto se genera un MovimientoInventario tipo 'ALTA'"""
        self._login_session()

        data = {
            'codigo_producto': 'H001',
            'nombre': 'ProductoHist1',
            'descripcion': 'Desc hist',
            'categoria': str(self.cat1.id_categoria),
            'precio': '100',
            'cantidad': '5',
        }

        resp = self.client.post('/core/producto/add/', data)
        # esperar redirección a la lista
        self.assertIn(resp.status_code, (302, 201))

        # Comprobar movimiento ALTA
        mov = MovimientoInventario.objects.filter(producto_codigo='H001', tipo='ALTA').first()
        print('\n[H-UT-01] Movimiento creado:', mov)
        if mov:
            print('[H-UT-01] detalles:', mov.resumen_operacion, 'usuario_id=', mov.usuario_id)

        self.assertIsNotNone(mov, 'H-UT-01: no se creó movimiento ALTA al agregar producto')
        self.assertEqual(mov.tipo, 'ALTA')

    def test_h_ut_02_modificacion_registra(self):
        """H-UT-02: Al modificar un producto (cambio de categoría) se crea MovimientoInventario tipo 'MODI'"""
        # crear producto inicial
        prod = Product = Producto.objects.create(
            codigo_producto='H002',
            nombre='ProductoHist2',
            descripcion='Desc',
            categoria=self.cat1,
            precio=200,
            cantidad=10,
        )
        # crear stock asociado
        Stock.objects.create(producto=prod, cantidad=10)

        self._login_session()

        update_data = {
            'nombre': 'ProductoHist2',
            'descripcion': 'Desc mod',
            'categoria': str(self.cat2.id_categoria),
            'precio': '200',
            'cantidad': '10',
        }

        resp = self.client.post(f'/core/producto/update/{prod.id_producto}/', update_data)
        self.assertIn(resp.status_code, (302, 200))

        mov = MovimientoInventario.objects.filter(producto=prod, tipo='MODI').first()
        print('\n[H-UT-02] Movimiento creado:', mov)
        if mov:
            print('[H-UT-02] detalles:', mov.resumen_operacion, 'usuario_id=', mov.usuario_id)

        self.assertIsNotNone(mov, 'H-UT-02: no se creó movimiento MODI al modificar producto')
        # movimientos por cambio de categoría usan tipo 'MODI'
        self.assertEqual(mov.tipo, 'MODI')
