# -*- coding: utf-8 -*-
"""Convierte docs/validacion_externa/informe.md y resumen_exposicion.md a PDF con el
estilo visual de la app ("Cuaderno de campo"), reutilizando el mismo lenguaje visual que
entregables/06_guia_tecnica/fuente_pdf/ (portada, recuadros, tablas con encabezado de
color, pie de pagina numerado).

NO cambia ningun numero, tabla ni conclusion de los .md -- solo los convierte a HTML
estilizado. El indice de informe.pdf usa numeros de pagina reales: se genera una primera
pasada, se mide en que pagina cae cada seccion con PyMuPDF, y se regenera con esos
numeros ya puestos.

Uso: python docs/validacion_externa/fuente_pdf/generar_pdf.py
"""
import os
import re
import sys
import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright
import fitz  # PyMuPDF

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.dirname(AQUI)  # docs/validacion_externa/
REPO = os.path.abspath(os.path.join(OUT_DIR, "..", ".."))
BUILD = os.path.join(AQUI, "_build")
PREVIEWS = os.path.join(REPO, "previews", "validacion_externa", "pdf")
os.makedirs(BUILD, exist_ok=True)
os.makedirs(PREVIEWS, exist_ok=True)

CSS_PATH = os.path.join(AQUI, "estilos.css")
INFORME_MD = os.path.join(OUT_DIR, "informe.md")
RESUMEN_MD = os.path.join(OUT_DIR, "resumen_exposicion.md")

AUTORES = "Richard Montez, Diego Barrios, Santiago Uribe, Oscar Llanos"
REPO_URL = "https://github.com/0scar07/proyecto-coffea-hma"
VERSION = "1.0"
FECHA_GENERACION = datetime.date.today().isoformat()


# ==============================================================================
# 1. Parser de markdown a medida (solo los constructos que usan estos 2 archivos)
# ==============================================================================
def parsear_bloques(md_texto):
    lineas = md_texto.split("\n")
    bloques = []
    i, n = 0, len(lineas)
    while i < n:
        linea = lineas[i]
        if not linea.strip():
            i += 1
            continue
        if linea.startswith("# "):
            bloques.append(("titulo", linea[2:].strip()))
            i += 1
        elif linea.startswith("## "):
            bloques.append(("h2", linea[3:].strip()))
            i += 1
        elif linea.startswith("|"):
            tabla = [linea]
            i += 1
            while i < n and lineas[i].startswith("|"):
                tabla.append(lineas[i])
                i += 1
            bloques.append(("tabla", tabla))
        elif linea.startswith("- "):
            items, actual = [], linea[2:]
            i += 1
            while i < n and (lineas[i].startswith("  ") or lineas[i].startswith("- ")):
                if lineas[i].startswith("- "):
                    items.append(actual)
                    actual = lineas[i][2:]
                else:
                    actual += " " + lineas[i].strip()
                i += 1
            items.append(actual)
            bloques.append(("lista", items))
        else:
            parrafo = [linea]
            i += 1
            while i < n and lineas[i].strip() and not (
                lineas[i].startswith("#") or lineas[i].startswith("|") or lineas[i].startswith("- ")
            ):
                parrafo.append(lineas[i])
                i += 1
            texto = " ".join(l.strip() for l in parrafo)
            bloques.append(("parrafo", texto))
    return bloques


def inline(texto):
    texto = re.sub(r"`([^`]+)`", r"<code>\1</code>", texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
    texto = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", texto)
    return texto


PATRON_FIGURA = re.compile(r"^\*\*Figura\s+(\d+)\.\*\*\s*(.*)$", re.DOTALL)
PATRON_FIGURA_RUTA = re.compile(r"^(.*?)\s*—\s*`(figuras/[^`]+)`\s*$", re.DOTALL)


def tabla_a_html(lineas_tabla):
    filas = [l.strip().strip("|").split("|") for l in lineas_tabla]
    encabezado = [c.strip() for c in filas[0]]
    cuerpo = [[c.strip() for c in f] for f in filas[2:]]  # filas[1] es el separador ---
    html = ['<div class="tabla-envoltura"><table class="tabla">', "<thead><tr>"]
    html += [f"<th>{inline(c)}</th>" for c in encabezado]
    html.append("</tr></thead><tbody>")
    for fila in cuerpo:
        html.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in fila) + "</tr>")
    html.append("</tbody></table></div>")
    return "\n".join(html)


