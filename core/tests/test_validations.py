import json
import os

from django.test import Client
from django.contrib.sessions.backends.db import SessionStore
from django.urls import reverse

from .test_logger import LoggedTestCase
from core.models import Usuario, Categoria


def _create_session_for_client(client, user):
    s = SessionStore()
    s['conectado_usuario'] = user.id_usuario
    s.create()
    client.cookies['sessionid'] = s.session_key


class ValidationsUnitTests(LoggedTestCase):
    def setUp(self):
        self.client = Client()

    def test_v_ut_01_precio_no_entero_rechazado(self):
        """V-UT-01: enviar precio no entero (float or string with comma) debe regresar 400"""
        cat = Categoria.objects.create(nombre='ValCat')

        user = Usuario.objects.create(nombres='VTest', usuario='v1', email='v1@example.test')
        user.set_password('p')
        user.save()
        _create_session_for_client(self.client, user)

        url = reverse('producto-add')
        # price as float
        payload = {
            'codigo_producto': 'Z001',
            'nombre': 'ProdV1',
            'descripcion': 'x',
            'categoria': cat.id_categoria,
            'precio': 12.50,
            'cantidad': 1,
        }

        resp = self.client.post(url, json.dumps(payload), content_type='application/json', HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, 400)

        # price with comma (string) should also be rejected
        payload['precio'] = '12,50'
        resp2 = self.client.post(url, json.dumps(payload), content_type='application/json', HTTP_ACCEPT='application/json')
        self.assertEqual(resp2.status_code, 400)

    def test_v_ut_02_nombre_vacio_no_permitir_guardar(self):
        """V-UT-02: nombre vacío debe fallar validación"""
        cat = Categoria.objects.create(nombre='ValCat2')

        user = Usuario.objects.create(nombres='VTest2', usuario='v2', email='v2@example.test')
        user.set_password('p')
        user.save()
        _create_session_for_client(self.client, user)

        url = reverse('producto-add')
        payload = {
            'codigo_producto': 'Y001',
            'nombre': '',
            'descripcion': 'x',
            'categoria': cat.id_categoria,
            'precio': 100,
            'cantidad': 1,
        }

        resp = self.client.post(url, json.dumps(payload), content_type='application/json', HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_v_ut_03_categoria_vacia_mensaje_especifico(self):
        """V-UT-03: categoría vacía retorna mensaje 'Categoría requerida'"""
        user = Usuario.objects.create(nombres='VTest3', usuario='v3', email='v3@example.test')
        user.set_password('p')
        user.save()
        _create_session_for_client(self.client, user)

        url = reverse('producto-add')
        payload = {
            'codigo_producto': 'X002',
            'nombre': 'ProdV3',
            'descripcion': 'x',
            'categoria': None,
            'precio': 50,
            'cantidad': 1,
        }

        resp = self.client.post(url, json.dumps(payload), content_type='application/json', HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('error', data)
        self.assertEqual(data.get('error'), 'Categoría requerida')
