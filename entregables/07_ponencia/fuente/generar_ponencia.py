# -*- coding: utf-8 -*-
"""Genera entregables/07_ponencia/ponencia_coffea_ia.pptx a partir de
entregables/07_ponencia/guion_ponencia.md y de las figuras/capturas reales en
docs/figuras/ y docs/screenshots/. Ninguna cifra se inventa aqui: las que
aparecen en las diapositivas ya fueron verificadas contra la salida real de
ajustar_todos_los_modelos/calcular_tabla_modelo/calcular_efecto_micorriza
sobre datos_reales_coffea_2023.xlsx (ver informe entregado aparte).

No modifica nada dentro de app/ ni datos_reales/; solo lee figuras/capturas
existentes y escribe el .pptx final en entregables/07_ponencia/.
"""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
FIGURAS = os.path.join(REPO, "docs", "figuras")
SHOTS = os.path.join(REPO, "docs", "screenshots")
SALIDA = os.path.join(REPO, "entregables", "07_ponencia", "ponencia_coffea_ia.pptx")

# ---------------------------------------------------------------------------
# Paleta real: entregables/../app/.streamlit/config.toml ("Cuaderno de campo")
# ---------------------------------------------------------------------------
CREMA = RGBColor(0xF1, 0xEC, 0xE3)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
TINTA = RGBColor(0x20, 0x1C, 0x18)
TERRACOTA = RGBColor(0xA8, 0x43, 0x2B)
BORDE = RGBColor(0xE4, 0xDF, 0xD6)
TERRACOTA_SUAVE = RGBColor(0xC9, 0x7A, 0x66)  # solo para acentos menores, derivado del mismo hue

F_TITULO = "Georgia"
F_CUERPO = "Calibri"

ANCHO, ALTO = Inches(13.333), Inches(7.5)
MARGEN_X = Inches(0.6)


def in_(v):
    return Inches(v)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def set_alt_text(shape, texto):
    el = shape._element
    for tag in ("nvSpPr", "nvPicPr", "nvGrpSpPr"):
        nv = getattr(el, tag, None)
        if nv is not None:
            nv.cNvPr.set("descr", texto)
            return


def fondo(slide, color):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def caja_texto(slide, left, top, width, height, texto, *, fuente=F_CUERPO, tam=18,
               color=TINTA, negrita=False, alineacion=PP_ALIGN.LEFT, interlineado=1.15,
               anchor=MSO_ANCHOR.TOP, ajustar=True):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    if ajustar:
        tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = alineacion
    p.line_spacing = interlineado
    r = p.add_run()
    r.text = texto
    r.font.name = fuente
    r.font.size = Pt(tam)
    r.font.color.rgb = color
    r.font.bold = negrita
    return tb


def viñetas(slide, left, top, width, height, items, *, tam=19, color=TINTA,
            espacio_antes=10, marca="—"):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.18
        p.space_before = Pt(espacio_antes if i else 0)
        r = p.add_run()
        r.text = f"{marca}  {item}"
        r.font.name = F_CUERPO
        r.font.size = Pt(tam)
        r.font.color.rgb = color
    return tb


def titulo_slide(slide, texto, *, color=TINTA, tam=32, top=0.55, subrayado=True):
    caja_texto(slide, MARGEN_X, in_(top), ANCHO - 2 * MARGEN_X, in_(1.05), texto,
               fuente=F_TITULO, tam=tam, color=color, negrita=True)
    if subrayado:
        linea = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, MARGEN_X, in_(top + 0.85),
                                        in_(0.9), Pt(3.2))
        linea.fill.solid()
        linea.fill.fore_color.rgb = TERRACOTA if color != CREMA else CREMA
        linea.line.fill.background()
        linea.shadow.inherit = False


def pie_pagina(slide, numero, total, *, sobre_terracota=False):
    color = CREMA if sobre_terracota else RGBColor(0x8A, 0x82, 0x77)
    caja_texto(slide, MARGEN_X, ALTO - in_(0.42), in_(3), in_(0.3), "Coffea IA",
               fuente=F_CUERPO, tam=12, color=color)
    caja_texto(slide, ANCHO - MARGEN_X - in_(1.2), ALTO - in_(0.42), in_(1.2), in_(0.3),
               f"{numero} / {total}", fuente=F_CUERPO, tam=12, color=color,
               alineacion=PP_ALIGN.RIGHT)


