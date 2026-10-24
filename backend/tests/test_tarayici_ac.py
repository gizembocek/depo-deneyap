"""tarayici_ac.py: tarayıcı, sunucu yanıt vermeye başlayınca açılmalı."""
import http.server
import socket
import threading
import time

import tarayici_ac


def _bos_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_sunucu_gec_acilsa_da_hazir_olunca_tarayici_acilir():
    port = _bos_port()

    class Saglik(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path == "/api/health" else 404)
            self.end_headers()

        def log_message(self, *a):
            pass

    sunucu = {}

    def gec_baslat():  # SQL Server'a bağlanırken olduğu gibi sunucu 1.5 sn sonra açılır
        time.sleep(1.5)
        sunucu["s"] = http.server.HTTPServer(("127.0.0.1", port), Saglik)
        sunucu["s"].serve_forever()

    threading.Thread(target=gec_baslat, daemon=True).start()
    acilan = []
    baslangic = time.monotonic()
    try:
        assert tarayici_ac.bekle_ve_ac(f"http://localhost:{port}", en_fazla=20, aralik=0.2, ac=acilan.append)
    finally:
        if "s" in sunucu:
            sunucu["s"].shutdown()
    assert acilan == [f"http://localhost:{port}"]
    assert time.monotonic() - baslangic >= 1.4  # sunucu açılmadan tarayıcı açılmadı


def test_sunucu_hic_acilmazsa_tarayici_acilmaz():
    acilan = []
    assert not tarayici_ac.bekle_ve_ac(f"http://localhost:{_bos_port()}", en_fazla=1, aralik=0.2, ac=acilan.append)
    assert acilan == []
