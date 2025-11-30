from urllib.parse import urlparse
import time
import os
from datetime import datetime

from .test_logger import LoggedLiveServerTestCase, append_test_result
from django.contrib.sessions.backends.db import SessionStore
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options

from core.models import Usuario, Categoria, Producto, Stock


class PUtSeleniumTests(LoggedLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        opts = Options()
        # Headless by default; set env HEADLESS=0 to see the browser
        if os.environ.get('HEADLESS', '1') != '0':
            opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        cls.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except Exception:
            pass
        super().tearDownClass()

    def _create_session_for_user(self, user):
        s = SessionStore()
        s['conectado_usuario'] = user.id_usuario
        s.create()
        return s.session_key

    def _open_base_and_add_session(self, session_key):
        parsed = urlparse(self.live_server_url)
        host = parsed.hostname
        port = parsed.port
        base = f"{parsed.scheme}://{host}:{port}"
        self.driver.get(base + '/')
        cookie = {'name': 'sessionid', 'value': session_key, 'path': '/', 'domain': host}
        self.driver.add_cookie(cookie)
        return base

    def _open_add_modal_and_fill(self, base, nombre, descripcion, precio, cantidad, set_code=None):
        # Go to products page
        self.driver.get(base + '/core/producto/')
        add_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-bs-target="#agregarProductoModal"]'))
        )
        add_btn.click()
        WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'nombre')))
        self.driver.find_element(By.ID, 'nombre').clear()
        self.driver.find_element(By.ID, 'nombre').send_keys(nombre)
        self.driver.find_element(By.ID, 'descripcion').clear()
        self.driver.find_element(By.ID, 'descripcion').send_keys(descripcion)

        # populate category select if needed
        cat_select = self.driver.find_element(By.ID, 'categoria')
        options = cat_select.find_elements(By.TAG_NAME, 'option')
        for opt in options:
            val = opt.get_attribute('value')
            if val:
                opt.click()
                break

        self.driver.find_element(By.ID, 'precio').clear()
        self.driver.find_element(By.ID, 'precio').send_keys(str(precio))
        q = self.driver.find_element(By.ID, 'cantidad')
        q.clear()
        q.send_keys(str(cantidad))

        # If test needs to force a specific code (readonly field), set via JS
        if set_code is not None:
            try:
                self.driver.execute_script("document.getElementById('codigo_producto').value = arguments[0];", set_code)
            except Exception:
                pass

        # Wait for code to be non-empty or small pause
        try:
            WebDriverWait(self.driver, 3).until(lambda d: d.find_element(By.ID, 'codigo_producto').get_attribute('value') != '')
        except Exception:
            time.sleep(0.4)

        submit = self.driver.find_element(By.CSS_SELECTOR, '#formAgregarProducto button[type="submit"]')
        submit.click()

    def _save_screenshot_for(self, name):
        try:
            tests_dir = os.path.dirname(__file__)
            path = os.path.join(tests_dir, name)
            self.driver.save_screenshot(path)
        except Exception:
            pass

    def tearDown(self):
        # Only report standardized result (append_test_result) to avoid
        # writing per-test lines that include screenshot paths.
        try:
            outcome = getattr(self, '_outcome', None)
            status = 'OK'
            if outcome:
                for test, exc in getattr(outcome, 'errors', []) or []:
                    if exc:
                        status = 'FAIL'
                        break

            try:
                duration = max(0.0, time.time() - getattr(self, '_start_time', time.time()))
                append_test_result(self.id(), status, duration)
            except Exception:
                pass
        except Exception:
            pass

    def test_p_ut_01_alta_basica(self):
        # Preparar: crear categoría y usuario
        cat = Categoria.objects.create(nombre='E2E Cat')
        user = Usuario.objects.create(nombres='E2E User', usuario='e2e_user', email='e2e@example.test')
        user.set_password('e2e')
        user.save()
        session_key = self._create_session_for_user(user)
        base = self._open_base_and_add_session(session_key)

        # Ejecutar: abrir modal y crear producto
        self._open_add_modal_and_fill(base, 'E2E Martillo', 'Creado por Selenium E2E', 1500, 2)

        # Esperar creación en DB
        timeout = 10
        interval = 0.5
        waited = 0.0
        found = False
        while waited < timeout:
            if Producto.objects.filter(nombre='E2E Martillo').exists():
                found = True
                break
            time.sleep(interval)
            waited += interval

        # Guardar captura P-UT-01.png
        self._save_screenshot_for('P-UT-01.png')

        if not found:
            self._save_screenshot_for('e2e_failure_screenshot.png')
            html = self.driver.page_source[:2000]
            raise AssertionError(f"P-UT-01 falló: producto no creado en DB. HTML snapshot:\n{html}")

    def test_p_ut_02_codigo_duplicado(self):
        # Preparar: crear categoría, usuario y producto existente con código M001
        cat = Categoria.objects.create(nombre='E2E Cat')
        existing = Producto.objects.create(codigo_producto='M001', nombre='Martillo Original', descripcion='orig', categoria=cat, precio=1000, cantidad=5)
        Stock.objects.create(producto=existing, cantidad=5)
        user = Usuario.objects.create(nombres='E2E User', usuario='e2e_user2', email='e2e2@example.test')
        user.set_password('e2e')
        user.save()
        session_key = self._create_session_for_user(user)
        base = self._open_base_and_add_session(session_key)

        # Intentar crear otro producto forzando el mismo código M001
        self._open_add_modal_and_fill(base, 'E2E Dup', 'Dup producto', 1200, 1, set_code='M001')

        # Esperar un breve tiempo y comprobar que no se creó el producto duplicado
        time.sleep(1)
        exists_dup = Producto.objects.filter(nombre='E2E Dup').exists()
        codigo_count = Producto.objects.filter(codigo_producto='M001').count()

        # Guardar captura P-UT-02.png
        self._save_screenshot_for('P-UT-02.png')

        if exists_dup or codigo_count != 1:
            self._save_screenshot_for('e2e_failure_screenshot.png')
            raise AssertionError('P-UT-02 falló: se permitió crear producto duplicado o el conteo de códigos es incorrecto')

    def test_p_ut_03_codigo_formato_invalido(self):
        # Preparar: crear categoría y usuario
        cat = Categoria.objects.create(nombre='E2E Cat')
        user = Usuario.objects.create(nombres='E2E User', usuario='e2e_user3', email='e2e3@example.test')
        user.set_password('e2e')
        user.save()
        session_key = self._create_session_for_user(user)
        base = self._open_base_and_add_session(session_key)

        # Intentar crear producto con código inválido 'MX12'
        self._open_add_modal_and_fill(base, 'E2E BadCode', 'Bad code', 900, 1, set_code='MX12')

        # Esperar un poco y comprobar que no se creó el producto
        time.sleep(1)
        exists_bad = Producto.objects.filter(nombre='E2E BadCode').exists()
        code_exists = Producto.objects.filter(codigo_producto='MX12').exists()

        # Guardar captura P-UT-03.png
        self._save_screenshot_for('P-UT-03.png')

        if exists_bad or code_exists:
            self._save_screenshot_for('e2e_failure_screenshot.png')
            raise AssertionError('P-UT-03 falló: se permitió crear producto con código inválido')
