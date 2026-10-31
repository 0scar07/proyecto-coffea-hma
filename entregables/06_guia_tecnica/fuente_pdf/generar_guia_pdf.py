# -*- coding: utf-8 -*-
"""
Genera entregables/06_guia_tecnica/guia_tecnica_usuario.pdf.

Uso (desde la raiz del repo, con el entorno ya instalado -- no crea nada nuevo):
    python entregables/06_guia_tecnica/fuente_pdf/generar_guia_pdf.py
Escribe el PDF final, y previsualizaciones PNG pagina por pagina en
entregables/06_guia_tecnica/fuente_pdf/previews/ (carpeta ignorada por git).

Todas las cifras se recalculan en vivo contra datos_reales_coffea_2023.xlsx llamando
directamente a las funciones de app/app.py (nunca se copian de memoria). Las capturas
usadas son las ya existentes en docs/screenshots/ y docs/figuras/ -- nunca se modifican,
solo se leen y se redimensionan a copias temporales para controlar el peso del PDF.
"""
import sys
import json
from pathlib import Path
from datetime import date

import pandas as pd
from PIL import Image

# ------------------------------------------------------------------------------------
# Rutas
# ------------------------------------------------------------------------------------
AQUI = Path(__file__).resolve().parent                      # .../06_guia_tecnica/fuente_pdf
GUIA_DIR = AQUI.parent                                       # .../06_guia_tecnica
REPO = AQUI.parents[2]                                       # raiz del repo
APP_DIR = REPO / "app"
DOCS_SCREENSHOTS = REPO / "docs" / "screenshots"
DOCS_FIGURAS = REPO / "docs" / "figuras"
# Dos capturas que no existian en docs/screenshots/ (Datos de prueba, Exportar reporte) se
# generaron con Playwright especificamente para esta guia y se guardan aqui -- no en
# docs/screenshots/, porque esa carpeta es compartida y esta tarea solo puede agregar
# contenido nuevo dentro de entregables/06_guia_tecnica/.
CAPTURAS_PROPIAS = AQUI / "capturas_propias"
XLSX = REPO / "datos_reales" / "datos_reales_coffea_2023.xlsx"
BUILD = AQUI / "_build"
PREVIEWS = AQUI / "previews"
IMG_BUILD = BUILD / "img"
PDF_SALIDA = GUIA_DIR / "guia_tecnica_usuario.pdf"
CSS_PATH = AQUI / "estilos.css"

for d in (BUILD, PREVIEWS, IMG_BUILD):
    d.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(APP_DIR))
import app as m  # noqa: E402  (modulo real de la app, para leer funciones y constantes reales)

FECHA_GENERACION = date.today().isoformat()
VERSION_GUIA = "1.0"


# ------------------------------------------------------------------------------------
# 1. Extraccion de datos reales (misma logica que entregables/06_guia_tecnica/*.md y
#    entregables/09-10_*, recalculada aqui en vivo para esta guia)
# ------------------------------------------------------------------------------------
def extraer_datos_reales():
    df = pd.read_excel(XLSX, sheet_name=0)
    df.columns = [c.strip().lower() for c in df.columns]
    datos = {v: {"-M": {}, "+M": {}} for v in sorted(df["variable"].unique())}
    for (variable, grupo, dia), g in df.groupby(["variable", "grupo", "dat"]):
        datos[variable][grupo][int(dia)] = g["valor"].to_numpy()

    RES = m.ajustar_todos_los_modelos(datos)
    modelos = list(m.MODELOS.keys())

    metricas = {}
    mejor_modelo = {}
    efecto = {}
    notas_k = {}
    for variable in datos:
        metricas[variable] = {}
        for grupo in ("-M", "+M"):
            metricas[variable][grupo] = {}
            for modelo in modelos:
                res = RES[variable][grupo][modelo]
                estado = m.estado_de_ajuste(res)
                if estado == m.ESTADO_OK:
                    metricas[variable][grupo][modelo] = {
                        "estado": "OK", "r2": float(res["r2"]), "rmse": float(res["rmse"]),
                        "mae": float(res.get("mae")),
                    }
                else:
                    metricas[variable][grupo][modelo] = {"estado": estado}
        _, mejores = m.calcular_tabla_modelo(RES, datos, variable, modelos)
        mejor_modelo[variable] = mejores
        filas = m.calcular_efecto_micorriza(datos, variable)
        efecto[variable] = [
            {"dia": int(f["dia"]), "media_control": float(f["media_control"]),
             "media_tratado": float(f["media_tratado"]), "incremento_pct": float(f["incremento_pct"]),
             "t": float(f["t"]), "p": float(f["p"]), "significativo": bool(f["significativo"])}
            for f in filas
        ]
        _, pie = m.fig_curvas_publicacion(datos, RES, variable, modelos, "real")
        notas_k[variable] = {"descripcion": pie["descripcion"], "notas": pie.get("notas") or []}

    return {"metricas": metricas, "mejor_modelo": mejor_modelo, "efecto": efecto, "notas_k": notas_k,
            "n_dias_por_modelo": {nombre: len(info["nombres_param"]) for nombre, info in m.MODELOS.items()}}


DATA = extraer_datos_reales()
with open(BUILD / "datos_guia.json", "w", encoding="utf-8") as f:
    json.dump(DATA, f, ensure_ascii=False, indent=2)

# Verificacion de nombres de seccion reales contra app.py (honestidad: no se inventan)
import re  # noqa: E402
codigo_app = (APP_DIR / "app.py").read_text(encoding="utf-8")
SECCIONES_REALES = re.findall(r'elif seccion == "([^"]+)"|^if seccion == "([^"]+)"', codigo_app, re.M)
SECCIONES_REALES = [a or b for a, b in SECCIONES_REALES]
SECCIONES_ESPERADAS = [
    "Resumen", "Ajustar modelos", "Metodología", "Resultados", "Gráficas de barras",
    "Resultados esperados", "Estadística", "Residuos", "Discusión y conclusiones",
    "Datos de prueba", "Exportar reporte",
]
assert SECCIONES_REALES == SECCIONES_ESPERADAS, (
    f"Las secciones de app.py cambiaron respecto a lo esperado por la guia: {SECCIONES_REALES}"
)
print("OK: 11 secciones de app.py verificadas contra el codigo:", SECCIONES_REALES)


# ------------------------------------------------------------------------------------
# 2. Preparacion de imagenes (copias redimensionadas, para controlar el peso del PDF;
#    los originales de docs/ nunca se tocan)
# ------------------------------------------------------------------------------------
def preparar_imagen(ruta_original: Path, max_ancho=1500, calidad=82) -> str:
    """Copia redimensionada+comprimida en _build/img/, devuelve un file:// URI absoluto."""
    destino = IMG_BUILD / (ruta_original.stem + ".jpg")
    with Image.open(ruta_original) as im:
        im = im.convert("RGB")
        if im.width > max_ancho:
            nueva_altura = int(im.height * (max_ancho / im.width))
            im = im.resize((max_ancho, nueva_altura), Image.LANCZOS)
        im.save(destino, "JPEG", quality=calidad, optimize=True)
    return destino.resolve().as_uri()


def img_screenshot(nombre_archivo: str) -> str:
    ruta = DOCS_SCREENSHOTS / nombre_archivo
    if not ruta.exists():
        raise FileNotFoundError(f"Captura no encontrada: {ruta}")
    return preparar_imagen(ruta)


def img_figura(nombre_archivo: str) -> str:
    ruta = DOCS_FIGURAS / nombre_archivo
    if not ruta.exists():
        raise FileNotFoundError(f"Figura no encontrada: {ruta}")
    return preparar_imagen(ruta)


def img_propia(nombre_archivo: str) -> str:
    """Capturas generadas para esta guia (no existian en docs/screenshots/): Datos de
    prueba y Exportar reporte. Ver CAPTURAS_PROPIAS mas arriba."""
    ruta = CAPTURAS_PROPIAS / nombre_archivo
    if not ruta.exists():
        raise FileNotFoundError(f"Captura propia no encontrada: {ruta}")
    return preparar_imagen(ruta)


print("Verificando que existan todas las capturas y figuras necesarias...")
NECESARIAS_SCREENSHOTS = [
    "resumen.png", "ajustar_modelos.png", "metodologia.png", "curvas.png", "tasas.png",
    "barras.png", "resultados_esperados.png", "estadistica.png", "residuos.png",
]
NECESARIAS_FIGURAS = ["curvas_area_foliar.png", "barras_r2_modelos.png"]
NECESARIAS_PROPIAS = ["datos_de_prueba.png", "exportar_reporte.png"]
faltantes = [n for n in NECESARIAS_SCREENSHOTS if not (DOCS_SCREENSHOTS / n).exists()]
faltantes += [n for n in NECESARIAS_FIGURAS if not (DOCS_FIGURAS / n).exists()]
faltantes += [n for n in NECESARIAS_PROPIAS if not (CAPTURAS_PROPIAS / n).exists()]
if faltantes:
    raise SystemExit(f"Faltan capturas/figuras necesarias: {faltantes}")
print("OK: todas las capturas y figuras necesarias existen.")


# ------------------------------------------------------------------------------------
# 3. Elementos visuales: bandas curvas e iconos de capitulo (vectoriales, propios)
# ------------------------------------------------------------------------------------
def banda_superior_svg():
    return """
    <svg viewBox="0 0 1000 100" preserveAspectRatio="none">
      <defs>
        <linearGradient id="gradSup" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#A8432B"/>
          <stop offset="1" stop-color="#B8791E"/>
        </linearGradient>
      </defs>
      <path d="M0,0 L1000,0 L1000,42 C 720,75 380,30 0,62 Z" fill="url(#gradSup)"/>
      <path d="M0,62 C 380,30 720,75 1000,42" fill="none" stroke="#FBEFE0" stroke-width="1.4" opacity="0.55"/>
    </svg>"""


def banda_inferior_svg():
    return """
    <svg viewBox="0 0 1000 100" preserveAspectRatio="none">
      <path d="M0,100 L1000,100 L1000,42 C 640,4 340,74 0,34 Z" fill="#201C18"/>
      <path d="M0,34 C 340,74 640,4 1000,42" fill="none" stroke="#A8432B" stroke-width="1.4" opacity="0.6"/>
    </svg>"""