def bloques_a_html(bloques, recuadro_para=None):
    """recuadro_para: {titulo_h2: clase_recuadro} -- envuelve la lista que sigue a ese
    h2 en un <div class="recuadro ..."> en vez de una <ul> suelta."""
    recuadro_para = recuadro_para or {}
    html = []
    dentro_de_recuadro = None
    for tipo, contenido in bloques:
        if tipo == "titulo":
            continue  # el titulo (#) se usa solo en la portada, no en el cuerpo
        if tipo == "h2":
            if dentro_de_recuadro:
                html.append("</div>")
                dentro_de_recuadro = None
            slug = re.sub(r"[^a-z0-9]+", "-", contenido.lower()).strip("-")
            html.append(f'<h2 class="titulo-seccion" id="sec-{slug}">{inline(contenido)}</h2>')
            if contenido in recuadro_para:
                clase, etiqueta = recuadro_para[contenido]
                html.append(f'<div class="recuadro {clase}"><div class="etiqueta">{etiqueta}</div>')
                dentro_de_recuadro = clase
            continue
        if tipo == "tabla":
            html.append(tabla_a_html(contenido))
            continue
        if tipo == "lista":
            html.append("<ul>" + "".join(f"<li>{inline(it)}</li>" for it in contenido) + "</ul>")
            continue
        if tipo == "parrafo":
            m = PATRON_FIGURA.match(contenido)
            if m:
                numero, resto = m.group(1), m.group(2)
                m2 = PATRON_FIGURA_RUTA.match(resto)
                if m2:
                    caption, ruta = m2.group(1), m2.group(2)
                    html.append(
                        f'<figure class="figura-marco"><img src="../../{ruta}" alt="Figura {numero}">'
                        f'<figcaption><b>Figura {numero}.</b> {inline(caption)}</figcaption></figure>'
                    )
                    continue
            if contenido.startswith("*Lectura:") or contenido.startswith("*"):
                if contenido.startswith("*Lectura:") or "Lectura" in contenido[:12]:
                    html.append(f'<p class="frase-lectura">{inline(contenido)}</p>')
                    continue
            html.append(f"<p>{inline(contenido)}</p>")
    if dentro_de_recuadro:
        html.append("</div>")
    return "\n".join(html)


# ==============================================================================
# 2. Construccion de informe.pdf (portada + indice de 2 pasadas + cuerpo)
# ==============================================================================
def construir_portada():
    return f"""
    <section class="portada">
      <div class="kicker">Coffea IA · Informe técnico</div>
      <h1>Validación externa parcial</h1>
      <div class="subt">Comprobación de la metodología de Coffea IA (modelos de crecimiento y
        criterios de convergencia/plausibilidad) contra tres estudios ya publicados</div>
      <div class="marca-parcial">Validación parcial — no sustituye un experimento propio nuevo</div>
      <div class="meta-caja">
        <span><b>Versión</b> {VERSION}</span>
        <span><b>Generado</b> {FECHA_GENERACION}</span>
        <span><b>Autores</b> {AUTORES}</span>
        <span><b>App / repositorio</b> {REPO_URL}</span>
      </div>
      <div class="pie-emisor"><b>Coffea IA</b><br/>Programa de Ingeniería, Universidad Simón Bolívar</div>
    </section>
    """


def construir_indice(secciones_con_pagina):
    filas = []
    for titulo, pagina, nivel in secciones_con_pagina:
        clase = "fila nivel2" if nivel == 2 else "fila"
        num = pagina if pagina is not None else "—"
        filas.append(f'<div class="{clase}"><span class="txt">{inline(titulo)}</span><span class="num">{num}</span></div>')
    return f"""
    <div class="contenido-doc toc">
      <h2 class="titulo-seccion">Índice</h2>
      {''.join(filas)}
    </div>
    """


RECUADROS_INFORME = {
    "Qué SÍ se puede afirmar": ("recuadro-consejo", "✓ Qué SÍ se puede afirmar"),
    "Qué NO se puede afirmar": ("recuadro-importante", "✗ Qué NO se puede afirmar"),
}


