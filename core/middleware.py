import time
import os
import logging

# Almacén global para asociar métricas a un test en ejecución
CURRENT_TEST_ID = None
RECORDED_METRICS = []  # cada item: dict con test_id y datos de la request

def set_current_test_id(test_id: str | None):
    global CURRENT_TEST_ID
    CURRENT_TEST_ID = test_id

def pop_request_metrics(test_id: str):
    """Extrae las métricas registradas para un test y las elimina del buffer."""
    global RECORDED_METRICS
    extracted = [m for m in RECORDED_METRICS if m.get('test_id') == test_id]
    RECORDED_METRICS = [m for m in RECORDED_METRICS if m.get('test_id') != test_id]
    return extracted

try:
    import psutil  # type: ignore
except Exception:  # Fallback: crear shim mínimo para que el middleware no falle
    class _Proc:
        def memory_info(self):
            class M:
                rss = 0
            return M()
        def cpu_times(self):
            class C:
                user = 0.0
                system = 0.0
            return C()

    class _PsutilShim:
        @staticmethod
        def Process(pid):  # pid ignorado en shim
            return _Proc()

    psutil = _PsutilShim()


class RequestMetricsMiddleware:
    """Middleware que registra latencia y uso de recursos por request.

    Loggea en el logger 'request_metrics' una línea por petición con:
    METHOD PATH | status | latency_ms | rss_before | rss_after | rss_diff | user_cpu_s | system_cpu_s
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.process = psutil.Process(os.getpid()) if hasattr(psutil, 'Process') else None
        self.logger = logging.getLogger('request_metrics')

    def __call__(self, request):
        start = time.perf_counter()
        rss_before = 0
        user_before = 0.0
        system_before = 0.0
        if self.process:
            try:
                rss_before = self.process.memory_info().rss
                cpu_before = self.process.cpu_times()
                user_before = getattr(cpu_before, 'user', 0.0)
                system_before = getattr(cpu_before, 'system', 0.0)
            except Exception:
                pass

        response = self.get_response(request)

        duration_ms = (time.perf_counter() - start) * 1000.0
        rss_after = rss_before
        user_cpu = 0.0
        system_cpu = 0.0
        if self.process:
            try:
                rss_after = self.process.memory_info().rss
                cpu_after = self.process.cpu_times()
                user_cpu = getattr(cpu_after, 'user', 0.0) - user_before
                system_cpu = getattr(cpu_after, 'system', 0.0) - system_before
            except Exception:
                pass

        rss_diff = rss_after - rss_before
        # Formato compacto para fácil parsing posterior
        # Filtrar favicon para evitar ruido en métricas
        if request.path != '/favicon.ico':
            log_line = (
                f"{request.method} {request.path} | {getattr(response, 'status_code', 'NA')} | "
                f"latency_ms={duration_ms:.2f} | rss_before={rss_before} | rss_after={rss_after} | rss_diff={rss_diff} | "
                f"user_cpu_s={user_cpu:.3f} | system_cpu_s={system_cpu:.3f}"
            )
            self.logger.info(log_line)

            # Registrar para integración con test_results.txt si hay test activo
            if CURRENT_TEST_ID:
                RECORDED_METRICS.append({
                    'test_id': CURRENT_TEST_ID,
                    'method': request.method,
                    'path': request.path,
                    'status': getattr(response, 'status_code', 'NA'),
                    'latency_ms': duration_ms,
                    'rss_before': rss_before,
                    'rss_after': rss_after,
                    'rss_diff': rss_diff,
                    'user_cpu_s': user_cpu,
                    'system_cpu_s': system_cpu,
                })
        return response