def _icono_svg(interior: str) -> str:
    return f"""<svg width="100%" height="100%" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="46" fill="#A8432B14" stroke="#A8432B" stroke-width="2"/>
      {interior}
    </svg>"""


ICONOS = {
    "introduccion": _icono_svg(
        '<polygon points="50,24 62,58 50,50 38,58" fill="#A8432B"/>'
        '<circle cx="50" cy="50" r="26" fill="none" stroke="#A8432B" stroke-width="2.2"/>'
    ),
    "conceptos": _icono_svg(
        '<circle cx="42" cy="50" r="22" fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<circle cx="60" cy="50" r="22" fill="none" stroke="#B8791E" stroke-width="2.4"/>'
    ),
    "interfaz": _icono_svg(
        '<rect x="26" y="26" width="19" height="19" rx="2.5" fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<rect x="55" y="26" width="19" height="19" rx="2.5" fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<rect x="26" y="55" width="19" height="19" rx="2.5" fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<rect x="55" y="55" width="19" height="19" rx="2.5" fill="#A8432B"/>'
    ),
    "datos": _icono_svg(
        '<ellipse cx="50" cy="34" rx="22" ry="8" fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<path d="M28,34 L28,66 C28,70.5 38,74 50,74 C62,74 72,70.5 72,66 L72,34" '
        'fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<path d="M28,50 C28,54.5 38,58 50,58 C62,58 72,54.5 72,50" fill="none" stroke="#B8791E" stroke-width="2"/>'
    ),
    "recorrido": _icono_svg(
        '<circle cx="30" cy="34" r="3.4" fill="#A8432B"/><line x1="40" y1="34" x2="74" y2="34" stroke="#A8432B" stroke-width="3"/>'
        '<circle cx="30" cy="50" r="3.4" fill="#A8432B"/><line x1="40" y1="50" x2="68" y2="50" stroke="#A8432B" stroke-width="3"/>'
        '<circle cx="30" cy="66" r="3.4" fill="#A8432B"/><line x1="40" y1="66" x2="62" y2="66" stroke="#A8432B" stroke-width="3"/>'
    ),
    "interpretar": _icono_svg(
        '<line x1="26" y1="72" x2="76" y2="72" stroke="#A8432B" stroke-width="2.4"/>'
        '<rect x="32" y="52" width="10" height="20" fill="#A8432B"/>'
        '<rect x="47" y="40" width="10" height="32" fill="#B8791E"/>'
        '<rect x="62" y="28" width="10" height="44" fill="#A8432B"/>'
    ),
    "exportar": _icono_svg(
        '<path d="M34,24 L58,24 L68,34 L68,76 L34,76 Z" fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<path d="M58,24 L58,34 L68,34" fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<line x1="51" y1="46" x2="51" y2="64" stroke="#B8791E" stroke-width="2.6"/>'
        '<polyline points="43,58 51,66 59,58" fill="none" stroke="#B8791E" stroke-width="2.6"/>'
    ),
    "problemas": _icono_svg(
        '<text x="50" y="64" font-size="42" font-family="Georgia, serif" font-weight="700" '
        'fill="#A8432B" text-anchor="middle">?</text>'
    ),
    "practicas": _icono_svg(
        '<path d="M50,24 L72,32 L72,52 C72,66 62,74 50,78 C38,74 28,66 28,52 L28,32 Z" '
        'fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<polyline points="39,50 47,60 63,40" fill="none" stroke="#B8791E" stroke-width="3.2"/>'
    ),
    "anexos": _icono_svg(
        '<rect x="38" y="22" width="24" height="46" rx="12" fill="none" stroke="#A8432B" stroke-width="2.4"/>'
        '<line x1="50" y1="30" x2="50" y2="64" stroke="#A8432B" stroke-width="2.4"/>'
        '<circle cx="50" cy="70" r="6" fill="none" stroke="#B8791E" stroke-width="2.4"/>'
    ),
}


# ------------------------------------------------------------------------------------
# 4. Sistema de paginacion: se registran las paginas en orden y el numero se asigna
#    automaticamente al construir el documento (nunca se escribe un numero a mano).
# ------------------------------------------------------------------------------------
class Documento:
    def __init__(self):
        self.paginas = []          # lista de dicts {clave, numero, titulo_banda, html_fn}
        self.registro_numeros = {} # clave -> numero de pagina (se llena en construir())

    def pagina(self, clave, titulo_banda, html_fn, numerar=True, extra_class=None):
        if extra_class is None:
            # Inferido de la clave para no depender de que cada llamada lo recuerde:
            # portada y cualquier "..._divisor" llevan su clase de layout especial.
            extra_class = "portada" if clave == "portada" else ("divisor" if clave.endswith("_divisor") else "")
        self.paginas.append({"clave": clave, "titulo_banda": titulo_banda, "html_fn": html_fn,
                              "numerar": numerar, "extra_class": extra_class})

    def construir(self):
        n = 0
        for p in self.paginas:
            if p["numerar"]:
                n += 1
                self.registro_numeros[p["clave"]] = n
        piezas = []
        for p in self.paginas:
            numero = self.registro_numeros.get(p["clave"])
            contenido_html = p["html_fn"](self)
            piezas.append(envolver_pagina(contenido_html, p["titulo_banda"], numero, clave=p["clave"],
                                           extra_class=p["extra_class"]))
        return "\n".join(piezas)

    def num(self, clave):
        return self.registro_numeros[clave]


def envolver_pagina(contenido_html, titulo_banda, numero, clave, extra_class=""):
    """Las bandas curvas se dibujan SIEMPRE (incluida la portada); el texto de la banda
    superior y la insignia de numero son opcionales (la portada y los divisores de
    capitulo no llevan texto en la banda, igual que la referencia de diseno)."""
    texto_banda_html = f'<div class="banda-titulo"><span class="txt">{titulo_banda}</span></div>' if titulo_banda else ""
    insignia_html = f'<div class="insignia-pagina">{numero}</div>' if numero is not None else ""
    id_attr = f' id="{clave}"' if clave else ""
    return f"""
    <section class="pagina {extra_class}"{id_attr}>
      <div class="patron-puntos"></div>
      <div class="banda banda-superior">{banda_superior_svg()}</div>
      {texto_banda_html}
      <div class="banda banda-inferior">{banda_inferior_svg()}</div>
      {insignia_html}
      <div class="contenido">{contenido_html}</div>
    </section>
    """


# ------------------------------------------------------------------------------------
# 5. Componentes de contenido reutilizables
# ------------------------------------------------------------------------------------
ETIQUETAS_RECUADRO = {
    "nota": ("Nota", "recuadro-nota"),
    "importante": ("Importante", "recuadro-importante"),
    "consejo": ("Consejo", "recuadro-consejo"),
    "advertencia": ("Advertencia", "recuadro-advertencia"),
}


def recuadro(tipo, html_interior, titulo=None):
    etiqueta, clase = ETIQUETAS_RECUADRO[tipo]
    titulo = titulo or etiqueta
    return f"""<div class="recuadro {clase}"><div class="etiqueta">{titulo}</div>{html_interior}</div>"""


def figura(src_uri, pie, ancho_pct=100):
    return f"""<div class="figura-marco" style="width:{ancho_pct}%;">
      <img src="{src_uri}"/></div><div class="figura-pie">{pie}</div>"""


def captura_anotada(src_uri, pie, cajas=None, callouts=None):
    """cajas: lista de (x%, y%, w%, h%) para marcos rojos punteados.
    callouts: lista de (numero, x%, y%) para circulos numerados azules."""
    cajas = cajas or []
    callouts = callouts or []
    overlays = []
    for (x, y, w, h) in cajas:
        overlays.append(
            f'<div class="marco-rojo" style="left:{x}%;top:{y}%;width:{w}%;height:{h}%;"></div>'
        )
    for (num, x, y) in callouts:
        overlays.append(
            f'<div class="callout-numero" style="left:{x}%;top:{y}%;">{num}</div>'
        )
    return f"""<div class="figura-marco"><div class="captura-anotada">
      <img src="{src_uri}"/>{''.join(overlays)}
      </div></div><div class="figura-pie">{pie}</div>"""


def paso(numero, campo, explicacion):
    return f"""<div class="paso"><div class="num-circulo">{numero}</div>
      <div class="txt"><span class="campo">{campo}</span> {explicacion}</div></div>"""


def tabla(encabezados, filas):
    ths = "".join(f"<th>{h}</th>" for h in encabezados)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in fila) + "</tr>" for fila in filas)
    return f'<table class="tabla"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>'


def titulo_seccion(numero, texto):
    return f'<h2 class="titulo-seccion"><span class="cap">{texto[0]}</span>{texto[1:]}</h2>'


def ref_cruzada(doc, clave, texto):
    return f'<a href="#{clave}" class="ref-cruzada">{texto}, página {doc.num(clave)}</a>'


def fmt_r2(v):
    return f"{v:.4f}" if v is not None else "–"


def fila_metrica(variable, grupo, modelo):
    d = DATA["metricas"][variable][grupo][modelo]
    if d["estado"] == "OK":
        return [grupo, modelo, fmt_r2(d["r2"]), fmt_r2(d["rmse"]), fmt_r2(d["mae"])]
    return [grupo, modelo, f"<i>{d['estado']}</i>", "–", "–"]


AUTORES = "Richard Montez, Diego Barrios, Santiago Uribe, Oscar Llanos"
REPO_URL = "https://github.com/0scar07/proyecto-coffea-hma"

# ------------------------------------------------------------------------------------
# 6. Construccion del documento completo
# ------------------------------------------------------------------------------------
doc = Documento()


