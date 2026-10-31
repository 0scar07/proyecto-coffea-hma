# -*- coding: utf-8 -*-
"""Exporta hoja_orador.html a entregables/07_ponencia/hoja_del_orador.pdf
(una pagina) usando Playwright, sin ninguna dependencia de red."""
import os
from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
HTML = os.path.join(AQUI, "hoja_orador.html")
PDF = os.path.join(REPO, "entregables", "07_ponencia", "hoja_del_orador.pdf")

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file:///{HTML.replace(os.sep, '/')}")
    page.pdf(path=PDF, format="A4", print_background=True,
             margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    browser.close()

print(f"Guardado: {PDF}")