def marca_kicker(slide, texto, *, sobre_terracota=False, top=0.22):
    color = CREMA if sobre_terracota else RGBColor(0x8A, 0x82, 0x77)
    caja_texto(slide, MARGEN_X, in_(top), in_(8), in_(0.3), texto.upper(),
               fuente=F_CUERPO, tam=12, color=color, negrita=True)


def nueva_slide(prs, *, fondo_color=BLANCO):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fondo(slide, fondo_color)
    return slide


def imagen_ajustada(slide, ruta, left, top, max_w, max_h, *, borde=True, alt=""):
    """Inserta la imagen conservando su proporcion real (sin deformar), dentro
    de una tarjeta crema con borde fino si borde=True."""
    with Image.open(ruta) as im:
        w_px, h_px = im.size
    ratio = w_px / h_px
    max_w_in, max_h_in = max_w / Inches(1), max_h / Inches(1)
    if max_w_in / max_h_in > ratio:
        h_in = max_h_in
        w_in = h_in * ratio
    else:
        w_in = max_w_in
        h_in = w_in / ratio
    left_c = left + Emu(int((max_w - Inches(w_in)) / 2))
    top_c = top + Emu(int((max_h - Inches(h_in)) / 2))
    pad = Inches(0.12)
    if borde:
        tarjeta = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, left_c - pad, top_c - pad,
            Inches(w_in) + 2 * pad, Inches(h_in) + 2 * pad)
        tarjeta.fill.solid()
        tarjeta.fill.fore_color.rgb = CREMA
        tarjeta.line.color.rgb = BORDE
        tarjeta.line.width = Pt(0.75)
        tarjeta.shadow.inherit = False
    pic = slide.shapes.add_picture(ruta, left_c, top_c, width=Inches(w_in), height=Inches(h_in))
    if alt:
        set_alt_text(pic, alt)
    return pic


def numero_grande(slide, left, top, width, numero, etiqueta, *, color=TERRACOTA):
    caja_texto(slide, left, top, width, in_(1.0), numero, fuente=F_TITULO, tam=54,
               color=color, negrita=True, alineacion=PP_ALIGN.CENTER)
    caja_texto(slide, left, top + in_(0.95), width, in_(0.5), etiqueta, fuente=F_CUERPO,
               tam=15, color=TINTA, alineacion=PP_ALIGN.CENTER)


def notas(slide, texto):
    slide.notes_slide.notes_text_frame.text = texto


def contar_palabras(texto):
    # quita la marca de tiempo "[NN s]" antes de contar
    import re
    limpio = re.sub(r"^\[\d+\s*s\]\s*", "", texto)
    return len(limpio.split())


# ---------------------------------------------------------------------------
# Construccion de la presentacion
# ---------------------------------------------------------------------------
prs = Presentation()
prs.slide_width = ANCHO
prs.slide_height = ALTO

TOTAL_PRINCIPALES = 14
notas_info = []  # (n_slide, titulo, segundos, palabras)

# --- 1. Portada -------------------------------------------------------------
s = nueva_slide(prs, fondo_color=TERRACOTA)
marca_kicker(s, "Borrador para revisión del docente", sobre_terracota=True, top=0.35)
caja_texto(s, MARGEN_X, in_(1.5), ANCHO - 2 * MARGEN_X, in_(2.1),
           "Modelado y comparación de curvas de crecimiento en Coffea arabica "
           "con y sin micorrizas",
           fuente=F_TITULO, tam=34, color=CREMA, negrita=True, interlineado=1.12)
caja_texto(s, MARGEN_X, in_(3.75), ANCHO - 2 * MARGEN_X, in_(0.7),
           "Ajuste de tres modelos no lineales (Exponencial, Logístico, Gompertz) "
           "y comparación estadística +M vs −M con la app Coffea IA",
           fuente=F_CUERPO, tam=19, color=CREMA)
caja_texto(s, MARGEN_X, in_(4.9), ANCHO - 2 * MARGEN_X, in_(0.45),
           "Richard Montez  ·  Diego Barrios  ·  Santiago Uribe  ·  Oscar Llanos",
           fuente=F_CUERPO, tam=17, color=CREMA, negrita=True)
caja_texto(s, MARGEN_X, in_(5.35), ANCHO - 2 * MARGEN_X, in_(0.4),
           "Programa de Ingeniería, Universidad Simón Bolívar [facultad/departamento por definir]",
           fuente=F_CUERPO, tam=14, color=CREMA)