def construir_cuerpo(bloques):
    return f'<div class="contenido-doc cuerpo">{bloques_a_html(bloques, RECUADROS_INFORME)}</div>'


def html_completo(css_texto, portada_html, indice_html, cuerpo_html, titulo_doc):
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>{titulo_doc}</title>
<style>{css_texto}</style>
</head><body>
{portada_html}
{indice_html}
<div style="page-break-before: always;"></div>
{cuerpo_html}
</body></html>"""


def render_pdf(html_texto, ruta_pdf, con_footer=True):
    ruta_html = os.path.join(BUILD, os.path.basename(ruta_pdf).replace(".pdf", ".html"))
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html_texto)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("file:///" + ruta_html.replace(os.sep, "/"))
        page.wait_for_timeout(200)
        # El margen inferior (12mm, reservado para el pie de pagina) se aplica SIEMPRE,
        # este visible o no el texto del pie: si cambiara entre pasadas, la paginacion
        # tambien cambiaria y los numeros de pagina medidos en la pasada 1 dejarian de
        # coincidir con la pasada 2 (asi se detecto el defecto real de texto encimado).
        footer_texto = """
            <div style="width:100%; font-family:'Segoe UI',Calibri,sans-serif; font-size:8pt;
                        color:#8A8277; padding:0 18mm; display:flex; justify-content:space-between;">
              <span>Coffea IA · Validación externa parcial</span>
              <span>Página <span class="pageNumber"></span> de <span class="totalPages"></span></span>
            </div>""" if con_footer else "<span></span>"
        kwargs = dict(path=ruta_pdf, print_background=True, prefer_css_page_size=True,
                      display_header_footer=True, header_template="<span></span>",
                      footer_template=footer_texto,
                      margin={"top": "0", "bottom": "12mm", "left": "0", "right": "0"})
        page.pdf(**kwargs)
        browser.close()
    return ruta_pdf


def paginas_de_secciones(ruta_pdf, titulos):
    """Busca en que pagina cae cada titulo de seccion, buscando SOLO despues de la
    pagina del indice (esa pagina repite todos los titulos como texto, asi que
    buscar desde el principio los encontraria ahi mismo en vez de en su ubicacion
    real)."""
    doc = fitz.open(ruta_pdf)
    pagina_indice = None
    for i in range(doc.page_count):
        if "Índice" in doc[i].get_text():
            pagina_indice = i
            break
    inicio = (pagina_indice + 1) if pagina_indice is not None else 0
    resultado = {}
    for titulo in titulos:
        encontrado = None
        for i in range(inicio, doc.page_count):
            if titulo in doc[i].get_text():
                encontrado = i + 1
                break
        resultado[titulo] = encontrado
    doc.close()
    return resultado


def generar_informe_pdf():
    with open(INFORME_MD, encoding="utf-8") as f:
        md_texto = f.read()
    with open(CSS_PATH, encoding="utf-8") as f:
        css_texto = f.read()
    bloques = parsear_bloques(md_texto)

    titulos_h2 = [t for tipo, t in bloques if tipo == "h2"]

    portada_html = construir_portada()
    cuerpo_html = construir_cuerpo(bloques)

    # --- Pasada 1: indice con placeholders, para medir en que pagina cae cada seccion ---
    indice_placeholder = construir_indice([(t, None, 1) for t in titulos_h2])
    html_pasada1 = html_completo(css_texto, portada_html, indice_placeholder, cuerpo_html,
                                  "Validación externa parcial — Coffea IA")
    pdf_pasada1 = os.path.join(BUILD, "informe_pasada1.pdf")
    render_pdf(html_pasada1, pdf_pasada1, con_footer=False)

    paginas = paginas_de_secciones(pdf_pasada1, titulos_h2)
    print("Páginas medidas (pasada 1):", paginas)

    # --- Pasada 2: indice con numeros reales ---
    indice_final = construir_indice([(t, paginas.get(t), 1) for t in titulos_h2])
    html_pasada2 = html_completo(css_texto, portada_html, indice_final, cuerpo_html,
                                  "Validación externa parcial — Coffea IA")
    pdf_sin_metadatos = os.path.join(BUILD, "informe_sin_metadatos.pdf")
    render_pdf(html_pasada2, pdf_sin_metadatos, con_footer=True)

    # --- Metadatos ---
    ruta_final = os.path.join(OUT_DIR, "informe.pdf")
    pdf = fitz.open(pdf_sin_metadatos)
    toc_outline = [[1, "Índice", 2]] + [[1, t, paginas.get(t) or 2] for t in titulos_h2]
    pdf.set_toc(toc_outline)
    pdf.set_metadata({
        "title": "Validación externa parcial — Coffea IA",
        "author": AUTORES,
        "subject": "Validación externa parcial de la metodología de Coffea IA contra estudios publicados",
        "keywords": "Coffea IA, validación externa, Coffea arabica, micorrizas, curva de crecimiento",
        "creator": "docs/validacion_externa/fuente_pdf/generar_pdf.py",
    })
    pdf.save(ruta_final, garbage=4, deflate=True)
    n_paginas = pdf.page_count
    pdf.close()
    print(f"informe.pdf generado: {ruta_final} ({os.path.getsize(ruta_final)} bytes, {n_paginas} páginas)")

    # --- Previews PNG ---
    pdf2 = fitz.open(ruta_final)
    for i in range(pdf2.page_count):
        pix = pdf2[i].get_pixmap(dpi=150)
        pix.save(os.path.join(PREVIEWS, f"informe_pagina_{i+1:02d}.png"))
    pdf2.close()
    return ruta_final, n_paginas


# ==============================================================================
# 3. Construccion de resumen_exposicion.pdf (una sola pagina)
# ==============================================================================
def generar_resumen_pdf():
    with open(RESUMEN_MD, encoding="utf-8") as f:
        md_texto = f.read()
    with open(CSS_PATH, encoding="utf-8") as f:
        css_texto = f.read()
    bloques = parsear_bloques(md_texto)

    titulo = next(t for tipo, t in bloques if tipo == "titulo")
    partes = []
    for tipo, contenido in bloques:
        if tipo == "titulo":
            continue
        elif tipo == "parrafo" and not partes:
            partes.append(f'<div class="intro">{inline(contenido)}</div>')
        elif tipo == "lista":
            partes.append("<ul>" + "".join(f"<li>{inline(it)}</li>" for it in contenido) + "</ul>")
        elif tipo == "tabla":
            partes.append(tabla_a_html(contenido))
        elif tipo == "parrafo" and contenido.startswith("Estado:"):
            partes.append(f'<div class="estado-final">{inline(contenido)}</div>')
        elif tipo == "parrafo":
            partes.append(f"<p>{inline(contenido)}</p>")

    html_pagina = f"""
    <section class="resumen-pagina">
      <div class="kicker">Coffea IA · Para la exposición</div>
      <h1>{inline(titulo)}</h1>
      {''.join(partes)}
    </section>
    """
    html_texto = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>Resumen — Validación externa parcial</title>
<style>{css_texto}</style>
</head><body>{html_pagina}</body></html>"""

    ruta_sin_metadatos = os.path.join(BUILD, "resumen_sin_metadatos.pdf")
    render_pdf(html_texto, ruta_sin_metadatos, con_footer=False)

    ruta_final = os.path.join(OUT_DIR, "resumen_exposicion.pdf")
    pdf = fitz.open(ruta_sin_metadatos)
    assert pdf.page_count == 1, f"El resumen debe medir 1 pagina, tiene {pdf.page_count}"
    pdf.set_metadata({
        "title": "Validación externa parcial — resumen para la exposición",
        "author": AUTORES,
        "subject": "Resumen de una pagina de la validacion externa parcial de Coffea IA",
        "keywords": "Coffea IA, validación externa, Coffea arabica, micorrizas",
        "creator": "docs/validacion_externa/fuente_pdf/generar_pdf.py",
    })
    pdf.save(ruta_final, garbage=4, deflate=True)
    pdf.close()
    print(f"resumen_exposicion.pdf generado: {ruta_final} ({os.path.getsize(ruta_final)} bytes, 1 página)")

    pdf2 = fitz.open(ruta_final)
    pix = pdf2[0].get_pixmap(dpi=150)
    pix.save(os.path.join(PREVIEWS, "resumen_pagina_01.png"))
    pdf2.close()
    return ruta_final


if __name__ == "__main__":
    generar_informe_pdf()
    generar_resumen_pdf()
    print("\nListo.")