def pg_portada(d):
    return f"""
    <div class="kicker">Coffea IA · Documentación técnica</div>
    <h1>Guía técnica de usuario</h1>
    <div class="subt">Cómo usar la app de modelado de crecimiento de <i>Coffea arabica</i> con y sin micorrizas</div>
    <div class="meta-caja">
      <span><b>Versión</b> {VERSION_GUIA}</span>
      <span><b>Generada</b> {FECHA_GENERACION}</span>
      <span><b>Autores</b> {AUTORES}</span>
    </div>
    <p class="small muted" style="margin-top:6mm;">App desplegada: [URL de la app en Streamlit Cloud — pendiente de publicar en el README]</p>
    <div class="pie-emisor"><b>Coffea IA</b><br/>[Institución / Programa académico]</div>
    """


def pg_control(d):
    filas_version = [["1.0", FECHA_GENERACION, AUTORES, "Borrador para revisión", "[contacto pendiente]"]]
    leyenda = (
        recuadro("nota", "Aclara un concepto o remite a otra sección de la guía.")
        + recuadro("importante", "Señala una condición que cambia el resultado (por ejemplo, cuándo un modelo no se dibuja).")
        + recuadro("consejo", "Sugerencia práctica para aprovechar mejor una sección.")
        + recuadro("advertencia", "Alerta sobre un límite metodológico real de los datos o el ajuste.")
    )
    return f"""
    {titulo_seccion(0, "Control del documento y cómo usar esta guía")}
    <div class="dos-columnas">
      <div class="col">
        <h3 class="subtitulo">Control de versión</h3>
        {tabla(["Versión", "Fecha", "Autores", "Estado", "Contacto"], filas_version)}
        <h3 class="subtitulo" style="margin-top:4mm;">Cómo usar esta guía</h3>
        <p>Esta guía complementa (no reemplaza) al Markdown de referencia en
        <span class="ref-cruzada">entregables/06_guia_tecnica/guia_tecnica_usuario.md</span>. Está pensada para
        leerse por capítulos según el perfil (ver Capítulo I) o para consultarse puntualmente usando la
        Tabla de contenido y las referencias cruzadas.</p>
        <p>Todas las capturas provienen de <span class="ref-cruzada">docs/screenshots/</span> y
        <span class="ref-cruzada">docs/figuras/</span>; todas las cifras se recalcularon el {FECHA_GENERACION}
        contra <span class="ref-cruzada">datos_reales_coffea_2023.xlsx</span> llamando directamente a las
        funciones de <span class="ref-cruzada">app/app.py</span>.</p>
      </div>
      <div class="col">
        <h3 class="subtitulo">Leyenda de recuadros</h3>
        {leyenda}
      </div>
    </div>
    """


def pg_toc(d):
    grupos = [
        ("Frente", [("Control del documento y cómo usar esta guía", "control"), ("Tabla de contenido general", "toc")]),
        ("I. Introducción", [("Qué es Coffea IA, para quién y qué necesitas / ruta de 5 minutos", "cap1_contenido")]),
        ("II. Conceptos básicos", [("Glosario ilustrado (1/2)", "cap2_gloss1"), ("Glosario ilustrado (2/2)", "cap2_gloss2")]),
        ("III. Acceso y mapa de la interfaz", [("Mapa de la interfaz", "cap3_mapa")]),
        ("IV. Datos", [("Simulados frente a reales; formato del archivo", "cap4_formato"),
                        ("Plantilla, carga de datos propios, validaciones", "cap4_plantilla")]),
        ("V. Recorrido por las secciones", [
            ("Resumen", "cap5_resumen"), ("Ajustar modelos", "cap5_ajustar"), ("Metodología", "cap5_metodologia"),
            ("Resultados — curvas", "cap5_resultados1"), ("Resultados — tasas AGR/RGR", "cap5_resultados2"),
            ("Gráficas de barras", "cap5_barras"), ("Resultados esperados", "cap5_esperados"),
            ("Estadística", "cap5_estadistica"), ("Residuos", "cap5_residuos"),
            ("Discusión y conclusiones · Datos de prueba", "cap5_discusion_datos"),
            ("Exportar reporte (vista en la app)", "cap5_exportar_ui"),
        ]),
        ("VI. Cómo interpretar los resultados", [
            ("R², RMSE, MAE · No convergió frente a Sin días suficientes", "cap6_metricas"),
            ("Asíntota K · Leer un p-valor con réplicas sintéticas", "cap6_asintota_pvalor"),
        ]),
        ("VII. Exportar el reporte en PDF", [("Qué incluye, cómo generarlo y cómo leerlo", "cap7_contenido")]),
        ("VIII. Solución de problemas y preguntas frecuentes", [("Tabla de síntomas y causas", "cap8_tabla")]),
        ("IX. Buenas prácticas y limitaciones", [("Ventana de muestreo, réplicas sintéticas, validación externa", "cap9_contenido")]),
        ("Anexos", [
            ("A. Ejemplo mínimo de archivo de datos", "anexo_a"), ("B. Fórmulas de los tres modelos", "anexo_b"),
            ("C. Referencias · D. Control de cambios", "anexo_cd"), ("E. Tarjeta de referencia rápida", "anexo_e"),
        ]),
    ]
    columnas = ['<div class="toc">', '<div class="toc">']
    mitad = sum(len(g[1]) for g in grupos) / 2
    acumulado = 0
    col_actual = 0
    for titulo_grupo, items in grupos:
        bloque = f'<div class="grupo"><div class="grupo-titulo">{titulo_grupo}</div>'
        for texto, clave in items:
            bloque += (f'<a class="fila" href="#{clave}"><span class="txt">{texto}</span>'
                       f'<span class="num">{doc.num(clave)}</span></a>')
        bloque += "</div>"
        columnas[col_actual] += bloque
        acumulado += len(items)
        if acumulado >= mitad and col_actual == 0:
            col_actual = 1
    columnas[0] += "</div>"
    columnas[1] += "</div>"
    return f"""{titulo_seccion(0, "Tabla de contenido general")}
    <div class="dos-columnas">{columnas[0]}{columnas[1]}</div>"""


def pg_divisor(numero_romano, titulo, icono_key, subsecciones):
    def render(d):
        filas = "".join(
            f'<a class="fila" href="#{clave}"><span>{texto}</span><span class="num">{d.num(clave)}</span></a>'
            for texto, clave in subsecciones
        )
        clase_indice = "indice-capitulo compacto" if len(subsecciones) > 6 else "indice-capitulo"
        return f"""
        <div class="icono-capitulo">{ICONOS[icono_key]}</div>
        <div class="titulo-bloque">
          <span class="numero-romano">{numero_romano}</span>
          <span class="titulo-capitulo">{titulo}</span>
        </div>
        <div class="version-fecha">Guía técnica de usuario · Coffea IA — v{VERSION_GUIA} · {FECHA_GENERACION}</div>
        <div class="{clase_indice}">
          <div class="cabecera"><span>Contenido del capítulo</span><span>Página</span></div>
          {filas}
        </div>
        """
    return render


# ---- Capitulo I: Introduccion ----
def pg_cap1_contenido(d):
    return f"""{titulo_seccion(1, "Qué es Coffea IA")}
    <div class="dos-columnas">
      <div class="col">
        <p><b>Coffea IA</b> es una aplicación en Streamlit que ajusta y compara tres modelos matemáticos de
        crecimiento — Exponencial, Logístico y Gompertz — sobre datos de altura, área foliar, biomasa total,
        número de hojas y diámetro del tallo de <i>Coffea arabica</i>, comparando un grupo control sin inocular
        (<b>−M</b>) frente a un grupo inoculado con hongos micorrízicos arbusculares (<b>+M</b>).</p>
        <p>El ajuste es una <b>regresión no lineal por mínimos cuadrados</b> (<code>scipy.optimize.curve_fit</code>)
        sobre los tres modelos — no hay ningún componente de aprendizaje automático ni entrenamiento de modelos
        predictivos.</p>
        <h3 class="subtitulo">¿Para quién es esta guía?</h3>
        <p><b>Estudiante</b>: quiere cargar datos, ajustar modelos y entender qué significa cada resultado
        &rarr; Capítulos II, IV, V, VI.<br/>
        <b>Investigador</b>: quiere revisar el criterio estadístico y las limitaciones metodológicas &rarr;
        Capítulos VI, IX, Anexo B.<br/>
        <b>Docente</b>: quiere usarla como material de clase o evaluar entregables &rarr; Capítulos III, V,
        VII, y el material en <span class="ref-cruzada">entregables/03_taller_capacitacion/</span>.</p>
      </div>
      <div class="col">
        <h3 class="subtitulo">¿Qué necesitas?</h3>
        <p>Un navegador y, o bien la app ya desplegada, o un entorno local con Python 3.11 y las dependencias de
        <span class="ref-cruzada">app/requirements.txt</span> (ver el README principal del repositorio para el
        comando exacto de instalación y ejecución).</p>
        <h3 class="subtitulo">Empieza aquí — ruta de 5 minutos</h3>
        {paso(1, "Abre la app", "y observa la sección Resumen (arranca con datos simulados por defecto).")}
        {paso(2, "Ve a Ajustar modelos", "y presiona el botón — esto corre la regresión no lineal sobre los datos activos.")}
        {paso(3, "Ve a Resultados", "y observa las curvas por variable, con las réplicas observadas y las bandas de confianza.")}
        {paso(4, "Ve a Gráficas de barras", "para ver la comparación −M vs +M con significancia estadística.")}
        {paso(5, "Ve a Exportar reporte", "y genera el PDF con todo lo anterior en un solo documento.")}
        {recuadro("consejo", "Para repetir esta ruta con los datos reales del paper, ve primero a <b>Datos de prueba</b> y carga <code>datos_reales_coffea_2023.xlsx</code>.")}
      </div>
    </div>
    """