caja_texto(s, MARGEN_X, in_(5.75), ANCHO - 2 * MARGEN_X, in_(0.4),
           "Evento: [por definir]   ·   Fecha: [por definir]",
           fuente=F_CUERPO, tam=14, color=CREMA)
caja_texto(s, MARGEN_X, in_(6.7), ANCHO - 2 * MARGEN_X, in_(0.4),
           "github.com/0scar07/proyecto-coffea-hma",
           fuente=F_CUERPO, tam=13, color=CREMA)
n1 = ("[30 s] Buenos días. Somos el equipo de Coffea IA, un proyecto de modelado "
      "aplicado, no un experimento de campo nuevo: tomamos datos ya publicados de "
      "crecimiento de café con y sin micorrizas, y construimos una herramienta que "
      "ajusta y compara modelos matemáticos de crecimiento sobre esos datos. En los "
      "próximos minutos mostramos qué hace la herramienta, qué encontramos, y qué "
      "limitaciones asumimos con honestidad.")
notas(s, n1)
notas_info.append((1, "Portada", 30, contar_palabras(n1)))

# --- 2. El problema (apertura de bloque, terracota) -------------------------
s = nueva_slide(prs, fondo_color=TERRACOTA)
titulo_slide(s, "El problema", color=CREMA, top=1.0)
viñetas(s, MARGEN_X, in_(2.3), ANCHO - 2 * MARGEN_X, in_(3), [
    "HMA: biofertilizante de interés para el vivero de café.",
    "Pregunta: ¿cómo modelar y comparar el crecimiento con rigor?",
    "Dos pasos: modelar la forma, comparar los grupos.",
], tam=21, color=CREMA)
n2 = ("[40 s] Los hongos micorrízicos arbusculares se estudian como biofertilizante "
      "para el vivero de Coffea arabica. Pero comparar con y sin micorriza solo "
      "mirando promedios en una tabla no basta: no describe la forma del crecimiento "
      "ni cuantifica si la diferencia es estadísticamente sólida. El problema tiene "
      "dos partes: primero modelar matemáticamente cómo crece la planta, y después "
      "comparar los dos grupos con una prueba estadística apropiada.")
notas(s, n2)
notas_info.append((2, "El problema", 40, contar_palabras(n2)))

# --- 3. Objetivo y resultados esperados -------------------------------------
s = nueva_slide(prs)
titulo_slide(s, "Objetivo y resultados esperados")
viñetas(s, MARGEN_X, in_(2.0), ANCHO - 2 * MARGEN_X, in_(3), [
    "Objetivo: ajustar 3 modelos y comparar −M vs +M.",
    "Resultado esperado 1: tabla de bondad de ajuste (R², RMSE, MAE).",
    "Resultado esperado 2: tabla del efecto de la inoculación.",
])
n3 = ("[40 s] El objetivo de la herramienta es automatizar dos resultados concretos, "
      "los mismos que calcula la app en la sección Resultados esperados. El primero "
      "es una tabla de bondad de ajuste: qué tan bien se ajusta cada modelo, medido "
      "con R², RMSE y MAE, por variable y por grupo. El segundo es una tabla del "
      "efecto de la inoculación: cuánto cambia la media de +M frente a −M en cada "
      "día, con su prueba t correspondiente.")
notas(s, n3)
notas_info.append((3, "Objetivo y resultados esperados", 40, contar_palabras(n3)))

# --- 4. Los datos -------------------------------------------------------------
s = nueva_slide(prs)
titulo_slide(s, "Los datos")
viñetas(s, MARGEN_X, in_(2.0), ANCHO - 2 * MARGEN_X, in_(3), [
    "Fuente: Aguirre-Medina et al. (2023), Rev. Fitotecnia Mexicana.",
    "4 variables · 4 momentos (28-112 ddt) · 5 réplicas.",
    "Grupos: −M (control) y +M (inoculado con HMA).",
    "Réplicas sintéticas: reconstruidas desde medias y CV% publicados.",
])
n4 = ("[50 s] Los datos base son reales, publicados por Aguirre-Medina y colegas en "
      "2023: cuatro variables de crecimiento medidas en cuatro momentos, de los 28 a "
      "los 112 días después del trasplante, con cinco réplicas por grupo y día. Un "
      "punto que subrayamos siempre: el artículo original solo publica promedios y "
      "coeficiente de variación, no mediciones planta por planta. Por eso las "
      "réplicas individuales que usa la herramienta son sintéticas, generadas para "
      "reproducir esos estadísticos — no son observaciones nuevas de campo.")
