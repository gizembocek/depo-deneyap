"""Tarayıcı testlerinin ortak ayarları: tüm test dosyaları aynı tarayıcıyı kullanır."""
import os

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        exe = os.getenv("PW_CHROMIUM") or ("/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None)
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        yield b
        b.close()
