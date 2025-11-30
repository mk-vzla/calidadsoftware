from core.tests.test_logger import LoggedTestCase


class MetricsSmokeTest(LoggedTestCase):
    def test_metrics_smoke(self):
        # Realiza una petición simple para generar métricas en middleware
        resp = self.client.get('/')
        self.assertIn(resp.status_code, (200, 302, 404))