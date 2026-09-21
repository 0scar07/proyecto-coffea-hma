# -*- coding: utf-8 -*-
"""Renderiza infografia.html (ancho fijo 1200px, alto natural) a:
  - infografia_coffea_ia.png (2x, en entregables/08_articulo_divulgativo/)
  - infografia_coffea_ia.pdf (una sola pagina, misma imagen)
Usa Playwright (ya en el proyecto) y Pillow, sin dependencias de red.
"""
import os
from playwright.sync_api import sync_playwright
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
HTML = os.path.join(AQUI, "infografia.html")
SALIDA_DIR = os.path.join(REPO, "entregables", "08_articulo_divulgativo")
PNG = os.path.join(SALIDA_DIR, "infografia_coffea_ia.png")
PDF = os.path.join(SALIDA_DIR, "infografia_coffea_ia.pdf")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 1000}, device_scale_factor=2)
    page.goto(f"file:///{HTML.replace(os.sep, '/')}")
    page.wait_for_timeout(150)
    altura = page.evaluate("document.body.scrollHeight")
    print(f"Alto real del documento: {altura}px")
    page.set_viewport_size({"width": 1200, "height": altura})
    page.screenshot(path=PNG, full_page=True)
    browser.close()

with Image.open(PNG) as im:
    print(f"PNG: {im.size[0]}x{im.size[1]} px")
    rgb = im.convert("RGB")
    rgb.save(PDF, "PDF", resolution=192.0)

print(f"Guardado: {PNG}")
print(f"Guardado: {PDF}")
