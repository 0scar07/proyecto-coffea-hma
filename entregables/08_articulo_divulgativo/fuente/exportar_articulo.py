# -*- coding: utf-8 -*-
"""Exporta articulo.html a entregables/08_articulo_divulgativo/articulo_divulgativo.pdf
en A4, usando los estilos @page ya definidos en el HTML (por eso no se pasa
'format' aqui: Playwright respeta el tamano de @page del documento)."""
import os
from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
HTML = os.path.join(AQUI, "articulo.html")
PDF = os.path.join(REPO, "entregables", "08_articulo_divulgativo", "articulo_divulgativo.pdf")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file:///{HTML.replace(os.sep, '/')}")
    page.pdf(path=PDF, print_background=True, prefer_css_page_size=True)
    browser.close()

print(f"Guardado: {PDF}")
