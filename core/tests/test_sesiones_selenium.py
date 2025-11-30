import os
import time
from urllib.parse import urlparse

from .test_logger import LoggedLiveServerTestCase
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options

from core.models import Usuario


class SesionesSeleniumTests(LoggedLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        opts = Options()
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

    def _save(self, name):
        try:
            tests_dir = os.path.dirname(__file__)
            path = os.path.join(tests_dir, name)
            self.driver.save_screenshot(path)
        except Exception:
            pass

    def test_a_ut_01_login_correcto(self):
        """A-UT-01: Login correcto crea sesión y redirige a /main"""
        user = Usuario.objects.create(nombres='Auth', usuario='auth1', email='auth1@example.test')
        user.set_password('pw')
        user.save()

        parsed = urlparse(self.live_server_url)
        base = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"

        # Open login page
        self.driver.get(base + '/')
        # Fill form
        self.driver.find_element(By.ID, 'username').send_keys('auth1')
        self.driver.find_element(By.ID, 'password').send_keys('pw')
        # Submit (login_validations.js will send AJAX and redirect)
        self.driver.find_element(By.CSS_SELECTOR, '#loginForm button[type="submit"]').click()

        # Wait until redirected to /main
        WebDriverWait(self.driver, 5).until(EC.url_contains('/main'))

        # Check session cookie exists
        cookie = self.driver.get_cookie('sessionid')
        self._save('A-UT-01.png')
        self.assertIsNotNone(cookie, 'A-UT-01: no session cookie after successful login')

        # Verify session on server stores conectado_usuario
        session_key = cookie['value']
        s = SessionStore(session_key=session_key)
        data = s.load()
        self.assertIn('conectado_usuario', data)
        self.assertEqual(data['conectado_usuario'], user.id_usuario)

    def test_a_ut_02_login_fallido(self):
        """A-UT-02: Login fallido con credenciales incorrectas no crea sesión y muestra error"""
        user = Usuario.objects.create(nombres='Auth2', usuario='auth2', email='auth2@example.test')
        user.set_password('pw')
        user.save()

        parsed = urlparse(self.live_server_url)
        base = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"

        self.driver.get(base + '/')
        self.driver.find_element(By.ID, 'username').send_keys('auth2')
        # wrong password
        self.driver.find_element(By.ID, 'password').send_keys('wrong')
        self.driver.find_element(By.CSS_SELECTOR, '#loginForm button[type="submit"]').click()

        # Wait for client error message container to show an alert
        try:
            WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '#client-messages .alert')))
        except Exception:
            pass

        self._save('A-UT-02.png')
        # Ensure no session cookie created
        cookie = self.driver.get_cookie('sessionid')
        self.assertIsNone(cookie, 'A-UT-02: session cookie should not exist after failed login')

        # Assert page displays invalid credentials message
        page = self.driver.page_source
        self.assertIn('Credenciales inválidas', page)

    def test_a_ut_03_timeout_por_inactividad(self):
        """A-UT-03: sesión expirada debe hacer que la siguiente petición AJAX devuelva 401"""
        user = Usuario.objects.create(nombres='Auth3', usuario='auth3', email='auth3@example.test')
        user.set_password('pw')
        user.save()

        parsed = urlparse(self.live_server_url)
        base = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"

        # Login via UI
        self.driver.get(base + '/')
        self.driver.find_element(By.ID, 'username').send_keys('auth3')
        self.driver.find_element(By.ID, 'password').send_keys('pw')
        self.driver.find_element(By.CSS_SELECTOR, '#loginForm button[type="submit"]').click()
        WebDriverWait(self.driver, 5).until(EC.url_contains('/main'))

        # Grab session cookie and ensure session exists
        cookie = self.driver.get_cookie('sessionid')
        self.assertIsNotNone(cookie, 'A-UT-03: no session cookie after login')
        session_key = cookie['value']
        s = SessionStore(session_key=session_key)
        data = s.load()
        self.assertIn('conectado_usuario', data)

        # Simulate timeout by deleting the session record from DB
        Session.objects.filter(session_key=session_key).delete()

        # Now perform an AJAX GET to a protected URL and expect 401
        # Use execute_async_script to await the fetch result and return status
        script = """
        var callback = arguments[arguments.length-1];
        fetch(arguments[0], {method: 'GET', headers: {'Accept':'application/json'}, credentials: 'same-origin'})
            .then(function(r){ callback(r.status); })
            .catch(function(e){ callback('error'); });
        """
        target = base + '/core/producto/update/1/'
        status = self.driver.execute_async_script(script, target)

        self._save('A-UT-03.png')
        self.assertTrue(status == 401 or status == 'error', f'A-UT-03: expected 401 after session deleted, got {status}')
