# -*- coding: utf-8 -*-
"""Abre ponencia_coffea_ia.pptx con el PowerPoint instalado en este equipo
(automatizacion COM via pywin32), exporta el PDF final y un PNG por
diapositiva a previews/ponencia/ para la verificacion visual en bucle.
No se commitea nada de previews/ (ignorado por git)."""
import os
import time
import win32com.client

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
PPTX = os.path.join(REPO, "entregables", "07_ponencia", "ponencia_coffea_ia.pptx")
PDF = os.path.join(REPO, "entregables", "07_ponencia", "ponencia_coffea_ia.pdf")
PREVIEWS = os.path.join(REPO, "previews", "ponencia")

os.makedirs(PREVIEWS, exist_ok=True)

powerpoint = win32com.client.Dispatch("PowerPoint.Application")
powerpoint.Visible = 1
deck = powerpoint.Presentations.Open(PPTX, WithWindow=False)

# 1) Exportar PDF (formato 32 = ppSaveAsPDF)
deck.SaveAs(PDF, 32)
print(f"PDF exportado: {PDF}")

# 2) Exportar cada diapositiva a PNG a resolucion alta (1920 ancho)
deck.Export(PREVIEWS, "PNG", 1920, 1080)
print(f"PNG exportados en: {PREVIEWS}")

deck.Close()
time.sleep(1)
powerpoint.Quit()
print("Listo.")
