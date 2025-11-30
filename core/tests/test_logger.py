import os
import time
from datetime import datetime, timedelta
import atexit
import re

# Importar funciones del middleware para asociar métricas a tests
try:
    from core.middleware import set_current_test_id, pop_request_metrics
except Exception:
    # Fallbacks para no romper ejecución si algo cambia
    def set_current_test_id(_):
        pass
    def pop_request_metrics(_):
        return []

from django.test import TestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


RESULTS_FILE = os.path.join(os.path.dirname(__file__), 'test_results.txt')


def _ensure_results_file():
    # ensure file exists
    if not os.path.exists(RESULTS_FILE):
        try:
            open(RESULTS_FILE, 'a', encoding='utf-8').close()
        except Exception:
            pass


def _label_from_test_name(name: str) -> str:
    lower = name.lower()
    m = re.search(r'(p_ut|s_ut|v_ut|h_ut|a_ut)[^0-9]*(\d{2})', lower)
    if m:
        prefix = m.group(1).upper().replace('_', '-')
        num = m.group(2)
        return f"{prefix}-{num}"
    # fallback: use last part of test id (method name)
    if '.' in name:
        last = name.split('.')[-1]
    else:
        last = name
    return last


def append_test_result(test_name: str, status: str, duration: float):
    _ensure_results_file()
    # Grouped logging: write a single 'Inicio' marker at the start of the run,
    # then append each test line. On process exit an atexit handler will write
    # the final 'Fin. Duración total: X.XXXs' line with the accumulated duration.
    global _block_open, _block_total
    end_dt = datetime.now()
    end_ts = end_dt.strftime('%Y-%m-%d %H:%M:%S')
    label = _label_from_test_name(test_name)
    line = f"{end_ts} | {label} | Resultado: {status} | {duration:.3f}s"
    try:
        with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
            if not _block_open:
                f.write("Inicio\n")
                _block_open = True
            f.write(line + "\n")
            _block_total += float(duration)
    except Exception:
        pass


# atexit handler: close block and write total duration
_block_open = False
_block_total = 0.0

def _write_block_footer():
    global _block_open, _block_total
    try:
        if _block_open:
            with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"Fin. Duración total: {_block_total:.3f}s\n")
    except Exception:
        pass

atexit.register(_write_block_footer)


class LoggedTestCase(TestCase):
    def setUp(self):
        self._start_time = time.time()
        set_current_test_id(self.id())
        super().setUp()

    def tearDown(self):
        # determine outcome: OK if no errors in _outcome
        duration = max(0.0, time.time() - getattr(self, '_start_time', time.time()))
        status = 'OK'
        outcome = getattr(self, '_outcome', None)
        try:
            if outcome:
                # _outcome.errors is a list of (test, exc_info) tuples
                for test, exc_info in getattr(outcome, 'errors', outcome.errors if hasattr(outcome, 'errors') else []):
                    if exc_info:
                        status = 'FAIL'
                        break
        except Exception:
            # fallback: treat as OK
            status = 'OK'

        try:
            append_test_result(self.id(), status, duration)
            # Añadir líneas de métricas de requests asociadas al test
            metrics = pop_request_metrics(self.id())
            if metrics:
                try:
                    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
                        for m in metrics:
                            f.write(
                                f"REQ | {m['method']} {m['path']} | {m['status']} | latency_ms={m['latency_ms']:.2f} | "
                                f"rss_diff={m['rss_diff']} | user_cpu_s={m['user_cpu_s']:.3f} | system_cpu_s={m['system_cpu_s']:.3f}\n"
                            )
                except Exception:
                    pass
        finally:
            set_current_test_id(None)
            super().tearDown()


class LoggedLiveServerTestCase(StaticLiveServerTestCase):
    def setUp(self):
        self._start_time = time.time()
        set_current_test_id(self.id())
        super().setUp()

    def tearDown(self):
        duration = max(0.0, time.time() - getattr(self, '_start_time', time.time()))
        status = 'OK'
        outcome = getattr(self, '_outcome', None)
        try:
            if outcome:
                for test, exc_info in getattr(outcome, 'errors', outcome.errors if hasattr(outcome, 'errors') else []):
                    if exc_info:
                        status = 'FAIL'
                        break
        except Exception:
            status = 'OK'

        try:
            append_test_result(self.id(), status, duration)
            metrics = pop_request_metrics(self.id())
            if metrics:
                try:
                    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
                        for m in metrics:
                            f.write(
                                f"REQ | {m['method']} {m['path']} | {m['status']} | latency_ms={m['latency_ms']:.2f} | "
                                f"rss_diff={m['rss_diff']} | user_cpu_s={m['user_cpu_s']:.3f} | system_cpu_s={m['system_cpu_s']:.3f}\n"
                            )
                except Exception:
                    pass
        finally:
            set_current_test_id(None)
            super().tearDown()