notas(s, n4)
notas_info.append((4, "Los datos", 50, contar_palabras(n4)))

# --- 5. Metodos (apertura de bloque, terracota) ------------------------------
s = nueva_slide(prs, fondo_color=TERRACOTA)
titulo_slide(s, "Métodos", color=CREMA, top=1.0)
viñetas(s, MARGEN_X, in_(2.3), ANCHO - 2 * MARGEN_X, in_(3.5), [
    "3 modelos: Exponencial, Logístico, Gompertz (regresión no lineal).",
    "Métricas: R², RMSE, MAE por variable, grupo y modelo.",
    "Comparación de grupos: prueba t de Welch por día.",
    "Sin días suficientes o sin convergencia: no se fuerza un ajuste.",
], tam=20, color=CREMA)
n5 = ("[55 s] Ajustamos tres modelos clásicos de crecimiento por mínimos cuadrados "
      "no lineales, usando curve fit: esto es regresión no lineal, no aprendizaje "
      "automático, no hay entrenamiento de ningún modelo predictivo. Para cada "
      "ajuste calculamos R², RMSE y MAE, y comparamos los grupos con una prueba t "
      "de Welch por variable y día. El punto que más nos importa metodológicamente: "
      "si un conjunto de datos no tiene suficientes días distintos, o si el ajuste "
      "no converge, la herramienta nunca fuerza un resultado — lo marca "
      "explícitamente.")
notas(s, n5)
notas_info.append((5, "Métodos", 55, contar_palabras(n5)))

# --- 6. La app (diagrama + captura) ------------------------------------------
s = nueva_slide(prs)
titulo_slide(s, "La app", top=0.45, tam=30)

# Diagrama simple de 4 cajas con flechas (formas vectoriales propias)
cajas = [
    ("Datos", "cargar_datos_desde_archivo"),
    ("Ajuste de 3 modelos", "ajustar_todos_los_modelos"),
    ("Métricas y estadística", "calcular_tabla_modelo /\ncalcular_efecto_micorriza"),
    ("Gráficas y reporte", "fig_curvas_publicacion /\nReportePDF"),
]
diag_top = in_(1.55)
caja_w, caja_h = in_(2.75), in_(1.05)
gap = in_(0.22)
total_w = 4 * caja_w + 3 * gap
x0 = (ANCHO - total_w) / 2
for i, (nombre, func) in enumerate(cajas):
    x = x0 + i * (caja_w + gap)
    rect = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, diag_top, caja_w, caja_h)
    rect.fill.solid()
    rect.fill.fore_color.rgb = CREMA
    rect.line.color.rgb = TERRACOTA
    rect.line.width = Pt(1.25)
    rect.shadow.inherit = False
    tf = rect.text_frame
    tf.word_wrap = True
    tf.margin_top = Pt(6)
    p0 = tf.paragraphs[0]
    p0.alignment = PP_ALIGN.CENTER
    r0 = p0.add_run()
    r0.text = nombre
    r0.font.name = F_CUERPO
    r0.font.bold = True
    r0.font.size = Pt(14)
    r0.font.color.rgb = TINTA
    p1 = tf.add_paragraph()
    p1.alignment = PP_ALIGN.CENTER
    r1 = p1.add_run()
    r1.text = func
    r1.font.name = "Consolas"
    r1.font.size = Pt(10.5)
    r1.font.color.rgb = TERRACOTA
    set_alt_text(rect, f"Paso del flujo: {nombre} ({func})")
    if i < len(cajas) - 1:
        flecha = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + caja_w, diag_top + caja_h / 2 - Pt(6),
                                     gap, Pt(12))
        flecha.fill.solid()
        flecha.fill.fore_color.rgb = TERRACOTA
        flecha.line.fill.background()
        flecha.shadow.inherit = False

imagen_ajustada(s, os.path.join(SHOTS, "curvas.png"), MARGEN_X, in_(3.05),
                ANCHO - 2 * MARGEN_X, in_(3.35),
                alt="Captura de la app Coffea IA mostrando las curvas de altura ajustadas con datos reales")