# ---- Capitulo II: Conceptos basicos (glosario) ----
GLOSARIO = [
    ("−M / +M", "Los dos grupos de comparación: −M es el control sin inocular, +M es el grupo inoculado con hongos micorrízicos arbusculares (HMA)."),
    ("ddt", "Días después del trasplante — la unidad de tiempo del eje X en todas las curvas (28, 56, 84 y 112 ddt en los datos reales)."),
    ("Curva de crecimiento", "La función matemática que describe cómo cambia una variable (altura, área foliar, etc.) en función del tiempo."),
    ("Exponencial", "Modelo de 2 parámetros, P(t) = P₀·e^(rt): crecimiento sin límite superior."),
    ("Logístico", "Modelo de 3 parámetros, P(t) = K/(1+e^(−k(t−Ti))): crecimiento sigmoide con asíntota K."),
    ("Gompertz", "Modelo de 3 parámetros, P(t) = K·e^(−e^(−k(t−Ti))): crecimiento sigmoide asimétrico, también con asíntota K."),
    ("R²", "Coeficiente de determinación: qué proporción de la variación observada explica el modelo (0 a 1, más cerca de 1 es mejor)."),
    ("RMSE", "Raíz del error cuadrático medio: el error típico del modelo, en las mismas unidades que la variable, penalizando más los errores grandes."),
    ("MAE", "Error absoluto medio: el error típico del modelo, en las mismas unidades que la variable, sin penalizar más los errores grandes."),
    ("Asíntota K", "El valor máximo teórico al que tiende la curva Logística o Gompertz. Solo se dibuja si pasa el criterio de plausibilidad (Capítulo VI)."),
    ("Convergencia", "Que el algoritmo de ajuste (curve_fit) haya encontrado una solución estable. Si no converge, la app no dibuja ese modelo ni reporta un R²."),
    ("Prueba t de Welch", "Prueba estadística para comparar las medias de −M y +M sin asumir que ambos grupos tienen la misma varianza (scipy.stats.ttest_ind, equal_var=False)."),
    ("Réplicas sintéticas", "En el dataset real, mediciones individuales generadas a partir de las medias y CV% publicados por Aguirre-Medina et al. (2023) — no son mediciones planta por planta."),
]


