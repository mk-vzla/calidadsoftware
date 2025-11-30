import json
from django.test import Client
from django.urls import reverse
from django.contrib.sessions.backends.db import SessionStore
from .test_logger import LoggedTestCase

from core.models import Usuario, Categoria, Producto, Stock, MovimientoInventario


def _create_session_for_client(client, user):
    s = SessionStore()
    s['conectado_usuario'] = user.id_usuario
    s.create()
    client.cookies['sessionid'] = s.session_key


class StockUnitTests(LoggedTestCase):
    def setUp(self):
        self.client = Client()

    def test_s_ut_01_agregar_stock_incrementa(self):
        """S-UT-01: incrementar stock en +10 y registrar movimiento"""
        cat = Categoria.objects.create(nombre='StockCat')
        prod = Producto.objects.create(codigo_producto='A001', nombre='ProdStock', descripcion='x', categoria=cat, precio=1000, cantidad=5)
        Stock.objects.create(producto=prod, cantidad=5)

        user = Usuario.objects.create(nombres='Test', usuario='t1', email='t1@example.test')
        user.set_password('t')
        user.save()
        _create_session_for_client(self.client, user)

        url = reverse('producto-update', args=[prod.id_producto])
        new_qty = 5 + 10
        data = {
            'nombre': prod.nombre,
            'descripcion': prod.descripcion,
            'categoria': prod.categoria.id_categoria,
            'precio': prod.precio,
            'cantidad': new_qty,
        }

        resp = self.client.post(url, data)
        self.assertIn(resp.status_code, (302, 200))

        stock = Stock.objects.get(producto=prod)
        self.assertEqual(stock.cantidad, new_qty)

        mov = MovimientoInventario.objects.filter(producto=prod, tipo='MODI').first()
        self.assertIsNotNone(mov, 'No se registró movimiento MODI')
        self.assertEqual(mov.cantidad, 10)
        # Comprobar contenido de resumen_operacion: intentar parsear JSON o validar texto legible
        resumen = mov.resumen_operacion or ''
        parsed = None
        try:
            parsed = json.loads(resumen)
        except Exception:
            parsed = None

        if parsed and isinstance(parsed, dict) and 'antes' in parsed and 'despues' in parsed:
            antes = parsed.get('antes')
            despues = parsed.get('despues')
            # si hay cantidad dentro de antes/despues
            if isinstance(antes, dict) and isinstance(despues, dict):
                self.assertEqual(int(antes.get('cantidad') or 0), 5)
                self.assertEqual(int(despues.get('cantidad') or 0), 15)
        else:
            # buscar texto legible: "Cantidad 5 a 15" o "5 a 15"
            self.assertIn('Cantidad', resumen) or self.assertIn('cantidad', resumen.lower())
            self.assertIn('5', resumen)
            self.assertIn('15', resumen)

    def test_s_ut_02_restar_stock_valido(self):
        """S-UT-02: restar 5 cuando stock >=5, no quedar negativo y registrar movimiento"""
        cat = Categoria.objects.create(nombre='StockCat2')
        prod = Producto.objects.create(codigo_producto='A002', nombre='ProdStock2', descripcion='x', categoria=cat, precio=500, cantidad=10)
        Stock.objects.create(producto=prod, cantidad=10)

        user = Usuario.objects.create(nombres='Test2', usuario='t2', email='t2@example.test')
        user.set_password('t')
        user.save()
        _create_session_for_client(self.client, user)

        url = reverse('producto-update', args=[prod.id_producto])
        new_qty = 10 - 5
        data = {
            'nombre': prod.nombre,
            'descripcion': prod.descripcion,
            'categoria': prod.categoria.id_categoria,
            'precio': prod.precio,
            'cantidad': new_qty,
        }

        resp = self.client.post(url, data)
        self.assertIn(resp.status_code, (302, 200))

        stock = Stock.objects.get(producto=prod)
        self.assertEqual(stock.cantidad, new_qty)

        mov = MovimientoInventario.objects.filter(producto=prod, tipo='MODI').first()
        self.assertIsNotNone(mov, 'No se registró movimiento MODI')
        self.assertEqual(mov.cantidad, 5)
        # Validar resumen_operacion contiene antes/despues de cantidad
        resumen = mov.resumen_operacion or ''
        parsed = None
        try:
            parsed = json.loads(resumen)
        except Exception:
            parsed = None

        if parsed and isinstance(parsed, dict) and 'antes' in parsed and 'despues' in parsed:
            antes = parsed.get('antes')
            despues = parsed.get('despues')
            if isinstance(antes, dict) and isinstance(despues, dict):
                self.assertEqual(int(antes.get('cantidad') or 0), 10)
                self.assertEqual(int(despues.get('cantidad') or 0), 5)
        else:
            self.assertIn('Cantidad', resumen) or self.assertIn('cantidad', resumen.lower())
            self.assertIn('10', resumen)
            self.assertIn('5', resumen)

    def test_s_ut_03_restar_a_negativo_bloqueado(self):
        """S-UT-03: intentar restar más del stock actual debe fallar y no modificar stock"""
        cat = Categoria.objects.create(nombre='StockCat3')
        prod = Producto.objects.create(codigo_producto='A003', nombre='ProdStock3', descripcion='x', categoria=cat, precio=200, cantidad=10)
        Stock.objects.create(producto=prod, cantidad=10)

        user = Usuario.objects.create(nombres='Test3', usuario='t3', email='t3@example.test')
        user.set_password('t')
        user.save()
        _create_session_for_client(self.client, user)

        url = reverse('producto-update', args=[prod.id_producto])
        # Send as JSON and request JSON response to get status codes from view
        payload = {
            'nombre': prod.nombre,
            'descripcion': prod.descripcion,
            'categoria': prod.categoria.id_categoria,
            'precio': prod.precio,
            'cantidad': -90,  # would lead to negative stock if applied
        }

        resp = self.client.post(url, json.dumps(payload), content_type='application/json', HTTP_ACCEPT='application/json')
        # View should return 400 for invalid negative quantity
        self.assertEqual(resp.status_code, 400)

        stock = Stock.objects.get(producto=prod)
        self.assertEqual(stock.cantidad, 10, 'Stock se modificó pese a operación bloqueada')

        mov = MovimientoInventario.objects.filter(producto=prod).first()
        # No debe haberse creado movimiento MODI
        self.assertIsNone(mov, 'Se registró movimiento pese a operación inválida')