n6 = ("[45 s] La app está construida en Streamlit. El usuario carga datos de prueba "
      "simulados o el Excel real de Aguirre-Medina et al., y con un solo botón se "
      "ejecuta el ajuste de los tres modelos sobre las cuatro variables y los dos "
      "grupos. A partir de ahí la misma app genera las tablas, las gráficas de "
      "curvas y barras, y un reporte en PDF descargable. Aquí la ven corriendo con "
      "los datos reales.")
notas(s, n6)
notas_info.append((6, "La app", 45, contar_palabras(n6)))

# --- 7. Resultado 1: bondad de ajuste (apertura de bloque, terracota) --------
s = nueva_slide(prs, fondo_color=TERRACOTA)
titulo_slide(s, "Resultado 1: bondad de ajuste por modelo", color=CREMA, top=0.5, tam=28)
imagen_ajustada(s, os.path.join(FIGURAS, "barras_r2_modelos.png"), MARGEN_X, in_(1.6),
                in_(7.6), in_(5.3),
                alt="R2 de Exponencial, Logistico y Gompertz por variable y grupo, con barras vacias donde no convergio")
viñetas(s, in_(8.55), in_(1.9), in_(4.15), in_(4.5), [
    "R² entre 0.876 y 0.997 en los modelos que convergen.",
    "Altura: gana Exponencial o Logístico según el grupo.",
    "Área foliar: gana Gompertz o Exponencial según el grupo.",
    "Biomasa y hojas: Logístico es el mejor en ambos grupos.",
], tam=17, color=CREMA)
n7 = ("[55 s] Esta gráfica resume el R² de los tres modelos en las cuatro "
      "variables y los dos grupos. En general el ajuste es bueno, entre 0.876 y "
      "0.997 cuando el modelo converge. El mejor modelo no es siempre el mismo: en "
      "altura gana Exponencial o Logístico según el grupo, en área foliar Gompertz "
      "o Exponencial, y en biomasa y número de hojas, Logístico es consistentemente "
      "el mejor. Las barras vacías marcadas No convergió son Gompertz fallando en "
      "algunos grupos, que explicamos en la diapositiva de hallazgos.")
notas(s, n7)
notas_info.append((7, "Resultado 1: bondad de ajuste", 55, contar_palabras(n7)))

# --- 8. Curvas de crecimiento -------------------------------------------------
s = nueva_slide(prs)
titulo_slide(s, "Curvas de crecimiento", top=0.45, tam=30)
imagen_ajustada(s, os.path.join(FIGURAS, "curvas_area_foliar.png"), MARGEN_X, in_(1.5),
                ANCHO - 2 * MARGEN_X, in_(4.9),
                alt="Curvas de area foliar ajustadas para -M y +M con replicas observadas y banda de confianza")
caja_texto(s, MARGEN_X, in_(6.55), ANCHO - 2 * MARGEN_X, in_(0.5),
           "Lectura: el área foliar de +M se separa de −M desde ~84 ddt.",
           fuente=F_CUERPO, tam=16, color=TERRACOTA, negrita=True)
n8 = ("[50 s] Esta es la mejor figura para ilustrar el patrón general: área foliar "
      "en ambos grupos, con las réplicas observadas como círculos y las curvas "
      "convergidas superpuestas. Se ve que en la ventana muestreada el crecimiento "
      "todavía es acelerado, no se alcanza a ver el aplanamiento característico de "
      "un modelo sigmoide. Por eso, como notan en el pie de la figura, la asíntota "
      "K no se dibuja para Logístico ni Gompertz en ninguno de los dos grupos.")
notas(s, n8)
notas_info.append((8, "Curvas de crecimiento", 50, contar_palabras(n8)))

# --- 9. Resultado 2: efecto de la inoculacion --------------------------------
s = nueva_slide(prs)
titulo_slide(s, "Resultado 2: efecto de la inoculación", top=0.45, tam=28)
imagen_ajustada(s, os.path.join(FIGURAS, "barras_area_foliar.png"), MARGEN_X, in_(1.45),
                in_(8.3), in_(4.55),
                alt="Area foliar por dia, media mas menos DE, con significancia de la prueba t de Welch")
numero_grande(s, in_(9.55), in_(2.1), in_(3.15), "+97.1%", "Área foliar a 112 ddt (+M vs −M)")
viñetas(s, in_(9.15), in_(3.55), in_(3.9), in_(2.6), [
    "Biomasa: significativa en 3/4 días (+71.7% a 112 ddt).",
    "Altura y hojas: mayormente no significativas.",
], tam=15)
caja_texto(s, MARGEN_X, in_(6.35), ANCHO - 2 * MARGEN_X, in_(0.7),
           "Recuerda: réplicas sintéticas — ilustra la metodología, no es evidencia experimental nueva.",
           fuente=F_CUERPO, tam=14, color=RGBColor(0x6B, 0x63, 0x59))
