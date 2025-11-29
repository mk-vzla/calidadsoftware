from urllib.parse import urlparse
import time
import os

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.sessions.backends.db import SessionStore
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options

from core.models import Usuario, Categoria, Producto


class ValidationsSeleniumTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        opts = Options()
        # Headless by default; set env HEADLESS=0 to see the browser
        if os.environ.get('HEADLESS', '1') != '0':
            opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--window-size=1280,800')
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

    def _open_add_modal_and_fill(self, base, nombre, descripcion, precio, cantidad, select_category=True, set_code=None):
        # Go to products page and open add modal
        self.driver.get(base + '/core/producto/')
        add_btn = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-bs-target="#agregarProductoModal"]'))
        )
        add_btn.click()
        WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.ID, 'nombre')))

        # Fill fields
        if nombre is not None:
            self.driver.find_element(By.ID, 'nombre').clear()
            self.driver.find_element(By.ID, 'nombre').send_keys(nombre)
        self.driver.find_element(By.ID, 'descripcion').clear()
        self.driver.find_element(By.ID, 'descripcion').send_keys(descripcion)

        # Category: choose first non-placeholder option if requested
        if select_category:
            try:
                cat_select = self.driver.find_element(By.ID, 'categoria')
                options = cat_select.find_elements(By.TAG_NAME, 'option')
                for opt in options:
                    val = opt.get_attribute('value')
                    if val:
                        opt.click()
                        break
            except Exception:
                pass

        # Price and quantity (send as string to emulate form)
        self.driver.find_element(By.ID, 'precio').clear()
        self.driver.find_element(By.ID, 'precio').send_keys(str(precio))
        q = self.driver.find_element(By.ID, 'cantidad')
        q.clear()
        q.send_keys(str(cantidad))

        # Optionally force code (readonly) via JS
        if set_code is not None:
            try:
                self.driver.execute_script("document.getElementById('codigo_producto').value = arguments[0];", set_code)
            except Exception:
                pass

        # Wait briefly for any client JS
        try:
            WebDriverWait(self.driver, 2).until(lambda d: d.find_element(By.ID, 'codigo_producto').get_attribute('value') != '')
        except Exception:
            time.sleep(0.2)

        # Submit using JS submit to bypass client validation when needed (we want server-side validation)
        try:
            self.driver.execute_script("document.getElementById('formAgregarProducto').submit();")
        except Exception:
            # fallback click
            submit = self.driver.find_element(By.CSS_SELECTOR, '#formAgregarProducto button[type="submit"]')
            submit.click()

    def _save(self, name):
        try:
            tests_dir = os.path.dirname(__file__)
            path = os.path.join(tests_dir, name)
            self.driver.save_screenshot(path)
        except Exception:
            pass

    def test_v_ut_01_precio_no_entero(self):
        """V-UT-01: precio no entero (12.50 o '12,50') debe ser rechazado"""
        cat = Categoria.objects.create(nombre='ValE2E')
        user = Usuario.objects.create(nombres='VT', usuario='vt1', email='vt1@example.test')
        user.set_password('p')
        user.save()
        session_key = self._create_session_for_user(user)
        base = self._open_base_and_add_session(session_key)

        # Use float-like string '12.50'
        self._open_add_modal_and_fill(base, 'ProdVselen1', 'desc', '12.50', 1, select_category=True)

        # Wait a bit and assert product not created
        time.sleep(1)
        found = Producto.objects.filter(nombre='ProdVselen1').exists()
        self._save('V-UT-01.png')
        self.assertFalse(found, 'V-UT-01: producto con precio no entero fue creado')

    def test_v_ut_02_nombre_vacio(self):
        """V-UT-02: nombre vacío no debe permitirse"""
        cat = Categoria.objects.create(nombre='ValE2E2')
        user = Usuario.objects.create(nombres='VT2', usuario='vt2', email='vt2@example.test')
        user.set_password('p')
        user.save()
        session_key = self._create_session_for_user(user)
        base = self._open_base_and_add_session(session_key)

        # Leave name empty
        self._open_add_modal_and_fill(base, '', 'desc', 100, 1, select_category=True)
        time.sleep(1)
        found = Producto.objects.filter(descripcion='desc').exists()
        self._save('V-UT-02.png')
        self.assertFalse(found, 'V-UT-02: producto con nombre vacío fue creado')

    def test_v_ut_03_categoria_vacia(self):
        """V-UT-03: categoría vacía -> mostrar mensaje 'Categoría requerida' y no crear producto"""
        # create a category so select has options but we will not select it
        Categoria.objects.create(nombre='ValE2E3')
        user = Usuario.objects.create(nombres='VT3', usuario='vt3', email='vt3@example.test')
        user.set_password('p')
        user.save()
        session_key = self._create_session_for_user(user)
        base = self._open_base_and_add_session(session_key)

        # Do not select category (select_category=False) and submit.
        # Force a valid code so the server-side category check is reached.
        self._open_add_modal_and_fill(base, 'ProdVselen3', 'desc3', 50, 1, select_category=False, set_code='Z010')

        # Wait for redirect/render and check for message in page
        time.sleep(1)
        page = self.driver.page_source
        self._save('V-UT-03.png')
        self.assertIn('Categoría requerida', page, 'V-UT-03: no se mostró mensaje "Categoría requerida"')
        self.assertFalse(Producto.objects.filter(nombre='ProdVselen3').exists(), 'V-UT-03: producto fue creado pese a categoría vacía')
