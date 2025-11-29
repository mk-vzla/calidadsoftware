from urllib.parse import urlparse
import time
import os
from datetime import datetime

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.sessions.backends.db import SessionStore
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options

from core.models import Usuario, Categoria, Producto, Stock


class ProductoE2ETest(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        opts = Options()
        # Headless by default; set env HEADLESS=0 to see the browser
        if os.environ.get('HEADLESS', '1') != '0':
            opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        # Create driver via webdriver-manager
        cls.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
        cls.driver.implicitly_wait(5)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except Exception:
            pass
        super().tearDownClass()

    def tearDown(self):
        # Log outcome for this test into core/tests/test_results.txt
        try:
            outcome = getattr(self, '_outcome', None)
            status = 'OK'
            details = ''
            if outcome:
                for test, exc in getattr(outcome, 'errors', []) or []:
                    if exc:
                        status = 'FAIL'
                        details = str(exc)
                        break

            method = getattr(self, '_testMethodName', 'unknown')
            png = 'P-UT-01.png'
            tests_dir = os.path.dirname(__file__)
            png_path = os.path.join(tests_dir, png)
            png_info = png_path if os.path.exists(png_path) else ''

            ts = datetime.now().isoformat(sep=' ', timespec='seconds')
            entry = f"{ts} | {self.__class__.__name__}.{method} | {status}"
            if png_info:
                entry += f" | screenshot: {png_info}"
            if details:
                entry += f" | {details[:300].replace('\n', ' ')}"

            results_file = os.path.join(tests_dir, 'test_results.txt')
            with open(results_file, 'a', encoding='utf-8') as f:
                f.write(entry + '\n')
        except Exception:
            pass

    def _create_session_for_user(self, user):
        """Create a Django session and return the session key."""
        s = SessionStore()
        s['conectado_usuario'] = user.id_usuario
        s.create()
        return s.session_key

    def test_agregar_producto_via_modal(self):
        # Preparar datos: crear categoría y usuario
        cat = Categoria.objects.create(nombre='E2E Cat')
        user = Usuario.objects.create(nombres='E2E User', usuario='e2e_user', email='e2e@example.test')
        user.set_password('e2e')
        user.save()

        # Crear sesión y añadir cookie al navegador
        session_key = self._create_session_for_user(user)

        # Navegar al dominio para poder añadir cookie
        parsed = urlparse(self.live_server_url)
        host = parsed.hostname
        port = parsed.port
        base = f"{parsed.scheme}://{host}:{port}"
        self.driver.get(base + '/')
        # Añadir cookie de sesión
        cookie = {'name': 'sessionid', 'value': session_key, 'path': '/', 'domain': host}
        self.driver.add_cookie(cookie)

        # Ir a la página de productos
        self.driver.get(base + '/core/producto/')

        # Abrir modal de agregar
        add_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-bs-target="#agregarProductoModal"]'))
        )
        add_btn.click()

        # Esperar modal y rellenar campos
        WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'nombre')))
        self.driver.find_element(By.ID, 'nombre').send_keys('E2E Martillo')
        self.driver.find_element(By.ID, 'descripcion').send_keys('Creado por Selenium E2E')

        # Seleccionar categoría (usar la opción disponible que no sea placeholder)
        cat_select = self.driver.find_element(By.ID, 'categoria')
        options = cat_select.find_elements(By.TAG_NAME, 'option')
        for opt in options:
            val = opt.get_attribute('value')
            if val:
                opt.click()
                break

        self.driver.find_element(By.ID, 'precio').send_keys('1500')
        q = self.driver.find_element(By.ID, 'cantidad')
        q.clear()
        q.send_keys('2')

        # Esperar a que el JS haya rellenado el código del producto (si aplica)
        try:
            WebDriverWait(self.driver, 3).until(lambda d: d.find_element(By.ID, 'codigo_producto').get_attribute('value') != '')
        except Exception:
            # Small fallback sleep to allow any pending JS to run
            time.sleep(0.4)

        # Enviar el formulario
        submit = self.driver.find_element(By.CSS_SELECTOR, '#formAgregarProducto button[type="submit"]')
        submit.click()

        # Esperar a que el servidor cree el producto consultando la DB (más robusto que buscar texto)
        timeout = 10
        interval = 0.5
        waited = 0.0
        found = False
        try:
            while waited < timeout:
                if Producto.objects.filter(nombre='E2E Martillo').exists():
                    found = True
                    break
                time.sleep(interval)
                waited += interval
        except Exception:
            # en caso de error con el ORM, capturamos pantalla para diagnóstico
            try:
                self.driver.save_screenshot('e2e_failure_screenshot.png')
            except Exception:
                pass
            raise

        # Si encontramos el producto en la BD, guardar una captura del estado final
        if found:
            try:
                tests_dir = os.path.dirname(__file__)
                path = os.path.join(tests_dir, 'P-UT-01.png')
                self.driver.save_screenshot(path)
            except Exception:
                pass

        if not found:
            try:
                self.driver.save_screenshot('e2e_failure_screenshot.png')
            except Exception:
                pass
            html = self.driver.page_source[:2000]
            raise AssertionError(f"Producto no creado en DB tras submit. HTML snapshot:\n{html}")