n9 = ("[60 s] Aquí comparamos +M contra −M con la prueba t de Welch. El área foliar "
      "es el resultado más consistente: diferencia significativa en los cuatro "
      "días, con más de 97% de incremento a los 112 días. La biomasa total también "
      "es significativa en tres de cuatro días, con 71.7% de incremento al final. "
      "Altura y número de hojas no muestran diferencias significativas en la "
      "mayoría de los días. Importante: esto viene de réplicas sintéticas, ilustra "
      "la metodología, no es evidencia experimental nueva.")
notas(s, n9)
notas_info.append((9, "Resultado 2: efecto de la inoculación", 60, contar_palabras(n9)))

# --- 10. Hallazgo: K no plausible ---------------------------------------------
s = nueva_slide(prs)
titulo_slide(s, "Hallazgo: cuándo no confiar en K", top=0.45, tam=28)
numero_grande(s, MARGEN_X, in_(1.5), in_(4.0), "790 679.8", "K estimada en cm (Logístico, Altura, −M)")
numero_grande(s, MARGEN_X + in_(4.3), in_(1.5), in_(4.0), "15.0", "cm · máximo observado en ese grupo",
              color=TINTA)
viñetas(s, MARGEN_X, in_(3.15), ANCHO - 2 * MARGEN_X, in_(3.6), [
    "Con 4 puntos, Logístico/Gompertz a veces no identifican K.",
    "Criterio: convergencia + R²≥0.90 + K≤1.5×máx + Ti en rango.",
    "Si falla una condición: no se dibuja, se anota.",
], tam=19)
n10 = ("[55 s] Este es el hallazgo metodológico que más nos importa mostrar. En "
       "altura, grupo control, el modelo Logístico converge con buen R², pero "
       "estima una asíntota K de casi 800 mil centímetros, cuando la altura máxima "
       "observada es 15 centímetros: una asíntota sin sentido biológico. Por eso la "
       "herramienta exige cuatro condiciones antes de dibujar K: modelo convergido, "
       "R² de al menos 0.90, K hasta 1.5 veces el máximo observado, y punto de "
       "inflexión dentro de los días muestreados. Si alguna falla, no se dibuja: se "
       "anota.")
notas(s, n10)
notas_info.append((10, "Hallazgo: K no plausible", 55, contar_palabras(n10)))

# --- 11. Validacion (apertura de bloque, terracota) --------------------------
s = nueva_slide(prs, fondo_color=TERRACOTA)
titulo_slide(s, "Validación", color=CREMA, top=1.0)
viñetas(s, MARGEN_X, in_(2.3), ANCHO - 2 * MARGEN_X, in_(3), [
    "Hecha: validación cruzada interna (hold-out 80/20) de las medias.",
    "En curso: validación externa con datos independientes.",
    "Aún no hay resultados externos que presentar.",
], tam=21, color=CREMA)
n11 = ("[45 s] La única validación completada hasta ahora es interna: un hold-out "
       "ochenta-veinte que mide qué tan estables son las medias estimadas, "
       "implementado en validacion cruzada real. Eso no mide generalización a otro "
       "estudio. La validación externa, con un conjunto de datos independiente de "
       "Coffea arabica, está en curso — todavía no tenemos resultados que "
       "mostrarles, y preferimos decirlo así de claro antes que insinuar un "
       "resultado que no existe.")
notas(s, n11)
notas_info.append((11, "Validación", 45, contar_palabras(n11)))

# --- 12. Limitaciones honestas -------------------------------------------------
s = nueva_slide(prs)
titulo_slide(s, "Limitaciones honestas")
viñetas(s, MARGEN_X, in_(2.0), ANCHO - 2 * MARGEN_X, in_(3.5), [
    "Réplicas sintéticas: los p-values ilustran metodología, no evidencia nueva.",
    "Ventana 28-112 ddt: solo fase acelerada, no de desaceleración.",
    "Un solo estudio de origen (Aguirre-Medina et al., 2023).",
    "Gompertz no converge en varios grupos con solo 4 puntos.",
])
n12 = ("[50 s] Preferimos ser explícitos con las limitaciones en vez de "
       "minimizarlas. Primero, las réplicas son sintéticas, así que los valores p "
       "ilustran la metodología estadística, no constituyen evidencia experimental "
       "independiente nueva. Segundo, la ventana de muestreo, de 28 a 112 días, "
       "captura la fase acelerada del crecimiento, no la fase de desaceleración que "
       "necesitan los modelos sigmoides. Tercero, todo viene de un solo estudio de "
       "origen. Estas tres limitaciones son la motivación de la validación externa.")