def pg_cap2_glosario(mitad):
    def render(d):
        items = "".join(
            f'<div class="glosario-item"><div class="glosario-term">{t}</div><div>{desc}</div></div>'
            for t, desc in mitad
        )
        n = len(mitad)
        col1 = items if n <= 4 else "".join(
            f'<div class="glosario-item"><div class="glosario-term">{t}</div><div>{desc}</div></div>'
            for t, desc in mitad[: (n + 1) // 2]
        )
        col2 = "" if n <= 4 else "".join(
            f'<div class="glosario-item"><div class="glosario-term">{t}</div><div>{desc}</div></div>'
            for t, desc in mitad[(n + 1) // 2:]
        )
        return f"""{titulo_seccion(2, "Glosario ilustrado")}
        <div class="dos-columnas"><div class="col">{col1}</div><div class="col">{col2}</div></div>"""
    return render


# ---- Capitulo III: Acceso y mapa de la interfaz ----
SIDEBAR_ITEMS = [
    ("Resumen", 24.0), ("Ajustar modelos", 33.5), ("Metodología", 42.7), ("Resultados", 47.5),
    ("Gráficas de barras", 52.4), ("Resultados esperados", 57.4), ("Estadística", 62.3),
    ("Residuos", 67.2), ("Discusión y conclusiones", 72.2), ("Datos de prueba", 81.4),
    ("Exportar reporte", 86.4),
]


def pg_cap3_mapa(d):
    cajas = [(5, y - 1.6, 15, 3.2) for _, y in SIDEBAR_ITEMS]
    callouts = [(i + 1, 19.5, y - 1.4) for i, (_, y) in enumerate(SIDEBAR_ITEMS)]
    lista_numerada = "".join(
        f'<div class="paso"><div class="num-circulo">{i+1}</div><div class="txt">{nombre}</div></div>'
        for i, (nombre, _) in enumerate(SIDEBAR_ITEMS)
    )
    return f"""{titulo_seccion(3, "Mapa de la interfaz")}
    <div class="dos-columnas">
      <div class="col">
        <p>Para acceder, abre la app (local o desplegada) — no requiere usuario ni contraseña.
        La barra lateral izquierda agrupa las 11 secciones de la navegación en cuatro bloques:
        Principal, Modelos, Análisis y Datos. Cada número de la captura corresponde al mismo
        número en esta lista.</p>
        {lista_numerada}
      </div>
      <div class="col">
        {captura_anotada(img_screenshot("curvas.png"),
            "Figura 3.1 — Barra lateral de Coffea IA con las 11 secciones numeradas.",
            cajas=cajas, callouts=callouts)}
      </div>
    </div>
    """


# ---- Capitulo IV: Datos ----
def pg_cap4_formato(d):
    return f"""{titulo_seccion(4, "Datos: simulados frente a reales, y formato del archivo")}
    <div class="dos-columnas">
      <div class="col">
        <p>La app arranca con <b>datos simulados</b> (con réplicas) para poder explorar todas las
        secciones sin depender de un archivo externo. Para trabajar con los datos reales del
        estudio de referencia, hay que cargarlos explícitamente en <b>Datos de prueba</b>.</p>
        {recuadro("advertencia", "Los dos modos usan la misma lógica de ajuste — la diferencia es solo el origen de los "
            "números, nunca el criterio de convergencia ni de plausibilidad de K.")}
        <h3 class="subtitulo">Formato exigido</h3>
        <p>La app acepta datos en <b>formato largo</b>, con estas columnas exactas (verificado contra
        <code>datos_reales_coffea_2023.xlsx</code>, hoja <code>datos</code>):</p>
        {tabla(["Columna", "Significado", "Ejemplo"], [
            ["<code>variable</code>", "Qué se midió", "altura, area_foliar, biomasa, hojas, diametro"],
            ["<code>grupo</code>", "Tratamiento", "-M (control) o +M (inoculado)"],
            ["<code>dat</code>", "Día después del trasplante", "28, 56, 84, 112"],
            ["<code>replica</code>", "Número de réplica", "1 a 5"],
            ["<code>valor</code>", "Valor medido", "9.0538"],
        ])}
      </div>
      <div class="col">
        <h3 class="subtitulo">Los datos reales incluidos</h3>
        <p>Altura, número de hojas, área foliar y biomasa total en 4 momentos de muestreo (28, 56, 84
        y 112 ddt), 5 réplicas por grupo y día, provienen de Aguirre-Medina et al. (2023) — ver
        Anexo C. El diámetro del tallo no está en ese estudio y sigue usando datos simulados.</p>
        {recuadro("importante",
            "Las réplicas individuales del archivo real son <b>sintéticas</b>: generadas para reproducir "
            "exactamente la media y el CV% publicados, no son mediciones planta por planta. "
            "Ver Capítulo VI para cómo esto afecta la lectura de los p-valores.")}
        <h3 class="subtitulo">Dos hojas en el Excel</h3>
        <p><code>datos</code> (las mediciones en el formato de la tabla) y <code>notas</code> (texto con
        la cita completa del estudio de origen).</p>
      </div>
    </div>
    """


def pg_cap4_plantilla(d):
    return f"""{titulo_seccion(4, "Plantilla, carga de datos propios y validaciones")}
    <div class="dos-columnas">
      <div class="col">
        <h3 class="subtitulo">Descargar la plantilla</h3>
        <p>En <b>Datos de prueba</b>, el botón <b>Descargar plantilla (Excel)</b> genera un archivo en
        blanco con las columnas correctas (función <code>generar_plantilla_excel()</code>), listo para
        completar con mediciones propias.</p>
        {paso(1, "Descarga la plantilla", "desde Datos de prueba.")}
        {paso(2, "Complétala", "respetando los nombres exactos de columna y los valores de grupo (-M/+M).")}
        {paso(3, "Súbela", "con el botón de carga de archivo en la misma sección.")}
        {paso(4, "Ve a Ajustar modelos", "y presiona el botón para correr el ajuste sobre tus datos.")}
      </div>
      <div class="col">
        <h3 class="subtitulo">Qué valida la app al cargar</h3>
        <p>La función <code>cargar_datos_desde_archivo</code> revisa que estén las columnas obligatorias
        antes de aceptar el archivo; si falta alguna, muestra el mensaje "Faltan columnas obligatorias"
        con el nombre exacto de la que falta, en vez de aceptar un archivo incompleto.</p>
        <p>Además, <code>advertir_dias_insuficientes</code> revisa, variable por variable, cuántos días
        distintos hay disponibles y anticipa qué modelos no van a poder ajustarse antes de que se presione
        "Ajustar modelos" (ver Capítulo VI para el umbral exacto por modelo).</p>
        {recuadro("consejo", "Si tu variable tiene menos de 3 días distintos de muestreo, Logístico y Gompertz "
            "no van a converger — esto no es un error de la app, es una limitación matemática del modelo "
            "(3 parámetros necesitan al menos 3 puntos distintos).")}
      </div>
    </div>
    """


# ---- Capitulo V: Recorrido por las secciones ----
def pagina_seccion(numero, nombre_seccion, para_que_sirve, que_veras, pasos, interpretar, img_html, ref_extra=""):
    def render(d):
        pasos_html = "".join(paso(i + 1, c, e) for i, (c, e) in enumerate(pasos))
        return f"""{titulo_seccion(5, nombre_seccion)}
        <div class="dos-columnas">
          <div class="col">
            <h3 class="subtitulo">Para qué sirve</h3><p>{para_que_sirve}</p>
            <h3 class="subtitulo">Qué verás</h3><p>{que_veras}</p>
            <h3 class="subtitulo">Paso a paso</h3>{pasos_html}
            <h3 class="subtitulo">Cómo interpretarlo</h3><p>{interpretar}</p>
            {ref_extra}
          </div>
          <div class="col">{img_html}</div>
        </div>"""
    return render


def pg_cap5_resumen(d):
    return pagina_seccion(
        5.1, "Resumen",
        "Da una vista rápida del estado general: qué fuente de datos está activa y si ya se corrió un ajuste.",
        "Un panel con el nombre de la fuente de datos activa (simulada o real) y, si ya se ajustó, un resumen "
        "del resultado más reciente.",
        [("Es la pantalla de entrada", "no requiere ninguna acción; solo confirma en qué estado está la app.")],
        "Si dice que no hay ajuste todavía, ve primero a Ajustar modelos.",
        figura(img_screenshot("resumen.png"), "Figura 5.1 — Sección Resumen."),
    )(d)


def pg_cap5_ajustar(d):
    return pagina_seccion(
        5.2, "Ajustar modelos",
        "Dispara la regresión no lineal (<code>curve_fit</code>) de los tres modelos sobre cada variable y grupo activos.",
        "Un botón \"Ajustar modelos\" y, tras presionarlo, badges de R² por variable y grupo apenas termina de calcular.",
        [("Revisa qué variables y modelos están activos", "antes de ajustar (se configuran en esta misma sección)."),
         ("Presiona \"Ajustar modelos\"", "la app corre curve_fit para cada variable × grupo × modelo."),
         ("Espera el mensaje", "\"Modelos ajustados sobre…\" confirma que terminó.")],
        "Un badge con R² alto indica buen ajuste en los puntos observados; un badge \"No convergió\" o \"Sin días "
        "suficientes\" significa que ese modelo no se pudo ajustar con los datos activos (ver Capítulo VI).",
        figura(img_screenshot("ajustar_modelos.png"), "Figura 5.2 — Resultado inmediato tras ajustar modelos."),
    )(d)


def pg_cap5_metodologia(d):
    return pagina_seccion(
        5.3, "Metodología",
        "Explica, con tratamiento editorial, la fórmula y el significado de cada uno de los tres modelos.",
        "Una tarjeta por modelo (Exponencial, Logístico, Gompertz) con su fórmula, sus parámetros y una nota sobre "
        "cuándo se espera que describa bien el crecimiento.",
        [("Léela antes de interpretar resultados", "si no conoces los tres modelos — no requiere ninguna acción en la app.")],
        "Es contenido de referencia, no un resultado calculado; para las fórmulas exactas del código, ver el Anexo B.",
        figura(img_screenshot("metodologia.png"), "Figura 5.3 — Sección Metodología."),
    )(d)


def pg_cap5_resultados1(d):
    return pagina_seccion(
        5.4, "Resultados — curvas ajustadas",
        "Muestra, variable por variable, las curvas de los modelos que convergieron junto con las réplicas "
        "observadas.",
        "Dos paneles por variable — (a) grupo −M y (b) grupo +M — con círculos de réplicas individuales, la línea "
        "de cada modelo convergido, su banda de confianza del 95%, y la asíntota K cuando es plausible.",
        [("Elige la variable", "con el selector en la parte superior de la sección."),
         ("Lee el pie de la figura", "indica qué modelos no se dibujan y por qué (no convergió, K implausible, etc.)."),
         ("Descarga el PNG", "con el botón bajo la figura, si lo necesitas para un informe.")],
        "Una banda de confianza angosta indica que el ajuste es preciso en esa zona; una asíntota K ausente no es "
        "un error, es la app aplicando el criterio de plausibilidad del Capítulo VI.",
        figura(img_figura("curvas_area_foliar.png"), "Figura 5.4 — Curvas de Área foliar (nota: Logístico y Gompertz no dibujan K aquí)."),
    )(d)


def pg_cap5_resultados2(d):
    return pagina_seccion(
        5.5, "Resultados — tasas de crecimiento (AGR/RGR)",
        "Dentro de un expander en Resultados: muestra la tasa de crecimiento absoluta (AGR) y relativa (RGR) del "
        "modelo con mejor R² en cada grupo.",
        "Dos paneles adicionales por variable, calculados analíticamente a partir de los parámetros ya ajustados "
        "(<code>calcular_agr_rgr</code>) — no se vuelve a ajustar ningún modelo para esto.",
        [("Abre el expander", "\"Tasas de crecimiento (AGR/RGR)\" debajo de las curvas."),
         ("Compara AGR entre grupos", "para ver en qué momento el crecimiento absoluto es más rápido."),
         ("Compara RGR entre grupos", "para ver el crecimiento proporcional al tamaño actual de la planta.")],
        "AGR alto pero RGR bajo es normal en una planta ya grande: crece mucho en términos absolutos pero poco "
        "en proporción a su tamaño.",
        figura(img_screenshot("tasas.png"), "Figura 5.5 — Paneles AGR/RGR de Altura."),
    )(d)


def pg_cap5_barras(d):
    return pagina_seccion(
        5.6, "Gráficas de barras",
        "Compara −M contra +M con barras de media ± desviación estándar por día, y compara R² entre los tres "
        "modelos.",
        "Barras agrupadas por día con marcas de significancia (ns/*/**/​***) sobre la prueba t de Welch, y una "
        "cuadrícula 2×2 de R² por modelo y variable.",
        [("Elige la variable", "en la parte superior."),
         ("Lee las marcas de significancia", "sobre cada par de barras (ns, *, **, ***)."),
         ("Revisa la cuadrícula de R²", "más abajo, para comparar los tres modelos en las 4 variables a la vez.")],
        "*** significa p&nbsp;&lt;&nbsp;0.001 (muy improbable que la diferencia sea azar); ns significa que no hay "
        "evidencia suficiente de diferencia con estos datos — no que no exista ningún efecto.",
        figura(img_screenshot("barras.png"), "Figura 5.6 — Barras de Biomasa total con significancia."),
    )(d)


def pg_cap5_esperados(d):
    return pagina_seccion(
        5.7, "Resultados esperados",
        "Genera automáticamente dos tablas: el mejor modelo por variable/grupo, y el efecto de la inoculación "
        "con la prueba t.",
        "\"Resultado esperado 1\" (mejor modelo, marcado con ★) y \"Resultado esperado 2\" (media −M, media +M, "
        "incremento %, t, p y significancia, por día).",
        [("No requiere configuración adicional", "se genera solo con el último ajuste ya calculado."),
         ("Revisa la columna \"Nota\"", "en la tabla 1 para ver por qué un modelo no aparece marcado.")],
        "Es la misma lógica que Gráficas de barras y Resultados, pero en formato de tabla — útil para copiar "
        "cifras exactas a un informe.",
        figura(img_screenshot("resultados_esperados.png"), "Figura 5.7 — Resultados esperados 1 y 2."),
    )(d)


def pg_cap5_estadistica(d):
    return pagina_seccion(
        5.8, "Estadística",
        "Muestra el detalle de la incertidumbre de cada parámetro y de la prueba t entre −M y +M.",
        "Intervalos de confianza por parámetro (calculados desde la matriz de covarianza de <code>curve_fit</code>) "
        "y el detalle completo de la prueba t de Welch.",
        [("Elige variable y modelo", "para ver el detalle de sus parámetros."),
         ("Revisa el ancho del intervalo de confianza", "un intervalo muy ancho indica un parámetro mal identificado "
          "con estos datos, aunque el R² general sea alto.")],
        "Un parámetro con intervalo de confianza que cruza cero o es desproporcionadamente ancho es la señal "
        "numérica detrás de una asíntota K que la app decide no dibujar (Capítulo VI).",
        figura(img_screenshot("estadistica.png"), "Figura 5.8 — Sección Estadística."),
    )(d)


def pg_cap5_residuos(d):
    return pagina_seccion(
        5.9, "Residuos",
        "Ofrece un diagnóstico visual de cada ajuste: si el error del modelo tiene un patrón sistemático.",
        "Gráficas de residuos (observado − predicho) por modelo y grupo.",
        [("Elige variable y modelo", "para ver sus residuos."),
         ("Busca patrones", "residuos dispersos alrededor de cero son buena señal; una curva o tendencia sistemática "
          "sugiere que el modelo no captura bien la forma real del crecimiento, aunque el R² sea aceptable.")],
        "Un R² alto con residuos claramente no aleatorios es una señal de alerta que la tabla de métricas por sí "
        "sola no muestra — por eso esta sección existe por separado.",
        figura(img_screenshot("residuos.png"), "Figura 5.9 — Sección Residuos."),
    )(d)


def pg_cap5_discusion_datos(d):
    return f"""{titulo_seccion(5, "Discusión y conclusiones · Datos de prueba")}
    <div class="dos-columnas">
      <div class="col">
        <h3 class="subtitulo">Discusión y conclusiones</h3>
        <p><b>Para qué sirve:</b> ofrece una lectura editorial de los resultados generales del último ajuste,
        redactada dinámicamente según la fuente de datos activa.</p>
        <p><b>Qué verás:</b> texto narrativo (no una tabla ni una figura) que resume qué tan bien ajustaron los
        modelos y qué patrón general se observa entre −M y +M.</p>
        <p><b>Cómo interpretarlo:</b> es una síntesis de lo que ya calcularon las demás secciones, útil como
        cierre de un informe — no introduce ningún cálculo nuevo.</p>
      </div>
      <div class="col">
        <h3 class="subtitulo">Datos de prueba</h3>
        <p><b>Para qué sirve:</b> elegir el origen de los datos: generar un nuevo lote simulado, descargar la
        plantilla, o cargar un Excel propio (o el real incluido en <code>datos_reales/</code>).</p>
        {paso(1, "Elige la fuente", "simulados (por defecto) o un archivo propio.")}
        {paso(2, "Con simulados", "puedes pedir un nuevo lote aleatorio.")}
        {paso(3, "Si subes un archivo", "se valida antes de aceptarlo (Capítulo IV).")}
        {figura(img_propia("datos_de_prueba.png"), "Figura 5.10 — Datos de prueba con datos reales cargados.", ancho_pct=78)}
      </div>
    </div>
    """


def pg_cap5_exportar_ui(d):
    return pagina_seccion(
        5.11, "Exportar reporte (vista en la app)",
        "Genera el documento PDF que reúne metodología, tablas y las mismas gráficas ya vistas en la app.",
        "Un botón \"Generar reporte PDF\" y, al terminar, un botón de descarga del archivo.",
        [("Asegúrate de haber ajustado modelos primero", "el reporte usa el último ajuste calculado."),
         ("Presiona \"Generar reporte PDF\"", "la generación tarda unos segundos porque exporta varias figuras."),
         ("Descarga el archivo", "con el botón que aparece al terminar.")],
        "El contenido y la lectura del reporte se detallan en el Capítulo VII.",
        figura(img_propia("exportar_reporte.png"), "Figura 5.11 — Sección Exportar reporte."),
    )(d)


# ---- Capitulo VI: Como interpretar los resultados ----
def pg_cap6_metricas(d):
    filas_altura = [fila_metrica("altura", g, mo) for g in ("-M", "+M") for mo in ("Exponencial", "Logístico", "Gompertz")]
    return f"""{titulo_seccion(6, "R², RMSE, MAE · “No convergió” frente a “Sin días suficientes”")}
    <div class="dos-columnas">
      <div class="col">
        <h3 class="subtitulo">Las tres métricas</h3>
        <p><b>R²</b> (0 a 1): qué proporción de la variación observada explica el modelo. <b>RMSE</b> y <b>MAE</b>:
        error típico en las mismas unidades que la variable; RMSE penaliza más los errores grandes que MAE.
        Sirven para comparar modelos <i>dentro de la misma variable</i> — no tiene sentido comparar el RMSE de
        altura (cm) contra el de biomasa (g).</p>
        <h3 class="subtitulo">Ejemplo real — Altura</h3>
        {tabla(["Grupo", "Modelo", "R²", "RMSE", "MAE"], filas_altura)}
        <p class="small muted">Recalculado el {FECHA_GENERACION} sobre datos_reales_coffea_2023.xlsx
        (sección Resultados / Estadística de la app).</p>
      </div>
      <div class="col">
        <h3 class="subtitulo">“Sin días suficientes”</h3>
        <p>El modelo necesita más días distintos de muestreo de los que hay disponibles para ese grupo/variable:
        Exponencial necesita ≥ 2 días; Logístico y Gompertz, ≥ 3 (por su número de parámetros). La app
        <b>no intenta el ajuste en absoluto</b>.</p>
        <h3 class="subtitulo">“No convergió”</h3>
        <p>El modelo sí tenía suficientes días, pero <code>curve_fit</code> no encontró una solución estable.
        Es más frecuente en Gompertz con solo 4 puntos por grupo — en los datos reales, Gompertz no converge en
        altura −M, área foliar +M y biomasa −M.</p>
        {recuadro("importante", "En ambos casos la app <b>no muestra un R² ni dibuja una curva</b> para ese modelo — "
            "es preferible mostrar la ausencia de resultado a inventar un ajuste poco confiable.")}
      </div>
    </div>
    """


def pg_cap6_asintota_pvalor(d):
    return f"""{titulo_seccion(6, "Asíntota K · Leer un p-valor con réplicas sintéticas")}
    <div class="dos-columnas">
      <div class="col">
        <h3 class="subtitulo">Cuándo se dibuja la asíntota K</h3>
        <p>La app solo dibuja la línea de K (y su banda de confianza) si se cumplen las <b>cuatro</b> condiciones
        a la vez (criterio vigente en <code>_asintota_k_plausible</code>):</p>
        {paso(1, "El modelo convergió.", "")}
        {paso(2, "R² ≥ 0.90.", "")}
        {paso(3, "K ≤ 1.5× el máximo observado", "en ese grupo y esa variable.")}
        {paso(4, "El punto de inflexión Ti", "cae dentro del rango de días efectivamente muestreados (28–112 ddt).")}
        <p>Ejemplo real: en Altura, Logístico (−M) estima K ≈ 790 679.8 cm frente a un máximo observado de
        15.0 cm — supera 1.5× el máximo por varios órdenes de magnitud, así que la app no la dibuja.
        Ver <span class="ref-cruzada">docs/figuras/curvas_altura.png</span> para la nota completa.</p>
      </div>
      <div class="col">
        <h3 class="subtitulo">Cómo leer un p-valor con réplicas sintéticas</h3>
        <p>La prueba t de Welch se calcula igual que en cualquier análisis (con <code>scipy.stats.ttest_ind</code>),
        pero en el dataset real las réplicas individuales son <b>sintéticas</b> — generadas para reproducir
        exactamente la media y el CV% publicados por Aguirre-Medina et al. (2023), no mediciones planta por
        planta.</p>
        {recuadro("advertencia",
            "Un p-valor bajo aquí confirma que la <i>diferencia entre las medias reportadas</i> es grande frente a "
            "la variabilidad reconstruida — pero no es evidencia estadística independiente nueva sobre el efecto "
            "de la micorrización, porque el tamaño de muestra efectivo es un artefacto de cómo se generaron los "
            "datos sintéticos, no observaciones originales.")}
        <p>Con datos propios (no sintéticos) cargados por el usuario, esta limitación no aplica: el cálculo es el
        mismo, pero la interpretación del p-valor es la estándar.</p>
      </div>
    </div>
    """


# ---- Capitulo VII: Exportar el reporte en PDF ----
def pg_cap7_contenido(d):
    return f"""{titulo_seccion(7, "Exportar el reporte en PDF")}
    <div class="dos-columnas">
      <div class="col">
        <h3 class="subtitulo">Qué incluye</h3>
        <p>El PDF que genera <b>Exportar reporte</b> reúne, en un solo documento: metodología de los tres modelos,
        tablas de R²/RMSE/MAE por variable y grupo, las curvas de crecimiento, la comparación de barras y R²,
        las tasas AGR/RGR, la tabla de efecto de la inoculación con la prueba t, y una sección de conclusiones y
        sugerencias generadas según la fuente de datos activa.</p>
        <h3 class="subtitulo">Cómo generarlo</h3>
        {paso(1, "Ajusta modelos primero", "en la sección Ajustar modelos.")}
        {paso(2, "Ve a Exportar reporte", "y presiona «Generar reporte PDF».")}
        {paso(3, "Descarga el archivo", "con el botón que aparece al terminar de generarse.")}
      </div>
      <div class="col">
        <h3 class="subtitulo">Cómo leerlo</h3>
        <p>El PDF sigue el mismo orden que la navegación de la app (Capítulo V), así que un lector que ya conoce
        la app puede ubicar cada sección directamente. Las figuras llevan el mismo pie de página que en pantalla
        — incluidas las notas de por qué un modelo no se dibuja.</p>
        {recuadro("nota", "Un PDF de ejemplo generado con datos reales está en "
            "<span class='ref-cruzada'>docs/reportes/reporte_ejemplo_datos_reales.pdf</span>.")}
        {recuadro("consejo", "Si generaste el reporte con datos simulados y quieres uno con los datos reales, ve a "
            "<b>Datos de prueba</b>, carga el Excel real, vuelve a <b>Ajustar modelos</b> y genera el reporte de nuevo.")}
      </div>
    </div>
    """


# ---- Capitulo VIII: Solucion de problemas y FAQ ----
FAQ_FILAS = [
    ["El archivo subido da error de columnas", "El Excel/CSV no usa exactamente <code>variable, grupo, dat, replica, valor</code>.",
     "Descarga la plantilla en Datos de prueba y compara los nombres de columna uno a uno."],
    ["Un modelo aparece como “Sin días suficientes”", "Esa variable/grupo tiene menos días distintos de muestreo de los "
     "que el modelo necesita (Exponencial ≥2, Logístico/Gompertz ≥3).",
     "No es un error: agrega más días de muestreo o acepta que ese modelo no aplica a esos datos."],
    ["Un modelo aparece como “No convergió”", "<code>curve_fit</code> no encontró una solución estable (frecuente en "
     "Gompertz con pocos puntos).", "No fuerces el ajuste; revisa Residuos y compara con los otros modelos que sí convergieron."],
    ["La asíntota K no se dibuja aunque el modelo convergió", "No cumple el criterio de plausibilidad (R²&lt;0.90, K&gt;1.5× el "
     "máximo observado, o Ti fuera del rango de días).", "Lee la nota en el pie de la figura: indica exactamente cuál condición falló."],
    ["Cambié los datos pero sigo viendo resultados anteriores", "No se volvió a presionar “Ajustar modelos” tras cambiar la "
     "fuente de datos.", "Ve a Ajustar modelos y corre el ajuste de nuevo — la app no reajusta sola al cambiar la fuente."],
    ["La app desplegada no refleja un cambio reciente del código", "Streamlit Cloud puede mantener una caché de "
     "<code>@st.cache_data</code> de una versión anterior.", "Usa “Reboot app” desde el menú de la app en Streamlit Cloud."],
    ["No encuentro mi variable tras subir el archivo", "El valor de la columna <code>variable</code> no coincide exactamente "
     "(mayúsculas, espacios, tildes).", "Revisa que el texto sea idéntico al de la plantilla descargable, carácter por carácter."],
]


def pg_cap8_tabla(d):
    return f"""{titulo_seccion(8, "Solución de problemas y preguntas frecuentes")}
    <div class="una-columna">
    <p>Problemas reales y reproducibles con la app, verificados contra el código y su comportamiento actual.</p>
    {tabla(["Síntoma", "Causa probable", "Qué hacer"], FAQ_FILAS)}
    </div>
    """


# ---- Capitulo IX: Buenas practicas y limitaciones ----
def pg_cap9_contenido(d):
    return f"""{titulo_seccion(9, "Buenas prácticas y limitaciones")}
    <div class="dos-columnas">
      <div class="col">
        <h3 class="subtitulo">Ventana de muestreo limitada</h3>
        <p>Con los 4 días disponibles (28–112 ddt) la planta está sobre todo en fase de crecimiento acelerado y
        todavía no muestra el “codo” de desaceleración que Logístico y Gompertz necesitan para estimar su
        asíntota K de forma confiable. Con solo 4 puntos por grupo (1 grado de libertad para un modelo de 3
        parámetros), Gompertz frecuentemente no converge en uno de los dos grupos. Esta es una limitación
        esperada del diseño de muestreo del estudio fuente, no un error de la aplicación.</p>
        <h3 class="subtitulo">Réplicas sintéticas</h3>
        <p>Las réplicas individuales del dataset real se generaron a partir de las medias y CV% publicados por
        Aguirre-Medina et al. (2023) — no son mediciones planta por planta. Cualquier prueba estadística sobre
        ellas ilustra la metodología, no aporta evidencia experimental nueva (ver Capítulo VI).</p>
      </div>
      <div class="col">
        <h3 class="subtitulo">Validación disponible — solo interna</h3>
        <p><code>scripts/validacion_cruzada_real.py</code> hace un hold-out 80/20 repetido 200 veces sobre las
        réplicas sintéticas, midiendo <b>qué tan estable es la media reportada</b> frente a qué réplicas caen en
        la muestra. Esto <b>no valida</b> que los modelos de crecimiento generalicen a datos nuevos.</p>
        {recuadro("advertencia", "No existe, todavía, ninguna validación externa de los modelos contra un dataset "
            "distinto al de Aguirre-Medina et al. (2023).")}
        <h3 class="subtitulo">Buenas prácticas recomendadas</h3>
        <p>Compara siempre R², RMSE, MAE <i>y</i> el gráfico de Residuos antes de elegir un modelo; no repitas un
        p-valor del dataset real como si fuera evidencia experimental nueva sin la nota metodológica; usa
        “ajuste de modelos” o “regresión no lineal”, nunca “entrenar/entrenamiento”, al describir lo que hace
        la app.</p>
      </div>
    </div>
    """


# ---- Anexos ----
def pg_anexo_a(d):
    filas = [["altura", "-M", "28", "1", "7.7094"], ["altura", "-M", "28", "2", "6.8835"],
             ["altura", "-M", "28", "3", "7.9832"], ["altura", "-M", "28", "4", "8.1000"],
             ["altura", "-M", "28", "5", "6.3239"]]
    return f"""{titulo_seccion(0, "Anexo A · Ejemplo mínimo de archivo de datos")}
    <div class="dos-columnas">
      <div class="col">
        <p>Extracto real de <code>datos_reales_coffea_2023.xlsx</code> (hoja <code>datos</code>), variable
        altura, grupo −M, día 28 — las 5 réplicas completas para esa combinación:</p>
        {tabla(["variable", "grupo", "dat", "replica", "valor"], filas)}
        <p class="small muted">Estos son los valores reales del archivo incluido en el repositorio, no un
        ejemplo inventado.</p>
      </div>
      <div class="col">
        {recuadro("nota", "Un archivo propio necesita exactamente estas 5 columnas, con estos nombres, en "
            "formato largo (una fila por réplica, no una columna por réplica). Ver Capítulo IV.")}
        {recuadro("consejo", "La forma más segura de tener el formato correcto es partir de la plantilla "
            "descargable en <b>Datos de prueba</b> y solo agregar filas.")}
      </div>
    </div>
    """


FORMULAS = [
    ("Exponencial", "P(t) = P₀ · e^(r·t)", "P₀, r", "modelo_exponencial(t, P0, r)"),
    ("Logístico", "P(t) = K / (1 + e^(−k·(t−Ti)))", "K, k, Ti", "modelo_logistico(t, K, k, Ti)"),
    ("Gompertz", "P(t) = K · e^(−e^(−k·(t−Ti)))", "K, k, Ti", "modelo_gompertz(t, K, k, Ti)"),
]


def pg_anexo_b(d):
    cajas = "".join(
        f"""<div class="formula-caja"><div class="nombre">{nombre}</div>
        <div class="expr">{expr}</div>
        <p class="small muted mb-0">Parámetros: {params} · código: <code>{codigo}</code></p></div>"""
        for nombre, expr, params, codigo in FORMULAS
    )
    return f"""{titulo_seccion(0, "Anexo B · Fórmulas de los tres modelos")}
    <div class="una-columna">
    <p>Parametrización exacta tal como está en <code>app/app.py</code> (copiada del código, no de memoria):</p>
    {cajas}
    <p>En los tres modelos, <code>t</code> es el día después del trasplante (ddt). En Logístico y Gompertz,
    <code>K</code> es la asíntota superior, <code>k</code> la tasa de crecimiento y <code>Ti</code> el punto de
    inflexión (el día en que la tasa de crecimiento es máxima). El ajuste de los tres modelos se hace con
    <code>scipy.optimize.curve_fit</code> — mínimos cuadrados no lineales, no aprendizaje automático.</p>
    </div>
    """


def pg_anexo_cd(d):
    return f"""{titulo_seccion(0, "Anexo C · Referencias  ·  Anexo D · Control de cambios")}
    <div class="dos-columnas">
      <div class="col">
        <h3 class="subtitulo">C. Referencias</h3>
        <p>Aguirre-Medina, J. F.; Aguirre-Cadena, J. F.; Escobar-España, J. C.; López-González, J. L. (2023).
        Crecimiento de <i>Coffea arabica</i> L. cv Catimor biofertilizado con diversos aislamientos de hongos
        endomicorrízicos en vivero. <i>Revista Fitotecnia Mexicana</i>, 46(3), 273-281.
        DOI: 10.35196/rfm.2023.3.273</p>
        <p class="small muted">Es la única fuente de datos externos usada en esta guía; no se citan otras
        referencias que no se hayan verificado directamente.</p>
      </div>
      <div class="col">
        <h3 class="subtitulo">D. Control de cambios</h3>
        {tabla(["Versión", "Fecha", "Cambios"], [
            ["1.0", FECHA_GENERACION, "Versión inicial de la guía técnica en PDF, generada a partir de "
             "entregables/06_guia_tecnica/guia_tecnica_usuario.md y verificada contra app/app.py."],
        ])}
      </div>
    </div>
    """


def pg_anexo_e(d):
    return f"""{titulo_seccion(0, "Anexo E · Tarjeta de referencia rápida")}
    <div class="dos-columnas">
      <div class="col">
        <div class="tarjeta"><h4>Modelos</h4><ul>
          <li>Exponencial: P₀·e^(rt) — 2 parámetros, ≥2 días.</li>
          <li>Logístico: K/(1+e^(−k(t−Ti))) — 3 parámetros, ≥3 días.</li>
          <li>Gompertz: K·e^(−e^(−k(t−Ti))) — 3 parámetros, ≥3 días.</li>
        </ul></div>
        <div class="tarjeta"><h4>Estados de ajuste</h4><ul>
          <li><b>OK</b>: convergió y tiene R² calculado.</li>
          <li><b>No convergió</b>: curve_fit no encontró solución estable.</li>
          <li><b>Sin días suficientes</b>: menos días distintos de los que el modelo necesita.</li>
        </ul></div>
      </div>
      <div class="col">
        <div class="tarjeta"><h4>Asíntota K se dibuja si</h4><ul>
          <li>Convergió, y</li><li>R² ≥ 0.90, y</li><li>K ≤ 1.5× el máximo observado, y</li>
          <li>Ti está dentro de los días muestreados.</li>
        </ul></div>
        <div class="tarjeta"><h4>Significancia (prueba t de Welch)</h4><ul>
          <li>ns = p ≥ 0.05 &nbsp;·&nbsp; * = p &lt; 0.05 &nbsp;·&nbsp; ** = p &lt; 0.01 &nbsp;·&nbsp; *** = p &lt; 0.001</li>
        </ul></div>
        <div class="tarjeta"><h4>Recordatorio metodológico</h4><ul>
          <li>Réplicas del dataset real: sintéticas (Aguirre-Medina et al., 2023).</li>
          <li>Validación externa: pendiente.</li>
        </ul></div>
      </div>
    </div>
    """


# ------------------------------------------------------------------------------------
# 7. Registro de paginas en orden (el numero se asigna al construir(), no a mano)
# ------------------------------------------------------------------------------------
doc.pagina("portada", None, pg_portada, numerar=False)
doc.pagina("control", "Control del documento", pg_control)
doc.pagina("toc", "Tabla de contenido", pg_toc)

doc.pagina("cap1_divisor", None, pg_divisor("I", "Introducción", "introduccion",
    [("Qué es Coffea IA · para quién y qué necesitas · ruta de 5 minutos", "cap1_contenido")]))
doc.pagina("cap1_contenido", "I · Introducción", pg_cap1_contenido)

doc.pagina("cap2_divisor", None, pg_divisor("II", "Conceptos básicos", "conceptos",
    [("Glosario ilustrado (1/2)", "cap2_gloss1"), ("Glosario ilustrado (2/2)", "cap2_gloss2")]))
doc.pagina("cap2_gloss1", "II · Conceptos básicos", pg_cap2_glosario(GLOSARIO[:7]))
doc.pagina("cap2_gloss2", "II · Conceptos básicos", pg_cap2_glosario(GLOSARIO[7:]))

doc.pagina("cap3_divisor", None, pg_divisor("III", "Acceso y mapa de la interfaz", "interfaz",
    [("Mapa de la interfaz", "cap3_mapa")]))
doc.pagina("cap3_mapa", "III · Acceso y mapa de la interfaz", pg_cap3_mapa)

doc.pagina("cap4_divisor", None, pg_divisor("IV", "Datos", "datos",
    [("Simulados frente a reales · formato del archivo", "cap4_formato"),
     ("Plantilla · carga de datos propios · validaciones", "cap4_plantilla")]))
doc.pagina("cap4_formato", "IV · Datos", pg_cap4_formato)
doc.pagina("cap4_plantilla", "IV · Datos", pg_cap4_plantilla)

doc.pagina("cap5_divisor", None, pg_divisor("V", "Recorrido por las secciones", "recorrido", [
    ("Resumen", "cap5_resumen"), ("Ajustar modelos", "cap5_ajustar"), ("Metodología", "cap5_metodologia"),
    ("Resultados — curvas", "cap5_resultados1"), ("Resultados — tasas AGR/RGR", "cap5_resultados2"),
    ("Gráficas de barras", "cap5_barras"), ("Resultados esperados", "cap5_esperados"),
    ("Estadística", "cap5_estadistica"), ("Residuos", "cap5_residuos"),
    ("Discusión y conclusiones · Datos de prueba", "cap5_discusion_datos"),
    ("Exportar reporte (vista en la app)", "cap5_exportar_ui"),
]))
doc.pagina("cap5_resumen", "V · Resumen", pg_cap5_resumen)
doc.pagina("cap5_ajustar", "V · Ajustar modelos", pg_cap5_ajustar)
doc.pagina("cap5_metodologia", "V · Metodología", pg_cap5_metodologia)
doc.pagina("cap5_resultados1", "V · Resultados", pg_cap5_resultados1)
doc.pagina("cap5_resultados2", "V · Resultados (AGR/RGR)", pg_cap5_resultados2)
doc.pagina("cap5_barras", "V · Gráficas de barras", pg_cap5_barras)
doc.pagina("cap5_esperados", "V · Resultados esperados", pg_cap5_esperados)
doc.pagina("cap5_estadistica", "V · Estadística", pg_cap5_estadistica)
doc.pagina("cap5_residuos", "V · Residuos", pg_cap5_residuos)
doc.pagina("cap5_discusion_datos", "V · Discusión · Datos de prueba", pg_cap5_discusion_datos)
doc.pagina("cap5_exportar_ui", "V · Exportar reporte", pg_cap5_exportar_ui)

doc.pagina("cap6_divisor", None, pg_divisor("VI", "Cómo interpretar los resultados", "interpretar", [
    ("R², RMSE, MAE · No convergió frente a Sin días suficientes", "cap6_metricas"),
    ("Asíntota K · Leer un p-valor con réplicas sintéticas", "cap6_asintota_pvalor"),
]))
doc.pagina("cap6_metricas", "VI · Interpretar resultados", pg_cap6_metricas)
doc.pagina("cap6_asintota_pvalor", "VI · Interpretar resultados", pg_cap6_asintota_pvalor)

doc.pagina("cap7_divisor", None, pg_divisor("VII", "Exportar el reporte en PDF", "exportar",
    [("Qué incluye, cómo generarlo y cómo leerlo", "cap7_contenido")]))
doc.pagina("cap7_contenido", "VII · Exportar el reporte en PDF", pg_cap7_contenido)

doc.pagina("cap8_divisor", None, pg_divisor("VIII", "Solución de problemas y preguntas frecuentes", "problemas",
    [("Tabla de síntomas, causas y soluciones", "cap8_tabla")]))
doc.pagina("cap8_tabla", "VIII · Solución de problemas", pg_cap8_tabla)

doc.pagina("cap9_divisor", None, pg_divisor("IX", "Buenas prácticas y limitaciones", "practicas",
    [("Ventana de muestreo, réplicas sintéticas, validación externa", "cap9_contenido")]))
doc.pagina("cap9_contenido", "IX · Buenas prácticas y limitaciones", pg_cap9_contenido)

doc.pagina("anexos_divisor", None, pg_divisor("", "Anexos", "anexos", [
    ("A. Ejemplo mínimo de archivo de datos", "anexo_a"), ("B. Fórmulas de los tres modelos", "anexo_b"),
    ("C. Referencias · D. Control de cambios", "anexo_cd"), ("E. Tarjeta de referencia rápida", "anexo_e"),
]))
doc.pagina("anexo_a", "Anexo A · Ejemplo de archivo", pg_anexo_a)
doc.pagina("anexo_b", "Anexo B · Fórmulas", pg_anexo_b)
doc.pagina("anexo_cd", "Anexo C-D · Referencias y control de cambios", pg_anexo_cd)
doc.pagina("anexo_e", "Anexo E · Tarjeta de referencia rápida", pg_anexo_e)


# ------------------------------------------------------------------------------------
# 8. Ensamblado de HTML, render a PDF con Playwright, y post-proceso (marcadores +
#    metadatos) con pymupdf.
# ------------------------------------------------------------------------------------
css_texto = CSS_PATH.read_text(encoding="utf-8")
html_paginas = doc.construir()
NUM_PAGINAS = len([p for p in doc.paginas if p["numerar"]]) + 1  # +1 por la portada sin numerar

html_completo = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"/>
<title>Guía técnica de usuario · Coffea IA</title>
<style>{css_texto}</style>
</head><body>
{html_paginas}
</body></html>"""

HTML_PATH = BUILD / "guia.html"
HTML_PATH.write_text(html_completo, encoding="utf-8")
print(f"HTML ensamblado: {HTML_PATH} ({len(html_completo)} caracteres, {len(doc.paginas)} páginas registradas)")

from playwright.sync_api import sync_playwright  # noqa: E402

PDF_SIN_METADATOS = BUILD / "guia_sin_metadatos.pdf"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(HTML_PATH.resolve().as_uri())
    page.wait_for_timeout(300)

    # Verificacion de desborde: ningun .pagina debe tener contenido mas alto que su caja.
    desbordes = page.evaluate("""
        () => Array.from(document.querySelectorAll('.pagina .contenido')).map((el, i) => {
            const cols = el.querySelectorAll('.col, .una-columna');
            let maxOverflow = 0;
            cols.forEach(c => { if (c.scrollHeight - c.clientHeight > maxOverflow) maxOverflow = c.scrollHeight - c.clientHeight; });
            return {indice: i, desbordePx: Math.round(maxOverflow)};
        }).filter(x => x.desbordePx > 3)
    """)
    if desbordes:
        print("ADVERTENCIA - paginas con posible desborde de contenido (px CSS):")
        for x in desbordes:
            print(" ", x)
    else:
        print("OK: ninguna pagina de contenido se desborda de su caja.")

    page.pdf(
        path=str(PDF_SIN_METADATOS),
        width="297mm", height="210mm",
        print_background=True, prefer_css_page_size=False, margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )
    browser.close()

print("PDF (sin marcadores/metadatos) generado:", PDF_SIN_METADATOS, PDF_SIN_METADATOS.stat().st_size, "bytes")

# ---- Post-proceso: marcadores (outline), metadatos, verificacion de fuentes ----
import fitz  # PyMuPDF, ya usado en otras partes de esta sesion  # noqa: E402

pdf = fitz.open(str(PDF_SIN_METADATOS))
assert pdf.page_count == NUM_PAGINAS, f"Se esperaban {NUM_PAGINAS} paginas, el PDF tiene {pdf.page_count}"

toc_outline = []
orden_capitulos = [
    (1, "Control del documento", "control"), (1, "Tabla de contenido", "toc"),
    (1, "I. Introducción", "cap1_divisor"), (2, "Qué es Coffea IA / ruta de 5 minutos", "cap1_contenido"),
    (1, "II. Conceptos básicos", "cap2_divisor"), (2, "Glosario (1/2)", "cap2_gloss1"), (2, "Glosario (2/2)", "cap2_gloss2"),
    (1, "III. Acceso y mapa de la interfaz", "cap3_divisor"), (2, "Mapa de la interfaz", "cap3_mapa"),
    (1, "IV. Datos", "cap4_divisor"), (2, "Simulados frente a reales", "cap4_formato"), (2, "Plantilla y validaciones", "cap4_plantilla"),
    (1, "V. Recorrido por las secciones", "cap5_divisor"),
    (2, "Resumen", "cap5_resumen"), (2, "Ajustar modelos", "cap5_ajustar"), (2, "Metodología", "cap5_metodologia"),
    (2, "Resultados — curvas", "cap5_resultados1"), (2, "Resultados — AGR/RGR", "cap5_resultados2"),
    (2, "Gráficas de barras", "cap5_barras"), (2, "Resultados esperados", "cap5_esperados"),
    (2, "Estadística", "cap5_estadistica"), (2, "Residuos", "cap5_residuos"),
    (2, "Discusión y Datos de prueba", "cap5_discusion_datos"), (2, "Exportar reporte (vista en la app)", "cap5_exportar_ui"),
    (1, "VI. Cómo interpretar los resultados", "cap6_divisor"),
    (2, "R², RMSE, MAE, convergencia", "cap6_metricas"), (2, "Asíntota K y p-valor", "cap6_asintota_pvalor"),
    (1, "VII. Exportar el reporte en PDF", "cap7_divisor"), (2, "Contenido y lectura", "cap7_contenido"),
    (1, "VIII. Solución de problemas y FAQ", "cap8_divisor"), (2, "Tabla de síntomas", "cap8_tabla"),
    (1, "IX. Buenas prácticas y limitaciones", "cap9_divisor"), (2, "Contenido", "cap9_contenido"),
    (1, "Anexos", "anexos_divisor"), (2, "A. Ejemplo de archivo", "anexo_a"), (2, "B. Fórmulas", "anexo_b"),
    (2, "C-D. Referencias y control de cambios", "anexo_cd"), (2, "E. Tarjeta de referencia rápida", "anexo_e"),
]
for nivel, titulo, clave in orden_capitulos:
    pagina_pdf = doc.num(clave)  # 1-indexado; pymupdf toc usa 1-indexado tambien
    toc_outline.append([nivel, titulo, pagina_pdf])
pdf.set_toc(toc_outline)

pdf.set_metadata({
    "title": "Guía técnica de usuario · Coffea IA",
    "author": AUTORES,
    "subject": "Guía de uso de la app Coffea IA (modelado de crecimiento de Coffea arabica con y sin micorrizas)",
    "keywords": "Coffea IA, Coffea arabica, micorrizas, curva de crecimiento, Streamlit",
    "creator": "entregables/06_guia_tecnica/fuente_pdf/generar_guia_pdf.py",
})
pdf.save(str(PDF_SALIDA), garbage=4, deflate=True)
pdf.close()
print("PDF final guardado:", PDF_SALIDA, PDF_SALIDA.stat().st_size, "bytes")

# ---- Verificacion de fuentes incrustadas ----
pdf2 = fitz.open(str(PDF_SALIDA))
fuentes_vistas = set()
for pno in range(pdf2.page_count):
    for f in pdf2.get_page_fonts(pno):
        # f = (xref, ext, type, basefont, name, encoding, ...)
        fuentes_vistas.add((f[3], f[1]))
no_incrustadas = [f for f in fuentes_vistas if f[1] == "n/a"]
print("Fuentes usadas en el PDF:", fuentes_vistas)
if no_incrustadas:
    print("ADVERTENCIA - fuentes posiblemente no incrustadas:", no_incrustadas)
else:
    print("OK: todas las fuentes reportadas por PyMuPDF tienen datos incrustados.")
pdf2.close()

# ---- Previsualizaciones PNG pagina por pagina (para revision visual; no se versionan) ----
pdf3 = fitz.open(str(PDF_SALIDA))
for i in range(pdf3.page_count):
    pix = pdf3[i].get_pixmap(dpi=150)
    pix.save(str(PREVIEWS / f"pagina_{i+1:02d}.png"))
pdf3.close()
print(f"OK: {pdf3.page_count if False else NUM_PAGINAS} previsualizaciones PNG en {PREVIEWS}")
print("LISTO.")