notas(s, n12)
notas_info.append((12, "Limitaciones honestas", 50, contar_palabras(n12)))

# --- 13. Entregables y estado real ---------------------------------------------
s = nueva_slide(prs)
titulo_slide(s, "Entregables y estado real", top=0.45, tam=28)
filas = [
    ("1", "Manuscrito científico", "Borrador para revisión del docente"),
    ("2", "Metodología estadística", "Cubierto por la app"),
    ("3", "Métricas de ajuste de modelos", "Cubierto por la app"),
    ("4", "Código documentado", "En preparación (HTML navegable)"),
    ("5", "Informes de estudiantes", "Plantilla"),
    ("6", "Taller de capacitación", "Plantilla"),
    ("7", "Publicación colaborativa", "Esquema / en preparación"),
    ("8", "Artículo divulgativo", "Borrador maquetado, pendiente de publicar"),
    ("9", "Guía técnica de usuario", "Borrador para revisión del docente"),
    ("10", "Ponencia (esta presentación)", "Material preparado, pendiente de presentar"),
]
tabla_top, tabla_left = in_(1.45), MARGEN_X
tabla_w, tabla_h = ANCHO - 2 * MARGEN_X, in_(5.5)
gshape = s.shapes.add_table(len(filas) + 1, 3, tabla_left, tabla_top, tabla_w, tabla_h)
tabla = gshape.table
tabla.columns[0].width = in_(0.6)
tabla.columns[1].width = in_(5.3)
tabla.columns[2].width = tabla_w - in_(0.6) - in_(5.3)
encabezados = ("#", "Producto", "Estado (entregables/README.md)")
for c, txt in enumerate(encabezados):
    cel = tabla.cell(0, c)
    cel.text = txt
    cel.fill.solid()
    cel.fill.fore_color.rgb = TERRACOTA
    p = cel.text_frame.paragraphs[0]
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = CREMA
    p.font.name = F_CUERPO
for r, (num, prod, estado) in enumerate(filas, start=1):
    for c, txt in enumerate((num, prod, estado)):
        cel = tabla.cell(r, c)
        cel.text = txt
        cel.fill.solid()
        cel.fill.fore_color.rgb = BLANCO if r % 2 else CREMA
        cel.margin_top = Pt(2)
        cel.margin_bottom = Pt(2)
        p = cel.text_frame.paragraphs[0]
        p.font.size = Pt(13)
        p.font.name = F_CUERPO
        p.font.color.rgb = TINTA
n13 = ("[40 s] Esta es la tabla real de entregables. Ningún producto está cerrado "
       "todavía: varios ya tienen un borrador sólido listo para revisión, dos están "
       "cubiertos directamente por la app, y otros siguen como plantilla pendiente "
       "de datos reales. Esta misma ponencia y el artículo divulgativo son los dos "
       "productos que acabamos de completar en esta etapa; quedan marcados como "
       "material preparado, pendiente de presentar o publicar, no como hechos "
       "consumados.")
notas(s, n13)
notas_info.append((13, "Entregables y estado real", 40, contar_palabras(n13)))

# --- 14. Cierre ------------------------------------------------------------
s = nueva_slide(prs, fondo_color=TERRACOTA)
titulo_slide(s, "Gracias", color=CREMA, top=1.3)
viñetas(s, MARGEN_X, in_(2.6), ANCHO - 2 * MARGEN_X, in_(2.6), [
    "Repositorio: github.com/0scar07/proyecto-coffea-hma",
    "App y documentación técnica navegable en el mismo repositorio.",
    "Contacto: [por definir]  ·  Preguntas.",
], tam=21, color=CREMA)
n14 = ("[45 s] Para cerrar: todo el código, los datos, y la documentación técnica "
       "navegable están en este mismo repositorio, incluida esta ponencia. Con "
       "gusto respondemos preguntas, y si alguien quiere ver el comportamiento de "
       "una variable específica en vivo, tenemos la app abierta para mostrarla en "
       "el momento. Gracias por su tiempo y por la retroalimentación que puedan "
       "darnos sobre este trabajo, que todavía está en preparación y revisión.")
notas(s, n14)
notas_info.append((14, "Cierre", 45, contar_palabras(n14)))

# pie de pagina en las 14 principales (todas menos backup)
for idx, sl in enumerate(prs.slides, start=1):
    sobre_terr = idx in (1, 2, 5, 7, 11, 14)
    pie_pagina(sl, idx, TOTAL_PRINCIPALES, sobre_terracota=sobre_terr)

# ---------------------------------------------------------------------------
# Respaldo: preguntas que puede hacer el jurado (4 diapositivas)
# ---------------------------------------------------------------------------
RESPALDO = [
    ("¿Por qué usar réplicas sintéticas y no los datos originales?",
     "El paper de Aguirre-Medina et al. (2023) solo publica medias y CV% por "
     "tratamiento y día, no mediciones planta por planta. Generamos réplicas "
     "sintéticas que reproducen exactamente esos estadísticos para poder ajustar "
     "los modelos y correr una prueba t; sin eso no habría datos individuales "
     "que ajustar."),
    ("¿Por qué Logístico o Gompertz a veces no convergen?",
     "Con solo 4 días de muestreo por grupo, un modelo de 3 parámetros como "
     "Logístico o Gompertz tiene apenas 1 grado de libertad. Si la curva "
     "observada no muestra todavía el «codo» de desaceleración, curve_fit no "
     "encuentra una solución estable: la app lo marca como «No convergió» en vez "
     "de forzar un ajuste."),
    ("¿Qué significa un R² alto con una K absurda?",
     "R² alto solo dice que la curva pasa cerca de los puntos observados dentro "
     "del rango muestreado; no garantiza que la extrapolación de la asíntota K "
     "tenga sentido fuera de ese rango. Por eso el criterio de plausibilidad "
     "evalúa K por separado del R², con un límite de 1.5 veces el máximo "
     "observado."),
    ("¿Qué falta para la validación externa?",
     "Un conjunto de datos de Coffea arabica de un estudio distinto al de "
     "Aguirre-Medina et al., con mediciones individuales reales, para correr los "
     "mismos tres modelos y comparar métricas de ajuste fuera de muestra. Ese "
     "trabajo está en curso; todavía no hay resultados que presentar."),
]
for i, (pregunta, respuesta) in enumerate(RESPALDO, start=1):
    s = nueva_slide(prs, fondo_color=CREMA)
    marca_kicker(s, "Respaldo — preguntas que puede hacer el jurado", top=0.4)
    caja_texto(s, MARGEN_X, in_(1.1), ANCHO - 2 * MARGEN_X, in_(1.3), pregunta,
               fuente=F_TITULO, tam=26, color=TERRACOTA, negrita=True, interlineado=1.15)
    caja_texto(s, MARGEN_X, in_(2.7), ANCHO - 2 * MARGEN_X, in_(4.0), respuesta,
               fuente=F_CUERPO, tam=19, color=TINTA, interlineado=1.35)
    caja_texto(s, MARGEN_X, ALTO - in_(0.42), in_(4), in_(0.3),
               f"Coffea IA · Respaldo {i}/4", fuente=F_CUERPO, tam=12,
               color=RGBColor(0x8A, 0x82, 0x77))
    notas(s, f"Diapositiva de respaldo, no forma parte de los 10-12 minutos principales. "
             f"Usar solo si surge esta pregunta en la ronda de preguntas.")

prs.save(SALIDA)
print(f"Guardado: {SALIDA}")

# ---------------------------------------------------------------------------
# Verificacion honesta de las notas del orador (60-90 palabras, tiempo total)
# ---------------------------------------------------------------------------
print("\n--- Verificación de notas del orador (14 principales) ---")
total_seg = 0
for n, titulo, seg, palabras in notas_info:
    total_seg += seg
    marca = "OK" if 60 <= palabras <= 90 else "FUERA DE RANGO"
    print(f"{n:2d}. {titulo:35s} {palabras:3d} palabras  [{seg:2d} s]  {marca}")
print(f"\nTiempo total (14 principales): {total_seg} s = {total_seg/60:.1f} min "
      f"({'OK 10-12 min' if 600 <= total_seg <= 720 else 'FUERA DE RANGO'})")
print(f"Total de diapositivas en el archivo: {len(prs.slides.__iter__.__self__._sldIdLst)}")
