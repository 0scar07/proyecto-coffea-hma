# -*- coding: utf-8 -*-
"""
==============================================================================
Coffea arabica — Modelos de crecimiento (−M vs +M)
==============================================================================
v5: los datos de prueba ahora incluyen RÉPLICAS por día (varias "plantas"
simuladas), lo que permite una prueba t/ANOVA de verdad (no solo una
aproximación con la serie temporal). Además: carga de tus propios datos
reales (CSV/Excel en formato largo) y exportación de un reporte en PDF.

CÓMO CORRERLA:
    pip install -r requirements.txt
    streamlit run app.py
==============================================================================
"""

import io
import re
import os
import tempfile
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from scipy.optimize import brentq, curve_fit
from scipy.stats import f_oneway, t as t_dist, ttest_ind, ttest_ind_from_stats, tukey_hsd
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Coffea arabica · Modelos de crecimiento", page_icon="⸙", layout="wide")

UNIDADES = {"altura": "cm", "biomasa": "g", "diametro": "mm", "hojas": "unidades", "area_foliar": "cm²"}
NOMBRE_VARIABLE = {"altura": "Altura", "biomasa": "Biomasa total (TDM)",
                    "diametro": "Diámetro del tallo", "hojas": "Número de hojas",
                    "area_foliar": "Área foliar"}
# Para frases dentro de títulos ("…, la altura es 12 % mayor…").
NOMBRE_EN_FRASE = {"altura": "la altura", "biomasa": "la biomasa total", "diametro": "el diámetro del tallo",
                   "hojas": "el número de hojas", "area_foliar": "el área foliar"}
DIAS = np.arange(0, 121, 10)
N_REPLICAS = 5

# ==============================================================================
# ESTADO INICIAL
# ==============================================================================
defaults = {
    "semilla": 42, "lote": 1, "seccion": "Resumen",
    "ajustado": False, "resultados": None, "variables_incluidas": ["altura", "biomasa", "diametro", "hojas"],
    "modelos_incluidos": ["Exponencial", "Logístico", "Gompertz"],
    "fuente_datos": "simulado", "datos_reales": None, "dia_ttest": 120, "ultimo_archivo_id": None,
    "cita_datos_reales": "", "recien_ajustado": False,
    "ve_paper": None, "ve_paper_id": None, "ve_ultimo_archivo": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==============================================================================
# TOKENS DE DISEÑO — "Cuaderno de campo": paleta única, sin modo oscuro
# ==============================================================================
T = dict(
    BG="#FAF8F5", SURFACE="#FFFFFF", CARD="#FFFFFF", BORDER="#E4DFD6", BORDER_STRONG="#D6CFC2",
    INK="#201C18", INK_MUTED="#6B6459",
    ACCENT="#A8432B", ACCENT_SOFT="#A8432B14",
    # Azul para −M (validado contra el terracota de +M: se distinguen también con daltonismo).
    CONTROL="#2A6FB0",
    VERDE="#3F7D45", AMBAR="#B8791E", ROJO="#BF3B3B",
)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.stApp {{
    background-color: {T['BG']};
    background-image: radial-gradient({T['BORDER']} 1px, transparent 1px);
    background-size: 24px 24px;
}}
[data-testid="stAppViewContainer"] {{ color: {T['INK']}; }}
[data-testid="stMainBlockContainer"] {{ color: {T['INK']}; }}
[data-testid="stHeader"] {{ background-color: {T['BG']}; }}

h1, h2, h3 {{ font-family: 'Fraunces', serif !important; font-weight: 600 !important; color: {T['INK']} !important; letter-spacing: -0.01em; }}
p, li, span, label, div {{ color: {T['INK']}; }}

:root {{
    --radius-sm: 8px;
    --radius-pill: 999px;
}}

[data-testid="stVerticalBlock"] {{ gap: 0.9rem; }}

.eyebrow {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; letter-spacing: 0.20em;
    text-transform: uppercase; color: {T['ACCENT']}; margin-bottom: 0.5rem; display: block; }}
.field-label {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.66rem; letter-spacing: 0.14em;
    text-transform: uppercase; color: {T['INK_MUTED']}; margin: 1rem 0 0.4rem 0; display: block; }}
.card-title {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.3rem; color: {T['INK']};
    letter-spacing: -0.01em; margin: 0 0 0.1rem 0; display: block; }}
.rule {{ border: none; border-top: 1px solid {T['BORDER']}; margin: 0.6rem 0 1.2rem 0; }}

.topbar {{ display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid {T['BORDER']}; padding-bottom: 0.6rem; margin-bottom: 0.4rem; }}
.topbar-brand {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.05rem; color: {T['INK']}; }}
.topbar-tag {{ font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; letter-spacing: 0.08em;
    color: {T['INK_MUTED']}; border: 1px solid {T['BORDER']}; padding: 0.2rem 0.6rem; border-radius: var(--radius-pill); }}

.tag {{ display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem;
    font-weight: 600; letter-spacing: 0.05em; padding: 0.15rem 0.6rem; border: 1px solid {T['BORDER']};
    border-radius: var(--radius-pill); color: {T['INK_MUTED']}; margin-right: 0.4rem; }}
.tag-control {{ border-color: {T['CONTROL']}; color: {T['CONTROL']}; }}
.tag-tratado {{ border-color: {T['ACCENT']}; color: {T['ACCENT']}; }}

.badge {{ display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
    font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; padding: 0.2rem 0.6rem;
    border-radius: var(--radius-pill); }}
.badge-verde {{ background-color: {T['VERDE']}1f; color: {T['VERDE']}; border: 1px solid {T['VERDE']}55; }}
.badge-ambar {{ background-color: {T['AMBAR']}1f; color: {T['AMBAR']}; border: 1px solid {T['AMBAR']}55; }}
.badge-rojo  {{ background-color: {T['ROJO']}1f;  color: {T['ROJO']};  border: 1px solid {T['ROJO']}55; }}

section[data-testid="stSidebar"] {{ background-color: {T['SURFACE']}; border-right: 1px solid {T['BORDER']}; }}
section[data-testid="stSidebar"] * {{ color: {T['INK']}; }}
section[data-testid="stSidebar"] [data-testid="stMainBlockContainer"] {{ padding-top: 1.75rem; }}

/* Navegación lateral: lista limpia, no botones con caja */
section[data-testid="stSidebar"] div[data-testid="stButton"] button {{
    border: none !important; background-color: transparent !important; box-shadow: none !important;
    border-radius: 6px !important; border-left: 3px solid transparent !important;
    padding: 0.45rem 0.7rem !important; font-weight: 500 !important; color: {T['INK_MUTED']} !important; }}
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {{
    background-color: {T['BORDER']}66 !important; color: {T['INK']} !important; }}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {{
    background-color: {T['ACCENT_SOFT']} !important; color: {T['ACCENT']} !important;
    border-left: 3px solid {T['ACCENT']} !important; font-weight: 600 !important; }}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"]:hover {{
    background-color: {T['ACCENT_SOFT']} !important; }}

/* Firma visual: "ficha de campo" -- marcador invisible (ver .ficha-marca) identifica
   que tarjeta (st.container(border=True)) es cual, sin depender de nombres internos
   de Streamlit que cambian entre versiones (ej. stVerticalBlockBorderWrapper). */
[data-testid="stElementContainer"]:has(.ficha-marca) {{
    height: 0 !important; min-height: 0 !important; margin: 0 !important; padding: 0 !important;
    overflow: visible !important; }}
[data-testid="stElementContainer"]:has(.ficha-marca) [data-testid="stMarkdownContainer"] p {{ margin: 0 !important; }}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .ficha-marca) {{
    background-color: {T['CARD']} !important;
    box-shadow: 0 1px 3px rgba(32,28,24,0.05);
    position: relative; }}
.ficha-marca {{ display: block; position: absolute; top: -3px; left: 18px; width: 28px; height: 6px;
    background-color: {T['ACCENT']}; border-radius: 0 0 3px 3px; opacity: 0.85; pointer-events: none; }}

[data-testid="stMetric"] {{ background-color: {T['CARD']}; border: 1px solid {T['BORDER']};
    border-radius: var(--radius-sm); padding: 0.9rem 1rem 0.7rem 1rem; box-shadow: 0 1px 3px rgba(32,28,24,0.04); }}
[data-testid="stMetricValue"] {{ font-family: 'IBM Plex Mono', monospace; color: {T['INK']};
    font-size: clamp(1.1rem, 2.6vw, 1.6rem) !important; white-space: normal !important;
    overflow-wrap: break-word !important; line-height: 1.25 !important; }}
[data-testid="stMetricLabel"] {{ font-family: 'IBM Plex Mono', monospace; text-transform: uppercase;
    letter-spacing: 0.10em; font-size: 0.66rem; color: {T['INK_MUTED']}; }}

[data-testid="stDataFrame"] {{ border: 1px solid {T['BORDER']}; border-radius: var(--radius-sm); overflow: hidden; }}

[data-testid="stFileUploaderDropzone"] {{ background-color: {T['SURFACE']}; border: 1px dashed {T['BORDER_STRONG']};
    border-radius: var(--radius-sm); }}

div[data-testid="stButton"] button[kind="secondary"] {{ border-color: {T['BORDER']} !important; }}

[data-testid="stAlertContainer"] {{ border-radius: var(--radius-sm); border: 1px solid transparent; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {{
    background-color: {T['AMBAR']}18; border-color: {T['AMBAR']}55; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) [data-testid="stAlertDynamicIcon"] {{ color: {T['AMBAR']}; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{
    background-color: {T['ROJO']}18; border-color: {T['ROJO']}55; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) [data-testid="stAlertDynamicIcon"] {{ color: {T['ROJO']}; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {{
    background-color: {T['VERDE']}18; border-color: {T['VERDE']}55; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) [data-testid="stAlertDynamicIcon"] {{ color: {T['VERDE']}; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) {{
    background-color: {T['CONTROL']}18; border-color: {T['CONTROL']}55; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) [data-testid="stAlertDynamicIcon"] {{ color: {T['CONTROL']}; }}

button[kind="secondary"], button[kind="primary"] {{ border-radius: var(--radius-sm) !important; font-family: 'Inter', sans-serif !important; }}
section[data-testid="stSidebar"] div[data-testid="stButton"] button {{ text-align: left !important; justify-content: flex-start !important; }}
</style>
""", unsafe_allow_html=True)

pio.templates["cuaderno"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=T["CARD"], plot_bgcolor=T["CARD"],
        font=dict(family="Inter, sans-serif", color=T["INK"], size=13),
        xaxis=dict(gridcolor=T["BORDER"], zeroline=False, showline=True, linecolor=T["BORDER"],
                    tickfont=dict(family="IBM Plex Mono, monospace", size=11, color=T["INK_MUTED"])),
        yaxis=dict(gridcolor=T["BORDER"], zeroline=False, showline=True, linecolor=T["BORDER"],
                    tickfont=dict(family="IBM Plex Mono, monospace", size=11, color=T["INK_MUTED"])),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        margin=dict(l=10, r=10, t=40, b=10),
    )
)
pio.templates.default = "cuaderno"


# ==============================================================================
# ESTILO DE PUBLICACIÓN — helper único aplicado a las gráficas exportables
# (pantalla, PNG y PDF).
#
# PRINCIPIO DE DISEÑO: la figura y su texto son cosas separadas.
#   - La figura de Plotly (estilo_publicacion) contiene SOLO paneles, ejes, leyenda y
#     etiquetas de panel. Nunca lleva pie de figura incrustado como anotación.
#   - El pie de figura (construir_pie) se muestra aparte: con st.caption/st.markdown
#     debajo de la figura en la app (mostrar_pie_streamlit), como texto debajo de la
#     imagen en el PDF (pie_a_lineas_texto + multi_cell), y compuesto con la imagen final
#     en los PNG descargables (componer_png_con_pie, vía PIL).
# ==============================================================================
FUENTE_PUBLICACION = "Inter, Arial, Helvetica, sans-serif"
# Tinta de las gráficas: el texto nunca usa el color de una serie (la identidad la lleva la marca).
G_INK, G_MUTED, G_GRID, G_EJE = T["INK"], T["INK_MUTED"], "#ECE7DF", "#B9B1A4"
COLOR_GRUPO = {"-M": T["CONTROL"], "+M": T["ACCENT"]}
NOMBRE_GRUPO = {"-M": "sin micorriza (control)", "+M": "inoculado con HMA"}


def texto_grupo(g):
    """'-M' -> '−M' (signo menos tipográfico) para títulos y etiquetas."""
    return g.replace("-", "−")


def estilo_publicacion(fig, width=None, height=420, left_margin=70, top_margin=None,
                        espacio_eje_x_px=38, espacio_leyenda_px=34, titulo=None, subtitulo=None,
                        mostrar_leyenda=True, right_margin=24):
    """Plantilla visual única para toda gráfica exportable (pantalla, PNG y PDF).

    La gráfica "habla sola": un TÍTULO que dice la conclusión (no solo qué variable es) y un
    SUBTÍTULO que explica cómo leerla. Ejes limpios (solo línea base en X, cuadrícula tenue en
    Y), texto en tinta neutra y, cuando hace falta, una leyenda en una fila debajo de los
    paneles. No toca datos ni trazos: se llama al final de cada fig_*(), antes de construir_pie().
    Si no se pasa `titulo`, se conserva el título que ya tuviera la figura."""
    if titulo is None and fig.layout.title is not None and fig.layout.title.text:
        titulo = fig.layout.title.text
    lineas_sub = (subtitulo or "").count("<br>") + 1 if subtitulo else 0
    if top_margin is None:
        top_margin = (62 if titulo else 24) + 22 * lineas_sub + 34
    texto_titulo = ""
    if titulo:
        texto_titulo = f"<b>{titulo}</b>"
        if subtitulo:
            texto_titulo += f"<br><span style='font-size:13.5px;color:{G_MUTED}'>{subtitulo}</span>"

    margen_b = espacio_eje_x_px + (espacio_leyenda_px if mostrar_leyenda else 0) + 14
    alto_trazado = max(height - top_margin - margen_b, 50)
    y_leyenda = -(espacio_eje_x_px + espacio_leyenda_px / 2) / alto_trazado

    layout_kwargs = dict(
        font=dict(family=FUENTE_PUBLICACION, size=13, color=G_INK),
        paper_bgcolor="white", plot_bgcolor="white",
        title=dict(text=texto_titulo, font=dict(family=FUENTE_PUBLICACION, size=19, color=G_INK),
                   x=0.012, xanchor="left", y=1, yref="container", yanchor="top", pad=dict(t=24)),
        showlegend=mostrar_leyenda,
        legend=dict(orientation="h", xanchor="center", x=0.5, yanchor="middle", y=y_leyenda,
                    bgcolor="rgba(255,255,255,0)", bordercolor="rgba(0,0,0,0)",
                    font=dict(family=FUENTE_PUBLICACION, size=12, color=G_INK)),
        margin=dict(l=left_margin, r=right_margin, t=top_margin, b=margen_b),
        height=height,
        hoverlabel=dict(font=dict(family=FUENTE_PUBLICACION)),
    )
    if width is not None:
        layout_kwargs["width"] = width
    fig.update_layout(**layout_kwargs)
    fig.update_xaxes(
        showgrid=False, zeroline=False, showline=True, linewidth=1, linecolor=G_EJE, mirror=False,
        ticks="outside", tickwidth=1, ticklen=4, tickcolor=G_EJE,
        tickfont=dict(family=FUENTE_PUBLICACION, size=12, color=G_MUTED),
        title_font=dict(family=FUENTE_PUBLICACION, size=13, color=G_MUTED),
        automargin=True, title_standoff=12,
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=G_GRID, gridwidth=1, zeroline=False, showline=False, ticks="", nticks=7,
        tickfont=dict(family=FUENTE_PUBLICACION, size=12, color=G_MUTED),
        title_font=dict(family=FUENTE_PUBLICACION, size=13, color=G_MUTED),
        automargin=True, title_standoff=12,
    )
    return fig


def alinear_titulos_panel_izquierda(fig, n_paneles, tam_fuente=14):
    """Los subplot_titles de Plotly se centran por defecto; el diseño los pide arriba a la
    IZQUIERDA de cada panel, en negrita. Reposiciona las primeras `n_paneles` anotaciones (que
    son exactamente los subplot_titles, en el mismo orden en que se crearon)."""
    for i in range(n_paneles):
        ann = fig.layout.annotations[i]
        nombre_eje = "xaxis" if i == 0 else f"xaxis{i + 1}"
        eje = fig.layout[nombre_eje]
        x0 = eje.domain[0] if eje.domain else 0
        ann.update(x=x0, xanchor="left", text=f"<b>{ann.text}</b>",
                   font=dict(size=tam_fuente, family=FUENTE_PUBLICACION, color=G_INK))
    return fig


def _ref_ejes(i):
    """Nombres de referencia de los ejes del panel i (1-based) para anotaciones y formas."""
    return ("x", "y") if i == 1 else (f"x{i}", f"y{i}")


def encabezado_panel(fig, panel, texto, color, alto_px=28):
    """Franja de color suave con borde izquierdo sólido sobre un panel: identifica el grupo
    (−M/+M) con color Y con texto, sin depender de una leyenda. Llamar DESPUÉS de
    estilo_publicacion (necesita el alto final de la figura para medir la franja en píxeles)."""
    xr, yr = _ref_ejes(panel)
    eje_y = fig.layout["yaxis" if panel == 1 else f"yaxis{panel}"]
    m = fig.layout.margin
    alto_panel = max(((fig.layout.height or 450) - (m.t or 0) - (m.b or 0)) * (eje_y.domain[1] - eje_y.domain[0]), 50)
    y0 = 1 + 10 / alto_panel
    y1 = y0 + alto_px / alto_panel
    fig.add_shape(type="rect", xref=f"{xr} domain", yref=f"{yr} domain", x0=0, x1=1, y0=y0, y1=y1,
                  fillcolor=color, opacity=0.10, line_width=0)
    fig.add_shape(type="rect", xref=f"{xr} domain", yref=f"{yr} domain", x0=0, x1=0.008, y0=y0, y1=y1,
                  fillcolor=color, line_width=0)
    fig.add_annotation(xref=f"{xr} domain", yref=f"{yr} domain", x=0.022, y=(y0 + y1) / 2, text=texto,
                       showarrow=False, xanchor="left", yanchor="middle",
                       font=dict(family=FUENTE_PUBLICACION, size=13.5, color=G_INK))
    return fig


def sello_veredicto(fig, panel, ok, linea1, linea2, x=0.98, y=0.97):
    """Recuadro ✓/✗ en la esquina de un panel (resultado de una prueba, con icono + texto,
    nunca solo color)."""
    xr, yr = _ref_ejes(panel)
    color = T["VERDE"] if ok else T["ROJO"]
    fig.add_annotation(xref=f"{xr} domain", yref=f"{yr} domain", x=x, y=y, xanchor="right", yanchor="top",
                       showarrow=False, align="right", bgcolor="white", bordercolor=color, borderwidth=1.2,
                       borderpad=4, font=dict(family=FUENTE_PUBLICACION, size=11.5, color=color),
                       text=f"<b>{'✓' if ok else '✗'} {linea1}</b><br>{linea2}")


def etiquetas_fin_de_linea(fig, panel, etiquetas, rango_y, separacion_frac=0.055, tam=11.5):
    """Etiquetas directas al final de cada línea (en vez de una leyenda aparte). `etiquetas` es
    una lista de (texto, x, y); se separan verticalmente cuando chocan."""
    xr, yr = _ref_ejes(panel)
    sep = (rango_y[1] - rango_y[0]) * separacion_frac
    etiquetas = sorted([list(e) for e in etiquetas], key=lambda e: e[2])
    for k in range(1, len(etiquetas)):
        if etiquetas[k][2] - etiquetas[k - 1][2] < sep:
            etiquetas[k][2] = etiquetas[k - 1][2] + sep
    for texto, x, y in etiquetas:
        fig.add_annotation(x=x, y=y, xref=xr, yref=yr, text=texto, showarrow=False, xanchor="left", xshift=6,
                           font=dict(family=FUENTE_PUBLICACION, size=tam, color=G_INK))


def construir_pie(descripcion, notas=None, extra=None, titulo_notas="Notas:"):
    """Estructura común del pie de figura: una línea de descripción + una lista corta de
    notas (una viñeta por modelo que no dibujó asíntota/banda o que no convergió) + una
    nota final opcional (ej. réplicas sintéticas). Nunca se agrega como anotación dentro
    de la figura de Plotly -- se usa igual en mostrar_pie_streamlit, pie_a_lineas_texto y
    componer_png_con_pie."""
    return {"descripcion": descripcion, "notas": list(notas or []), "extra": extra, "titulo_notas": titulo_notas}


def pie_a_lineas_texto(pie):
    """Aplana el pie a líneas de texto plano, para el PDF y los PNG compuestos."""
    lineas = [pie["descripcion"]]
    if pie["notas"]:
        lineas.append(pie.get("titulo_notas", "Notas:"))
        lineas.extend(f"• {n}" for n in pie["notas"])
    if pie["extra"]:
        lineas.append(pie["extra"])
    return lineas


def mostrar_pie_streamlit(pie):
    """Muestra el pie DEBAJO de la figura en la app, con st.caption/st.markdown -- nunca
    como anotación de Plotly (principio de diseño: figura y texto son cosas separadas)."""
    st.caption(pie["descripcion"])
    if pie["notas"]:
        st.markdown(f"**{pie.get('titulo_notas', 'Notas:')}**\n" + "\n".join(f"- {n}" for n in pie["notas"]))
    if pie["extra"]:
        st.caption(pie["extra"])


_FUENTE_PIE_PNG_CACHE = {}


def _fuente_pie_png(tam_px):
    """Fuente TTF real para componer el pie en los PNG descargables (el bitmap por
    defecto de PIL es ilegible a cualquier tamaño). Reutiliza la DejaVu Sans que ya trae
    matplotlib -- ya es dependencia de la app, no se agrega ninguna nueva."""
    if tam_px not in _FUENTE_PIE_PNG_CACHE:
        import matplotlib.font_manager as fm
        ruta = fm.findfont("DejaVu Sans")
        _FUENTE_PIE_PNG_CACHE[tam_px] = ImageFont.truetype(ruta, tam_px)
    return _FUENTE_PIE_PNG_CACHE[tam_px]


def componer_png_con_pie(png_bytes, pie, scale=3):
    """Compone el PNG final para descarga: la figura de Plotly (limpia, sin pie
    incrustado) arriba, y el pie como una franja blanca debajo, con texto envuelto a
    líneas, alineado a la izquierda, fuente >= 11pt (proporcional a `scale`, igual que el
    resto de la figura, para que no quede diminuta en la imagen de alta resolución)."""
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    ancho = img.width
    tam_fuente = max(int(15 * scale), 14)
    interlineado = int(tam_fuente * 1.5)
    margen = int(14 * scale)
    fuente = _fuente_pie_png(tam_fuente)

    draw_tmp = ImageDraw.Draw(img)
    ancho_max_texto = ancho - 2 * margen

    def envolver(texto):
        palabras = texto.split(" ")
        actual, salida = "", []
        for palabra in palabras:
            prueba = (actual + " " + palabra).strip()
            if not actual or draw_tmp.textlength(prueba, font=fuente) <= ancho_max_texto:
                actual = prueba
            else:
                salida.append(actual)
                actual = palabra
        if actual:
            salida.append(actual)
        return salida or [""]

    lineas_fisicas = [fisica for logica in pie_a_lineas_texto(pie) for fisica in envolver(logica)]

    alto_pie = margen * 2 + interlineado * len(lineas_fisicas)
    lienzo = Image.new("RGB", (ancho, img.height + alto_pie), "white")
    lienzo.paste(img, (0, 0))
    draw = ImageDraw.Draw(lienzo)
    y = img.height + margen
    for linea in lineas_fisicas:
        draw.text((margen, y), linea, font=fuente, fill=(60, 56, 50))
        y += interlineado

    buf = io.BytesIO()
    lienzo.save(buf, format="PNG")
    return buf.getvalue()


def formatear_p(p):
    """Evita el 'p = 0.0000' enganoso: por debajo de 0.0001 se reporta como cota superior."""
    if p < 0.0001:
        return "p < 0.0001"
    return f"p = {p:.4f}"


# Paleta Okabe-Ito (distinguible para las formas mas comunes de daltonismo) para los 3
# modelos de crecimiento, combinada con un tipo de linea distinto por modelo para que
# tambien se distingan en blanco y negro (no dependen solo del color).
MODELO_ESTILO = {
    "Exponencial": {"color": "#0072B2", "dash": "dot"},
    "Logístico":   {"color": "#E69F00", "dash": "dash"},
    "Gompertz":    {"color": "#009E73", "dash": "solid"},
}



def texto_significancia(p):
    """Asteriscos de significancia (convencion estandar): ns, *, **, ***."""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def agregar_pie_figura(fig, lineas, altura_linea_px=17, espacio_eje_x_px=70):
    """Agrega una o mas lineas de texto como pie de figura, debajo del título del eje X, y
    expande el margen inferior para que quepan. Las anotaciones usan yref="paper", que es
    relativo al ALTO DEL ÁREA DE TRAZADO (no de la figura completa) -- por eso la posición de
    cada línea se calcula en píxeles reales y se convierte a fracción usando el alto de
    trazado resultante, en vez de una fracción fija que se desalinea según cuántas líneas
    tenga el pie o cuánto margen ya tuviera la figura (con muchas líneas, una fracción fija
    dejaba el texto encimado con el título del eje X)."""
    margen = fig.layout.margin
    alto_total = fig.layout.height or 450
    margen_t = margen.t if margen and margen.t is not None else 70
    margen_b_actual = margen.b if margen and margen.b is not None else 70
    margen_b_nuevo = margen_b_actual + espacio_eje_x_px + altura_linea_px * len(lineas) + 12
    alto_trazado = max(alto_total - margen_t - margen_b_nuevo, 50)
    for i, linea in enumerate(lineas):
        y_px = espacio_eje_x_px + i * altura_linea_px
        fig.add_annotation(
            text=linea, xref="paper", yref="paper", x=0, y=-(y_px / alto_trazado),
            showarrow=False, align="left", xanchor="left", yanchor="top",
            font=dict(family=FUENTE_PUBLICACION, size=10.5, color=T["INK_MUTED"]),
        )
    fig.update_layout(margin=dict(b=margen_b_nuevo))
    return fig


# ==============================================================================
# 1. MODELOS MATEMÁTICOS
# ==============================================================================
def modelo_exponencial(t, P0, r):
    return P0 * np.exp(r * t)

def modelo_logistico(t, K, k, Ti):
    return K / (1 + np.exp(-k * (t - Ti)))

def modelo_gompertz(t, K, k, Ti):
    return K * np.exp(-np.exp(-k * (t - Ti)))

MODELOS = {
    "Exponencial": {"func": modelo_exponencial, "nombres_param": ["P0", "r"]},
    "Logístico":   {"func": modelo_logistico,   "nombres_param": ["K", "k", "Ti"]},
    "Gompertz":    {"func": modelo_gompertz,    "nombres_param": ["K", "k", "Ti"]},
}

TEXTOS_MODELOS = {
    "Exponencial": {
        "num": "01", "ecuacion": r"P(t) = P_0 \cdot e^{r \cdot t}",
        "parametros": [("P0", "Valor inicial de la variable en t = 0 (altura o biomasa al trasplante)."),
                       ("r", "Tasa de crecimiento relativo (día⁻¹): qué tan rápido crece la planta en proporción a su tamaño actual.")],
        "supuesto": "Crecimiento a tasa constante proporcional al tamaño, sin límite superior. El modelo más simple de los tres.",
        "cuando_usar": "Como línea base de comparación y para describir la fase inicial (primeras semanas), antes de que aparezcan limitaciones de recursos, luz o espacio.",
        "limitacion": "No es realista a largo plazo: ninguna planta crece de forma indefinida. Suele ajustar peor en el rango completo de 0 a 120 días.",
    },
    "Logístico": {
        "num": "02", "ecuacion": r"P(t) = \dfrac{K}{1 + e^{-k (t - T_i)}}",
        "parametros": [("K", "Capacidad de carga: valor máximo asintótico que alcanza la planta."),
                       ("k", "Tasa de crecimiento: qué tan rápido se acerca la curva a K."),
                       ("Ti", "Punto de inflexión: momento donde el crecimiento pasa de acelerar a desacelerar.")],
        "supuesto": "Curva en forma de S simétrica: aceleración y desaceleración ocurren con la misma velocidad relativa alrededor de Ti.",
        "cuando_usar": "Modelo clásico de crecimiento poblacional/vegetal cuando se espera que la desaceleración sea simétrica a la aceleración inicial.",
        "limitacion": "La simetría puede no representar bien casos donde la planta tarda mucho más en frenar de lo que tardó en acelerar.",
    },
    "Gompertz": {
        "num": "03", "ecuacion": r"P(t) = K \cdot e^{-e^{-k (t - T_i)}}",
        "parametros": [("K", "Capacidad de carga: valor máximo asintótico."),
                       ("k", "Tasa de crecimiento."),
                       ("Ti", "Punto de inflexión de la curva.")],
        "supuesto": "Curva en S asimétrica: la desaceleración hacia K es más lenta y gradual que la aceleración inicial.",
        "cuando_usar": "Muy usado en fisiología vegetal: suele ajustar mejor cuando la fase de freno se prolonga más que la fase de arranque, algo común en vivero.",
        "limitacion": "Su asimetría implícita puede volverse menos estable que el logístico cuando el dataset tiene muy pocos puntos.",
    },
}


# ==============================================================================
# 2. DATOS — ahora con RÉPLICAS por día: DATOS[variable][grupo][dia] = array
# ==============================================================================
@st.cache_data
def generar_datos(semilla: int):
    rng = np.random.default_rng(semilla)

    def simular(func, params_reales, ruido_rel):
        y_medio = func(DIAS, *params_reales)
        datos_dia = {}
        for i, dia in enumerate(DIAS):
            ruido = rng.normal(1.0, ruido_rel, size=N_REPLICAS)
            datos_dia[int(dia)] = np.clip(y_medio[i] * ruido, 0.01, None)
        return datos_dia

    var = rng.uniform(0.85, 1.15, size=20)
    datos = {
        "altura": {
            "-M": simular(modelo_logistico, [45*var[0], 0.05*var[1], 40], 0.08),
            "+M": simular(modelo_logistico, [60*var[2], 0.055*var[3], 38], 0.08),
        },
        "biomasa": {
            "-M": simular(modelo_gompertz, [6.5*var[4], 0.030*var[5], 55], 0.12),
            "+M": simular(modelo_gompertz, [10.0*var[6], 0.032*var[7], 50], 0.12),
        },
        "diametro": {
            "-M": simular(modelo_logistico, [4.2*var[8], 0.05*var[9], 42], 0.07),
            "+M": simular(modelo_logistico, [5.8*var[10], 0.055*var[11], 38], 0.07),
        },
        "hojas": {
            "-M": simular(modelo_logistico, [14*var[12], 0.045*var[13], 45], 0.10),
            "+M": simular(modelo_logistico, [19*var[14], 0.050*var[15], 40], 0.10),
        },
        "area_foliar": {
            "-M": simular(modelo_logistico, [160*var[16], 0.045*var[17], 55], 0.10),
            "+M": simular(modelo_logistico, [700*var[18], 0.050*var[19], 50], 0.10),
        },
    }
    # El numero de hojas es un conteo (entero) -- redondear conservando el minimo de 1
    for grupo in datos["hojas"]:
        for dia in datos["hojas"][grupo]:
            datos["hojas"][grupo][dia] = np.clip(np.round(datos["hojas"][grupo][dia]), 1, None)
    return datos


def dias_disponibles(datos_var_grupo):
    return sorted(datos_var_grupo.keys())

def flatten_replicas(datos_var_grupo):
    """De {dia: [valores...]} a arrays planos (t, y) para curve_fit."""
    t_flat, y_flat = [], []
    for dia in sorted(datos_var_grupo.keys()):
        for v in datos_var_grupo[dia]:
            t_flat.append(dia)
            y_flat.append(v)
    return np.array(t_flat, dtype=float), np.array(y_flat, dtype=float)

def media_sd_por_dia(datos_var_grupo):
    dias = dias_disponibles(datos_var_grupo)
    medias = np.array([np.mean(datos_var_grupo[d]) for d in dias])
    sds = np.array([np.std(datos_var_grupo[d], ddof=1) if len(datos_var_grupo[d]) > 1 else 0.0 for d in dias])
    ns = np.array([len(datos_var_grupo[d]) for d in dias])
    return np.array(dias, dtype=float), medias, sds, ns


def calcular_r2(y_obs, y_pred):
    ss_res = np.sum((y_obs - y_pred) ** 2)
    ss_tot = np.sum((y_obs - np.mean(y_obs)) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

def calcular_rmse(y_obs, y_pred):
    return np.sqrt(np.mean((y_obs - y_pred) ** 2))

def calcular_mae(y_obs, y_pred):
    return np.mean(np.abs(y_obs - y_pred))

P0_INICIAL = {
    "Exponencial": lambda y: [max(y[0], 0.1), 0.02],
    "Logístico":   lambda y: [max(y) * 1.3, 0.05, 50],
    "Gompertz":    lambda y: [max(y) * 1.3, 0.03, 50],
}

@st.cache_data
def ajustar_todos_los_modelos(datos):
    resultados = {}
    for variable, grupos in datos.items():
        resultados[variable] = {}
        for grupo, datos_dia in grupos.items():
            resultados[variable][grupo] = {}
            t_flat, y_flat = flatten_replicas(datos_dia)
            _, medias_dia, _, _ = media_sd_por_dia(datos_dia)
            dias_unicos = len(set(t_flat.tolist()))
            for nombre_modelo, info in MODELOS.items():
                func = info["func"]
                n_params = len(info["nombres_param"])
                if dias_unicos < n_params:
                    # No hay suficientes dias distintos para identificar el modelo:
                    # un ajuste aqui daria parametros/R2 sin sentido (no es un error
                    # de la app, es una limitacion matematica real de los datos).
                    resultados[variable][grupo][nombre_modelo] = {
                        "params": None, "pcov": None, "r2": None, "rmse": None, "mae": None,
                        "error_std": None, "ci_bajo": None, "ci_alto": None,
                        "residuos": None, "t_flat": t_flat,
                        "insuficiente": True, "dias_disponibles": dias_unicos, "dias_requeridos": n_params,
                    }
                    continue
                p0 = P0_INICIAL[nombre_modelo](medias_dia)
                try:
                    popt, pcov = curve_fit(func, t_flat, y_flat, p0=p0, maxfev=20000)
                    y_pred_flat = func(t_flat, *popt)
                    r2 = calcular_r2(y_flat, y_pred_flat)
                    rmse = calcular_rmse(y_flat, y_pred_flat)
                    mae = calcular_mae(y_flat, y_pred_flat)
                    n = len(y_flat)
                    gl = max(n - n_params, 1)
                    error_std = np.sqrt(np.diag(pcov))
                    t_critico = t_dist.ppf(0.975, gl)
                    ci_bajo = popt - t_critico * error_std
                    ci_alto = popt + t_critico * error_std
                    residuos = y_flat - y_pred_flat
                except RuntimeError:
                    popt, pcov, r2, rmse, mae = None, None, np.nan, np.nan, np.nan
                    error_std = ci_bajo = ci_alto = residuos = None
                resultados[variable][grupo][nombre_modelo] = {
                    "params": popt, "pcov": pcov, "r2": r2, "rmse": rmse, "mae": mae,
                    "error_std": error_std, "ci_bajo": ci_bajo, "ci_alto": ci_alto,
                    "residuos": residuos, "t_flat": t_flat, "insuficiente": False,
                }
    return resultados


def prueba_t_independiente(datos, variable, dia):
    """Prueba t de dos muestras independientes (Welch) entre −M y +M en un
    día concreto, usando las réplicas reales de ese día — ahora sí es una
    prueba t propiamente dicha, no una aproximación."""
    y_control = np.asarray(datos[variable]["-M"].get(dia, []))
    y_tratado = np.asarray(datos[variable]["+M"].get(dia, []))
    if len(y_control) < 2 or len(y_tratado) < 2:
        return None
    estadistico, valor_p = ttest_ind(y_tratado, y_control, equal_var=False)
    return {
        "t": estadistico, "p": valor_p, "significativo": valor_p < 0.05,
        "media_control": np.mean(y_control), "sd_control": np.std(y_control, ddof=1),
        "media_tratado": np.mean(y_tratado), "sd_tratado": np.std(y_tratado, ddof=1),
        "n_control": len(y_control), "n_tratado": len(y_tratado),
    }


NOTA_NO_CONVERGENCIA_K = (
    "Cuando Logístico o Gompertz no convergen con estos datos, la causa más probable es que la "
    "ventana de muestreo disponible no alcance a capturar la fase de desaceleración necesaria para "
    "estimar la capacidad de carga (K) de una curva en forma de S."
)

# ==============================================================================
# VOCABULARIO ÚNICO DE ESTADO — antes convivían "Sin ajuste"/"No convergió" para el
# MISMO caso (curve_fit lanzó RuntimeError) y "Sin suficientes días"/"Sin días
# suficientes"/"Sin sufic. dias" para el caso de días insuficientes, con distinta
# redacción en la app y el PDF. Estas constantes son la única fuente de verdad para
# los 3 estados posibles de un ajuste (no cambian la regla, solo cómo se nombra):
#   - ESTADO_OK: el modelo convergió y tiene R².
#   - ESTADO_NO_CONVERGIO: había días suficientes pero curve_fit no encontró solución.
#   - ESTADO_SIN_DIAS: no hay suficientes días distintos para ese modelo (nunca se
#     intenta el ajuste; es una limitación matemática de los datos, no un fallo).
# ==============================================================================
ESTADO_OK = "OK"
ESTADO_NO_CONVERGIO = "No convergió"
ESTADO_SIN_DIAS = "Sin días suficientes"


def texto_estado_sin_dias(dias_disponibles, dias_requeridos):
    return f"{ESTADO_SIN_DIAS} ({dias_disponibles}/{dias_requeridos})"


def estado_de_ajuste(res):
    """Determina el estado (ESTADO_OK / ESTADO_NO_CONVERGIO / texto_estado_sin_dias) de un
    resultado de `ajustar_todos_los_modelos`, sin recalcular ni reinterpretar la regla de
    insuficiente/no convergió que ya define esa función -- solo nombra el mismo caso siempre
    de la misma forma en toda la app y el PDF."""
    if res.get("insuficiente"):
        return texto_estado_sin_dias(res["dias_disponibles"], res["dias_requeridos"])
    r2 = res["r2"]
    r2_ok = r2 is not None and not (isinstance(r2, float) and np.isnan(r2))
    return ESTADO_OK if r2_ok else ESTADO_NO_CONVERGIO


def calcular_tabla_modelo(RES, datos, variable, modelos):
    """Para una variable: por cada grupo (-M/+M), arma las filas Grupo/Modelo/R2/RMSE/MAE con una
    nota corta cuando el modelo no pudo ajustarse, y determina el modelo con mejor R2 de entre los
    que sí ajustaron. No recalcula nada: solo lee los resultados que ya produjo
    `ajustar_todos_los_modelos` (misma regla de insuficiente/no convergió, sin tocarla)."""
    filas = []
    mejores = {}
    for grupo in datos[variable]:
        validos = []
        for m in modelos:
            r2 = RES[variable][grupo][m]["r2"]
            if r2 is not None and not (isinstance(r2, float) and np.isnan(r2)):
                validos.append((m, r2))
        mejores[grupo] = max(validos, key=lambda x: x[1])[0] if validos else None
        for m in modelos:
            res = RES[variable][grupo][m]
            r2, rmse, mae = res["r2"], res["rmse"], res.get("mae")
            r2_ok = r2 is not None and not (isinstance(r2, float) and np.isnan(r2))
            estado = estado_de_ajuste(res)
            nota = "" if estado == ESTADO_OK else estado
            filas.append({
                "grupo": grupo, "modelo": m,
                "r2": round(r2, 4) if r2_ok else None,
                "rmse": round(rmse, 4) if rmse is not None and not (isinstance(rmse, float) and np.isnan(rmse)) else None,
                "mae": round(mae, 4) if mae is not None and not (isinstance(mae, float) and np.isnan(mae)) else None,
                "mejor": m == mejores[grupo],
                "nota": nota,
            })
    return filas, mejores


def calcular_efecto_micorriza(datos, variable):
    """Por cada día con réplicas en ambos grupos, calcula el % de incremento de +M sobre -M y la
    prueba t de Welch entre grupos, reutilizando `prueba_t_independiente` (misma prueba que ya usa
    la sección Estadística, sin duplicar su lógica)."""
    filas = []
    dias = sorted(set(datos[variable]["-M"].keys()) & set(datos[variable]["+M"].keys()))
    for dia in dias:
        t_res = prueba_t_independiente(datos, variable, dia)
        if t_res is None:
            continue
        incremento_pct = ((t_res["media_tratado"] - t_res["media_control"]) / t_res["media_control"] * 100
                           if t_res["media_control"] != 0 else float("nan"))
        filas.append({"dia": dia, "incremento_pct": incremento_pct, **t_res})
    return filas


def texto_interpretativo_efecto(variable, fila):
    dia = int(fila["dia"])
    inc = fila["incremento_pct"]
    direccion = "superó a" if inc >= 0 else "fue menor que"
    signif = "significativo" if fila["significativo"] else "no significativo"
    return (f"A los {dia} ddt, {NOMBRE_VARIABLE[variable].lower()} de +M {direccion} -M en "
            f"{abs(inc):.1f}% ({formatear_p(fila['p'])}, {signif}).")


def titulo_barras_significancia(datos, variable, filas=None):
    """Título-conclusión de las barras: en cuántas fechas +M supera a −M de forma significativa
    (misma prueba t de Welch que usa toda la app, vía calcular_efecto_micorriza) y cómo termina."""
    nombre = NOMBRE_VARIABLE[variable]
    if filas is None:
        filas = calcular_efecto_micorriza(datos, variable) if {"-M", "+M"} <= set(datos[variable]) else []
    if not filas:
        return f"{nombre}: media ± DE por día"
    sig_pos = [f for f in filas if f["significativo"] and f["incremento_pct"] > 0]
    sig_neg = [f for f in filas if f["significativo"] and f["incremento_pct"] < 0]
    ult = filas[-1]
    final = (f"al final, {_fmt_signo(ult['incremento_pct'], 0)} % "
             f"({'significativo' if ult['significativo'] else 'no significativo'})")
    if sig_pos:
        return (f"{nombre}: +M supera a −M de forma significativa en {len(sig_pos)} de {len(filas)} fechas; "
                f"{final}")
    if sig_neg:
        return f"{nombre}: +M queda por debajo de −M en {len(sig_neg)} de {len(filas)} fechas; {final}"
    return f"{nombre}: sin diferencias significativas entre +M y −M; {final}"


def fig_barras_variable(datos, variable, fuente_datos="simulado"):
    """Barras −M vs +M por día, diseñadas para leerse solas:
    - barra = promedio del día (color sólido por grupo, sin tramas) y ± DE;
    - un círculo por cada planta medida, encima de su barra (se ve la variación real);
    - sobre cada día, un corchete con cuánto más crece +M que −M, la significancia de la
      prueba t de Welch ya existente (prueba_t_independiente) y los promedios −M → +M;
      en tinta si es significativa y en gris si no;
    - leyenda escrita arriba y título con la conclusión."""
    unidad = UNIDADES[variable]
    grupos = [g for g in ("-M", "+M") if g in datos[variable]]
    dias = sorted(set().union(*[set(datos[variable][g]) for g in grupos]))
    x = np.arange(len(dias), dtype=float)
    denso = len(dias) > 6
    ancho = 0.36
    fig = go.Figure()
    rng = np.random.default_rng(3)
    techo = 0.0
    n_replicas_vistas = set()
    for k, g in enumerate(grupos):
        desplaz = (k - (len(grupos) - 1) / 2) * ancho * 1.08
        dias_g, medias, sds, ns = media_sd_por_dia(datos[variable][g])
        n_replicas_vistas.update(int(n) for n in ns)
        xs = np.array([x[dias.index(d)] for d in dias_g]) + desplaz
        techo = max(techo, float(np.max(medias + sds)),
                    max(float(np.max(datos[variable][g][d])) for d in dias_g))
        fig.add_trace(go.Bar(
            x=xs, y=medias, width=ancho, name=f"{texto_grupo(g)} · {NOMBRE_GRUPO[g]}",
            marker=dict(color=COLOR_GRUPO[g], opacity=0.9, line_width=0, cornerradius=4),
            error_y=dict(type="data", array=sds, color=G_INK, thickness=1.2, width=0),
            customdata=dias_g,
            hovertemplate=f"{texto_grupo(g)} · día %{{customdata:.0f}}<br>promedio %{{y:.3g}} {unidad}<extra></extra>"))
        px, py = [], []
        for xi, d in zip(xs, dias_g):
            v = np.asarray(datos[variable][g][d], dtype=float)
            px += list(xi + rng.uniform(-ancho * 0.28, ancho * 0.28, len(v)))
            py += list(v)
        fig.add_trace(go.Scatter(x=px, y=py, mode="markers", showlegend=False, hoverinfo="skip",
                                 marker=dict(size=5 if denso else 6, color="white", line=dict(color=G_INK, width=1))))

    filas = calcular_efecto_micorriza(datos, variable) if len(grupos) == 2 else []
    techo = techo if techo > 0 else 1.0
    for f in filas:
        i = dias.index(f["dia"])
        a, b = np.asarray(datos[variable]["-M"][f["dia"]]), np.asarray(datos[variable]["+M"][f["dia"]])
        y_c = max(f["media_control"] + f["sd_control"], f["media_tratado"] + f["sd_tratado"],
                  float(a.max()), float(b.max())) + techo * 0.05
        x0, x1 = x[i] - ancho * 0.54, x[i] + ancho * 0.54
        sig = f["significativo"]
        color = G_INK if sig else G_MUTED
        fig.add_shape(type="path", line=dict(color=color, width=1.3),
                      path=f"M {x0},{y_c - techo * 0.02} L {x0},{y_c} L {x1},{y_c} L {x1},{y_c - techo * 0.02}")
        efecto = _fmt_signo(f["incremento_pct"], 0)
        estrellas = texto_significancia(f["p"])
        if denso:
            texto = f"<b>{efecto}%</b><br>{estrellas}" if sig else f"{efecto}%<br>ns"
        else:
            texto = (f"<b>{efecto} %</b> {estrellas}" if sig else f"{efecto} % · ns") + (
                f"<br><span style='font-size:11px;color:{G_MUTED}'>"
                f"{f['media_control']:.3g} → {f['media_tratado']:.3g} {unidad}</span>")
        fig.add_annotation(x=x[i], y=y_c, yanchor="bottom", showarrow=False, text=texto,
                           font=dict(family=FUENTE_PUBLICACION, size=(10.5 if denso else 13) if sig else
                                     (10 if denso else 12), color=color))

    # Leyenda escrita arriba a la izquierda (en vez de una caja de leyenda aparte)
    for k, g in enumerate(grupos):
        fig.add_annotation(xref="paper", yref="paper", x=k * 0.24, y=1.04, xanchor="left", yanchor="bottom",
                           showarrow=False, text=f"<span style='color:{COLOR_GRUPO[g]}'>■</span> "
                                                 f"{texto_grupo(g)} · {NOMBRE_GRUPO[g]}",
                           font=dict(family=FUENTE_PUBLICACION, size=13, color=G_INK))
    fig.update_xaxes(tickvals=x, ticktext=[f"Día {d:g}" for d in dias], title_text="Días después del trasplante",
                     ticks="", range=[-0.6, len(dias) - 0.4])
    fig.update_yaxes(title_text=f"{NOMBRE_VARIABLE[variable]} ({unidad})", range=[0, techo * 1.36])
    estilo_publicacion(
        fig, width=1100, height=580, titulo=titulo_barras_significancia(datos, variable, filas),
        mostrar_leyenda=False, left_margin=75,
        subtitulo="Barra = promedio · círculos = cada planta · línea = ± DE<br>Arriba de cada día: cuánto más crece "
                  "+M que −M, la prueba t y los promedios (−M → +M) · ns = sin diferencia · * p < 0.05 · "
                  "** p < 0.01 · *** p < 0.001")
    fig.update_layout(margin=dict(t=fig.layout.margin.t + 12))

    n_reps_txt = "/".join(str(n) for n in sorted(n_replicas_vistas)) if n_replicas_vistas else "?"
    descripcion = (
        f"{NOMBRE_VARIABLE[variable]} ({unidad}): barra = promedio y línea = ± DE de n = {n_reps_txt} plantas por "
        "día y grupo; círculos = cada planta. Sobre cada día: % de incremento de +M sobre −M y prueba t de Welch "
        "(ns = p ≥ 0.05 · * p < 0.05 · ** p < 0.01 · *** p < 0.001)."
    )
    extra = ("Réplicas sintéticas generadas a partir de medias y CV% publicados (Aguirre-Medina et al., 2023)."
             if fuente_datos == "real" else None)
    return fig, construir_pie(descripcion, extra=extra)


def fig_resumen_efecto_final(datos, variables, fuente_datos="simulado"):
    """Resumen en una sola gráfica: cuánto más crece +M que −M en el ÚLTIMO día común de cada
    variable (barra horizontal = % de incremento, línea = IC 95 % por bootstrap de las réplicas),
    color fuerte si la prueba t de Welch es significativa y claro si no, con los promedios
    escritos al lado. Devuelve (None, motivo) si ninguna variable tiene −M y +M comparables."""
    filas = []
    for v in variables:
        if not {"-M", "+M"} <= set(datos[v]):
            continue
        comunes = sorted(set(datos[v]["-M"]) & set(datos[v]["+M"]))
        if not comunes:
            continue
        d = comunes[-1]
        t_res = prueba_t_independiente(datos, v, d)
        a, b = np.asarray(datos[v]["-M"][d], dtype=float), np.asarray(datos[v]["+M"][d], dtype=float)
        if t_res is None or a.mean() == 0:
            continue
        inc = (b.mean() - a.mean()) / a.mean() * 100
        rng = np.random.default_rng(1)
        boot = np.array([(rng.choice(b, len(b)).mean() / rng.choice(a, len(a)).mean() - 1) * 100
                         for _ in range(4000)])
        lo, hi = np.percentile(boot[np.isfinite(boot)], [2.5, 97.5])
        filas.append(dict(nombre=NOMBRE_VARIABLE[v], inc=inc, lo=lo, hi=hi, p=t_res["p"],
                          sig=t_res["significativo"], dia=d, ma=a.mean(), mb=b.mean(), u=UNIDADES[v]))
    if not filas:
        return None, "Ninguna variable tiene −M y +M con réplicas en un mismo día para comparar."
    filas.sort(key=lambda f: f["inc"])
    color_claro = "#D9C6BF"
    fig = go.Figure()
    for f in filas:
        fig.add_trace(go.Bar(
            y=[f["nombre"]], x=[f["inc"]], orientation="h", width=0.55, showlegend=False,
            marker=dict(color=T["ACCENT"] if f["sig"] else color_claro, cornerradius=4),
            error_x=dict(type="data", symmetric=False, array=[f["hi"] - f["inc"]], arrayminus=[f["inc"] - f["lo"]],
                         color=G_INK, thickness=1.2, width=5),
            hovertemplate=f"{f['nombre']}: %{{x:+.1f}} %<extra></extra>"))
        fig.add_annotation(
            y=f["nombre"], x=max(f["hi"], f["inc"], 0), xshift=10, xanchor="left", showarrow=False, align="left",
            text=(f"<b>{_fmt_signo(f['inc'], 0)} %</b> {texto_significancia(f['p'])}<br>"
                  f"<span style='font-size:11px;color:{G_MUTED}'>{f['ma']:.3g} → {f['mb']:.3g} {f['u']} "
                  f"(día {f['dia']:g})</span>"),
            font=dict(family=FUENTE_PUBLICACION, size=13, color=G_INK if f["sig"] else G_MUTED))
    fig.add_vline(x=0, line=dict(color=G_INK, width=1))
    x_min = min(0.0, min(f["lo"] for f in filas)) - 5
    x_max = max(max(f["hi"] for f in filas), 5) * 1.4
    fig.update_xaxes(ticksuffix=" %", range=[x_min, x_max], showgrid=True, gridcolor=G_GRID,
                     title_text="Cuánto más crece +M que −M al final del ensayo")
    fig.update_yaxes(showgrid=False, tickfont=dict(family=FUENTE_PUBLICACION, size=14, color=G_INK))
    n_sig = sum(f["sig"] and f["inc"] > 0 for f in filas)
    titulo = (f"Al final del ensayo, la micorriza aumenta {n_sig} de {len(filas)} variables de forma significativa"
              if n_sig else "Al final del ensayo, la micorriza no aumenta ninguna variable de forma significativa")
    estilo_publicacion(fig, width=1100, height=max(320, 150 + 85 * len(filas)), titulo=titulo,
                       mostrar_leyenda=False, left_margin=150,
                       subtitulo="Barra = % de incremento de +M sobre −M el último día · línea = IC 95 % · "
                                 "color fuerte = diferencia significativa (prueba t), claro = no significativa")
    fig.update_yaxes(showgrid=False)
    extra = ("Réplicas sintéticas generadas a partir de medias y CV% publicados (Aguirre-Medina et al., 2023)."
             if fuente_datos == "real" else None)
    pie = construir_pie(
        "% de incremento de +M sobre −M en el último día con datos de ambos grupos, por variable. Línea = IC 95 % "
        "por remuestreo (bootstrap) de las réplicas. Significancia: prueba t de Welch (ns = p ≥ 0.05 · * p < 0.05 · "
        "** p < 0.01 · *** p < 0.001).", extra=extra)
    return fig, pie


def fig_barras_r2_comparacion(RES, datos, variables, modelos):
    """R² de cada modelo como tabla de calor (filas = variable · grupo, columnas = modelo): más
    oscuro = mejor ajuste, ★ = mejor modelo de la fila y el estado escrito en la celda cuando el
    modelo no convergió o no tuvo días suficientes. Mucho más fácil de comparar que barras de
    0.88 frente a 0.91."""
    filas_txt, z, texto = [], [], []
    ganadores = []
    for variable in variables:
        _, mejores = calcular_tabla_modelo(RES, datos, variable, modelos)
        for grupo in [g for g in ("-M", "+M") if g in datos[variable]]:
            fila_z, fila_t = [], []
            for m in modelos:
                res = RES[variable][grupo][m]
                r2 = res["r2"]
                if res.get("insuficiente"):
                    fila_z.append(None)
                    fila_t.append(f"—<br><span style='font-size:10px'>{ESTADO_SIN_DIAS.lower()}</span>")
                elif r2 is None or (isinstance(r2, float) and np.isnan(r2)):
                    fila_z.append(None)
                    fila_t.append(f"—<br><span style='font-size:10px'>{ESTADO_NO_CONVERGIO.lower()}</span>")
                else:
                    fila_z.append(float(r2))
                    fila_t.append(f"★ <b>{r2:.3f}</b>" if m == mejores[grupo] else f"{r2:.3f}")
            if mejores[grupo]:
                ganadores.append(mejores[grupo])
            filas_txt.append(f"{NOMBRE_VARIABLE[variable]} · {texto_grupo(grupo)}")
            z.append(fila_z)
            texto.append(fila_t)
    validos = [v for fila in z for v in fila if v is not None]
    z_min = min(0.8, np.floor(min(validos) * 20) / 20) if validos else 0.8
    fig = go.Figure(go.Heatmap(
        z=z, x=modelos, y=filas_txt, text=texto, texttemplate="%{text}", xgap=4, ygap=4,
        colorscale=[[0, "#F7EFE9"], [0.5, "#D9A08C"], [1, "#8E3520"]], zmin=z_min, zmax=1,
        colorbar=dict(title=dict(text="R²", font=dict(color=G_MUTED)), thickness=12, len=0.8,
                      tickfont=dict(color=G_MUTED)),
        textfont=dict(family=FUENTE_PUBLICACION, size=14),
        hovertemplate="%{y} · %{x}<br>R² = %{z:.3f}<extra></extra>"))
    if ganadores:
        top = max(set(ganadores), key=ganadores.count)
        titulo = f"{top} logra el mejor ajuste en {ganadores.count(top)} de {len(filas_txt)} casos"
    else:
        titulo = "Comparación de R² por modelo"
    estilo_publicacion(fig, width=1100, height=max(360, 170 + 62 * len(filas_txt)), titulo=titulo,
                       mostrar_leyenda=False, left_margin=180,
                       subtitulo=f"Cada celda = R² del modelo (1 = ajuste perfecto) · más oscuro = mejor · ★ = mejor "
                                 f"modelo de la fila · escala de color de {z_min:.2f} a 1")
    fig.update_xaxes(side="top", showline=False, showgrid=False, ticks="",
                     tickfont=dict(family=FUENTE_PUBLICACION, size=14, color=G_INK))
    fig.update_yaxes(autorange="reversed", showgrid=False, tickmode="array", tickvals=filas_txt,
                     ticktext=filas_txt, tickfont=dict(family=FUENTE_PUBLICACION, size=13, color=G_INK))
    pie = construir_pie(
        "R² de cada modelo (Exponencial, Logístico, Gompertz) por variable y grupo. ★ = mayor R² de la fila. "
        "Las celdas con «—» indican que el modelo no convergió o no tuvo días suficientes.")
    return fig, pie


def _asintota_k_plausible(res, y_max_obs_grupo, dia_min, dia_max):
    """Criterio de plausibilidad de K (versión endurecida): se dibuja la asíntota solo si
    se cumplen TODAS: (1) el modelo convergió, (2) R² >= 0.90, (3) K <= 1.5x el máximo
    observado en ese grupo/variable, y (4) el punto de inflexión Ti cae dentro del rango de
    días observados (o sea que los datos sí alcanzan a mostrar la desaceleración hacia K).
    Devuelve (dibujar, K, motivo). El Exponencial no tiene K y nunca llega a llamar esto
    (se filtra en el llamador por nombres_param)."""
    if res.get("insuficiente") or res["params"] is None:
        return False, None, "el modelo no convergió"
    r2 = res["r2"]
    if r2 is None or (isinstance(r2, float) and np.isnan(r2)):
        return False, None, "el modelo no convergió"
    K = res["params"][0]
    Ti = res["params"][2]
    if r2 < 0.90:
        return False, K, f"R²={r2:.3f} < 0.90"
    if y_max_obs_grupo > 0 and K > 1.5 * y_max_obs_grupo:
        return False, K, f"K={K:.1f} supera 1.5× el máximo observado ({y_max_obs_grupo:.1f})"
    if not (dia_min <= Ti <= dia_max):
        return False, K, (f"el punto de inflexión (Ti={Ti:.1f}) cae fuera de la ventana "
                           f"observada ({dia_min:.0f}–{dia_max:.0f} ddt)")
    return True, K, None


def titulo_efecto_final(datos, variable):
    """Título-conclusión de una figura −M vs +M: cuánto difiere +M de −M en el último día que
    comparten, con el resultado de la prueba t de Welch ya existente (prueba_t_independiente).
    Devuelve None si no hay dos grupos con un día en común."""
    if not {"-M", "+M"} <= set(datos[variable]):
        return None
    comunes = sorted(set(datos[variable]["-M"]) & set(datos[variable]["+M"]))
    if not comunes:
        return None
    dia = comunes[-1]
    m_c, m_t = np.mean(datos[variable]["-M"][dia]), np.mean(datos[variable]["+M"][dia])
    if m_c == 0:
        return None
    inc = (m_t - m_c) / m_c * 100
    nombre = NOMBRE_EN_FRASE.get(variable, NOMBRE_VARIABLE.get(variable, variable).lower())
    base = (f"Con micorriza (+M), {nombre} es {abs(inc):.0f} % {'mayor' if inc >= 0 else 'menor'} "
            f"que sin ella a los {int(dia)} días")
    t_res = prueba_t_independiente(datos, variable, dia)
    if t_res is None:
        return base
    if t_res["significativo"]:
        return f"{base} ({formatear_p(t_res['p'])})"
    return f"{base}, pero la diferencia no es significativa ({formatear_p(t_res['p'])})"


def _jitter(n, ancho=1.2, semilla=11):
    """Desplazamiento horizontal pequeño y reproducible para que las réplicas del mismo día no
    se tapen entre sí (solo visual: el hover muestra el día real)."""
    return np.random.default_rng(semilla).uniform(-ancho, ancho, n)


def fig_curvas_publicacion(datos, RES, variable, modelos, fuente_datos="simulado"):
    """Curvas de crecimiento: panel (a) = −M, panel (b) = +M, mismo eje Y.

    - Puntos claros = cada planta medida (réplicas); punto con barra = media ± DE del día.
    - Una línea por modelo convergido (color + tipo de línea por modelo, paleta Okabe-Ito),
      con su nombre y R² escritos al final de la línea (etiqueta directa, sin leyenda aparte).
      El mejor modelo (★, mayor R²) va más grueso y es el único con banda IC 95 %.
    - Del mejor modelo se anotan la asíntota K ("techo estimado") y el punto de inflexión
      ("día en que crece más rápido"), solo si K pasa el criterio de plausibilidad.
    - El título dice la conclusión (+M vs −M en el último día, con prueba t).
    Los modelos que no convergieron (o sin días suficientes) no se dibujan y se anotan en el pie.
    No cambia el ajuste ni la regla de insuficiente/no convergió: solo lee RES."""
    grupos = [g for g in ("-M", "+M") if g in datos[variable]]
    dias_todos = sorted(set().union(*[set(datos[variable][g].keys()) for g in grupos]))
    t_fino = np.linspace(dias_todos[0], dias_todos[-1], 300)
    unidad = UNIDADES[variable]

    todos_los_valores = [v for g in grupos for vals in datos[variable][g].values() for v in vals]
    y_obs_min, y_obs_max = min(todos_los_valores), max(todos_los_valores)
    dia_min, dia_max = dias_todos[0], dias_todos[-1]

    # Techo/piso del eje Y calculados ANTES de dibujar: deciden el rango final y si una banda
    # de confianza es "estable" (cabe en el rango visible) o se omite.
    rango_total = max(y_obs_max - y_obs_min, 1e-6)
    y_bottom_cap = min(0, y_obs_min) - 0.05 * rango_total
    y_top_cap = y_obs_max * 1.25

    fig = make_subplots(rows=1, cols=len(grupos), horizontal_spacing=0.13, shared_yaxes=True)

    notas = []
    ticks_x = dias_todos if len(dias_todos) <= 8 else None
    for col, grupo in enumerate(grupos, start=1):
        color_g = COLOR_GRUPO[grupo]
        xr, yr = _ref_ejes(col)
        y_max_obs_grupo = max(v for vals in datos[variable][grupo].values() for v in vals)
        t_flat, y_flat = flatten_replicas(datos[variable][grupo])
        fig.add_trace(go.Scatter(
            x=t_flat + _jitter(len(t_flat), ancho=max((dia_max - dia_min) / 100, 0.5)), y=y_flat,
            mode="markers", name="Planta medida", showlegend=False,
            marker=dict(size=6, color=color_g, opacity=0.28, line_width=0),
            customdata=t_flat, hovertemplate=f"Día %{{customdata:.0f}}<br>%{{y:.2f}} {unidad}<extra>planta</extra>",
        ), row=1, col=col)
        dias_g, medias_g, sds_g, _ = media_sd_por_dia(datos[variable][grupo])
        fig.add_trace(go.Scatter(
            x=dias_g, y=medias_g, mode="markers", name="Media ± DE", showlegend=False,
            error_y=dict(type="data", array=sds_g, color=color_g, thickness=1.4, width=0),
            marker=dict(size=9, color=color_g, line=dict(color="white", width=2)),
            hovertemplate=f"Día %{{x:.0f}}<br>media %{{y:.2f}} {unidad}<extra></extra>",
        ), row=1, col=col)

        # Modelos válidos y el mejor (mayor R²) de este grupo
        validos = {}
        for modelo in modelos:
            res = RES[variable][grupo][modelo]
            if res.get("insuficiente"):
                notas.append(f"{modelo} ({texto_grupo(grupo)}): sin suficientes días de muestreo "
                             f"({res['dias_disponibles']}/{res['dias_requeridos']}).")
                continue
            r2 = res["r2"]
            if res["params"] is None or r2 is None or (isinstance(r2, float) and np.isnan(r2)):
                notas.append(f"{modelo} ({texto_grupo(grupo)}): no convergió.")
                continue
            validos[modelo] = res
        mejor = max(validos, key=lambda m: validos[m]["r2"]) if validos else None

        etiquetas = []
        for modelo, res in validos.items():
            estilo = MODELO_ESTILO[modelo]
            func = MODELOS[modelo]["func"]
            es_mejor = modelo == mejor
            y_fino = func(t_fino, *res["params"])
            if es_mejor:
                tiene_k = MODELOS[modelo]["nombres_param"][0] == "K"
                dibujar_k, K, motivo_k = (_asintota_k_plausible(res, y_max_obs_grupo, dia_min, dia_max)
                                          if tiene_k else (True, None, None))
                banda_baja, banda_alta = calcular_banda_confianza(func, res["params"], res["pcov"], t_fino)
                if banda_baja is not None and tiene_k and not dibujar_k:
                    notas.append(f"{modelo} ({texto_grupo(grupo)}): ni la asíntota K ni la banda de confianza "
                                 f"se dibujan ({motivo_k}).")
                elif banda_baja is not None and (np.max(banda_alta) > 3 * y_top_cap
                                                 or np.min(banda_baja) < 3 * y_bottom_cap - 2 * rango_total):
                    notas.append(f"{modelo} ({texto_grupo(grupo)}): banda de confianza no se dibuja (la "
                                 "incertidumbre del ajuste excede varias veces el rango visible).")
                elif banda_baja is not None:
                    r_, g_, b_ = (int(estilo["color"][k:k + 2], 16) for k in (1, 3, 5))
                    alta = np.clip(banda_alta, y_bottom_cap, y_top_cap)
                    baja = np.clip(banda_baja, y_bottom_cap, y_top_cap)
                    fig.add_trace(go.Scatter(x=np.r_[t_fino, t_fino[::-1]], y=np.r_[alta, baja[::-1]],
                                             mode="lines", fill="toself", fillcolor=f"rgba({r_},{g_},{b_},0.16)",
                                             line_width=0, showlegend=False, hoverinfo="skip"), row=1, col=col)
                elif tiene_k and not dibujar_k:
                    notas.append(f"{modelo} ({texto_grupo(grupo)}): asíntota K no se dibuja ({motivo_k}).")

                if tiene_k and dibujar_k:
                    fig.add_hline(y=K, line=dict(color=G_MUTED, dash="dot", width=1), row=1, col=col)
                    fig.add_annotation(x=0.01, y=K, xref=f"{xr} domain", yref=yr, showarrow=False, xanchor="left",
                                       yanchor="bottom", text=f"K ≈ {K:.3g} {unidad} · techo estimado",
                                       font=dict(family=FUENTE_PUBLICACION, size=11, color=G_MUTED))
                    Ti = res["params"][2]
                    y_ti = float(func(Ti, *res["params"]))
                    fig.add_trace(go.Scatter(x=[Ti], y=[y_ti], mode="markers", showlegend=False,
                                             marker=dict(symbol="diamond", size=12, color="white",
                                                         line=dict(color=G_INK, width=2)),
                                             hovertemplate=f"Punto de inflexión: día {Ti:.0f}<extra></extra>"),
                                  row=1, col=col)
                    fig.add_annotation(x=Ti, y=y_ti, xref=xr, yref=yr, ax=-70, ay=-46, showarrow=True,
                                       arrowhead=0, arrowcolor=G_MUTED, arrowwidth=1, align="right",
                                       text=f"Día {Ti:.0f}: crece<br>más rápido",
                                       font=dict(family=FUENTE_PUBLICACION, size=11, color=G_INK))

            visible = np.where((y_fino > y_top_cap) | (y_fino < y_bottom_cap), np.nan, y_fino)
            fig.add_trace(go.Scatter(
                x=t_fino, y=visible, mode="lines", name=modelo, showlegend=False,
                line=dict(color=estilo["color"], dash=estilo["dash"], width=3 if es_mejor else 1.8),
                hovertemplate=f"{modelo}<br>Día %{{x:.0f}}: %{{y:.2f}} {unidad}<extra></extra>",
            ), row=1, col=col)
            if np.any(~np.isnan(visible)):
                k_ult = int(np.where(~np.isnan(visible))[0][-1])
                etiquetas.append((f"{'★ ' if es_mejor else ''}<b>{modelo}</b> R²={res['r2']:.3f}",
                                  t_fino[k_ult], visible[k_ult]))
        etiquetas_fin_de_linea(fig, col, etiquetas, (y_bottom_cap, y_top_cap))
        fig.update_xaxes(title_text="Días después del trasplante", row=1, col=col,
                         range=[dia_min - 0.03 * (dia_max - dia_min), dia_max + 0.03 * (dia_max - dia_min)],
                         **({"tickvals": ticks_x} if ticks_x else {}))
        if col == 1:
            fig.update_yaxes(title_text=f"{NOMBRE_VARIABLE[variable]} ({unidad})", row=1, col=col)

    # Eje Y limitado a ~1.25x el maximo observado (no a la curva/asintota ajustada): asi
    # ninguna curva ni asintota puede dominar la escala del panel.
    fig.update_yaxes(range=[y_bottom_cap, y_top_cap])
    titulo = titulo_efecto_final(datos, variable) or f"{NOMBRE_VARIABLE[variable]}: curvas de crecimiento ajustadas"
    estilo_publicacion(
        fig, width=1200, height=600, titulo=titulo, mostrar_leyenda=False, right_margin=185, left_margin=80,
        subtitulo="Puntos claros = cada planta medida · punto con barra = media ± DE · líneas = modelos ajustados "
                  "(★ = mejor ajuste; banda = IC 95 %)")
    for col, grupo in enumerate(grupos, start=1):
        ultimo = max(datos[variable][grupo])
        encabezado_panel(fig, col, f"<b>({'ab'[col - 1]}) {texto_grupo(grupo)}</b> · {NOMBRE_GRUPO[grupo]} — "
                                   f"media final {np.mean(datos[variable][grupo][ultimo]):.3g} {unidad}",
                         COLOR_GRUPO[grupo])

    descripcion = ("Puntos claros = réplicas individuales; punto con barra = media ± DE por día. Líneas = modelos "
                   "convergidos con su R² escrito al final; ★ = mejor R² del grupo (el único con banda IC 95 %). "
                   "Eje Y limitado a ~1.25× el máximo observado. Asíntota K (techo estimado) y punto de inflexión "
                   "(◇) del mejor modelo: solo si convergió, R² ≥ 0.90, K ≤ 1.5× el máximo observado y la "
                   "inflexión cae dentro de los días observados.")
    extra = ("Réplicas sintéticas generadas a partir de medias y CV% publicados (Aguirre-Medina et al., 2023)."
             if fuente_datos == "real" else None)
    return fig, construir_pie(descripcion, notas=notas, extra=extra)


def calcular_agr_rgr(modelo, params, t):
    """AGR (dP/dt) y RGR ((1/P)·dP/dt), calculados analíticamente a partir de las derivadas
    cerradas de cada modelo y de los parámetros que YA ajustó curve_fit -- no se reajusta ni
    se modifica el ajuste, solo se evalúan formulas conocidas en esos parámetros:
      Exponencial P=P0·e^(rt)      -> dP/dt = r·P            -> RGR = r (constante)
      Logístico  P=K/(1+e^-k(t-Ti)) -> dP/dt = k·P·(1-P/K)   -> RGR = k·(1-P/K)
      Gompertz   P=K·e^(-e^-k(t-Ti)) -> dP/dt = k·P·ln(K/P)  -> RGR = k·ln(K/P)
    """
    if modelo == "Exponencial":
        P0, r = params
        P = P0 * np.exp(r * t)
        rgr = np.full_like(t, r, dtype=float)
        agr = r * P
    elif modelo == "Logístico":
        K, k, Ti = params
        P = K / (1 + np.exp(-k * (t - Ti)))
        rgr = k * (1 - P / K)
        agr = P * rgr
    elif modelo == "Gompertz":
        K, k, Ti = params
        P = K * np.exp(-np.exp(-k * (t - Ti)))
        with np.errstate(divide="ignore", invalid="ignore"):
            rgr = k * np.log(K / P)
        agr = P * rgr
    else:
        raise ValueError(f"Modelo desconocido: {modelo}")
    return agr, rgr


def fig_tasas_crecimiento(datos, RES, variable, modelos, fuente_datos="simulado"):
    """AGR y RGR del modelo con MEJOR R² en cada grupo -- reutiliza calcular_tabla_modelo para
    decidir cuál es el mejor, sin duplicar ese criterio. Se marca el día de crecimiento más
    rápido (máximo de AGR) y el título lo compara entre grupos. Devuelve (fig, pie) o
    (None, motivo) si ningún grupo tiene un modelo convergido."""
    grupos = [g for g in ("-M", "+M") if g in datos[variable]]
    _, mejores = calcular_tabla_modelo(RES, datos, variable, modelos)
    grupos_validos = [g for g in grupos if mejores.get(g)]
    if not grupos_validos:
        return None, "Ningún modelo convergió en ningún grupo: no hay tasas de crecimiento que calcular."

    unidad = UNIDADES[variable]
    dias_todos = sorted(set().union(*[set(datos[variable][g].keys()) for g in grupos]))
    t_fino = np.linspace(dias_todos[0], dias_todos[-1], 300)
    n = len(grupos_validos)
    fig = make_subplots(rows=2, cols=n, horizontal_spacing=0.1, vertical_spacing=0.16, shared_xaxes=True)

    maximos = {}
    for col, grupo in enumerate(grupos_validos, start=1):
        modelo = mejores[grupo]
        estilo = MODELO_ESTILO[modelo]
        res = RES[variable][grupo][modelo]
        agr, rgr = calcular_agr_rgr(modelo, res["params"], t_fino)
        for fila, serie, u in ((1, agr, f"{unidad}/día"), (2, rgr, "día⁻¹")):
            fig.add_trace(go.Scatter(x=t_fino, y=serie, mode="lines", showlegend=False,
                                     line=dict(color=COLOR_GRUPO[grupo], dash=estilo["dash"], width=2.6),
                                     hovertemplate=f"Día %{{x:.0f}}: %{{y:.4g}} {u}<extra>{modelo}</extra>"),
                          row=fila, col=col)
        k = int(np.nanargmax(agr))
        maximos[grupo] = (t_fino[k], agr[k], modelo)
        panel_agr = col
        xr, yr = _ref_ejes(panel_agr)
        fig.add_trace(go.Scatter(x=[t_fino[k]], y=[agr[k]], mode="markers", showlegend=False,
                                 marker=dict(symbol="diamond", size=11, color="white",
                                             line=dict(color=G_INK, width=2)), hoverinfo="skip"), row=1, col=col)
        fig.add_annotation(x=t_fino[k], y=agr[k], xref=xr, yref=yr, showarrow=False, yanchor="bottom", yshift=8,
                           text=f"máx. día {t_fino[k]:.0f}: {agr[k]:.3g} {unidad}/día",
                           font=dict(family=FUENTE_PUBLICACION, size=11.5, color=G_INK))
        fig.add_annotation(x=1, y=0.02, xref=f"{_ref_ejes(n + col)[0]} domain",
                           yref=f"{_ref_ejes(n + col)[1]} domain", xanchor="right", yanchor="bottom",
                           showarrow=False, text=f"modelo: {modelo} (mejor R²)",
                           font=dict(family=FUENTE_PUBLICACION, size=11, color=G_MUTED))
        fig.update_yaxes(rangemode="tozero", row=1, col=col)
        rgr_max = float(np.nanmax(rgr)) if np.any(np.isfinite(rgr)) else 0.0
        fig.update_yaxes(range=[0, rgr_max * 1.15 if rgr_max > 0 else 1], row=2, col=col)
        if col == 1:
            fig.update_yaxes(title_text=f"AGR ({unidad}/día)<br><span style='font-size:11px'>cuánto crece por día</span>",
                             row=1, col=col)
            fig.update_yaxes(title_text="RGR (día⁻¹)<br><span style='font-size:11px'>crecimiento relativo a su tamaño</span>",
                             row=2, col=col)
        rango_x = [dias_todos[0], dias_todos[-1]]
        ticks = dict(tickvals=dias_todos) if len(dias_todos) <= 8 else {}
        fig.update_xaxes(range=rango_x, showticklabels=True, row=1, col=col, **ticks)
        fig.update_xaxes(range=rango_x, title_text="Días después del trasplante", showticklabels=True,
                         row=2, col=col, **ticks)

    if len(maximos) == 2:
        (d_c, v_c, _), (d_t, v_t, _) = maximos["-M"], maximos["+M"]
        titulo = (f"Velocidad máxima de crecimiento: +M {v_t:.3g} {unidad}/día (día {d_t:.0f}) frente a "
                  f"−M {v_c:.3g} {unidad}/día (día {d_c:.0f})")
    else:
        g0 = next(iter(maximos))
        titulo = (f"{NOMBRE_VARIABLE[variable]}: velocidad máxima de {texto_grupo(g0)} = "
                  f"{maximos[g0][1]:.3g} {unidad}/día (día {maximos[g0][0]:.0f})")
    estilo_publicacion(fig, width=1200, height=820, titulo=titulo, mostrar_leyenda=False, left_margin=90,
                       subtitulo="Arriba, AGR: cuánto crece la planta cada día · abajo, RGR: cuánto crece en "
                                 "proporción a su tamaño · ◇ = día de crecimiento más rápido")
    for col, grupo in enumerate(grupos_validos, start=1):
        encabezado_panel(fig, col, f"<b>{texto_grupo(grupo)}</b> · {NOMBRE_GRUPO[grupo]}", COLOR_GRUPO[grupo])

    notas = [f"Modelo usado en {texto_grupo(g)}: {mejores[g]} (mejor R² entre los convergidos)." for g in grupos_validos]
    if len(grupos_validos) < len(grupos):
        notas.append(f"Sin tasas para {', '.join(texto_grupo(g) for g in grupos if g not in grupos_validos)}: "
                     "ningún modelo convergió en ese grupo.")
    extra = ("Réplicas sintéticas generadas a partir de medias y CV% publicados (Aguirre-Medina et al., 2023)."
             if fuente_datos == "real" else None)
    descripcion = ("Tasas calculadas analíticamente a partir de los parámetros ya ajustados del modelo con "
                   "mejor R² en cada grupo (sin reajustar). AGR = dP/dt (cuánto crece por día); "
                   "RGR = (1/P)·dP/dt (crecimiento relativo a su tamaño). ◇ = máximo de AGR.")
    return fig, construir_pie(descripcion, notas=notas, extra=extra)


# ==============================================================================
# ANOVA DE RESIDUOS — la variable respuesta es el residuo (medido − predicho).
#   1) residuo ~ día   (por grupo y modelo): ¿el error cambia según la etapa? = patrón sistemático.
#   2) |residuo| ~ modelo (por grupo), con Tukey: ¿qué modelo se equivoca menos?
# Cada figura va acompañada de "Cómo leer esta gráfica", "Qué dice aquí" (generado con los
# números reales), la tabla ANOVA y el significado de cada columna.
# ==============================================================================
COLOR_MODELO_TEXTO = {"Exponencial": "#0072B2", "Logístico": "#A06A00", "Gompertz": "#00805C"}


def anova_un_factor(y, factor):
    """ANOVA de un factor. Devuelve SC/gl/CM entre y dentro de niveles, F y p; o None si no
    hay al menos 2 niveles o no quedan grados de libertad dentro (sin réplicas)."""
    y, factor = np.asarray(y, dtype=float), np.asarray(factor)
    niveles = [n for n in np.unique(factor) if np.sum(factor == n) > 0]
    gl_e, gl_d = len(niveles) - 1, len(y) - len(niveles)
    if gl_e < 1 or gl_d < 1:
        return None
    grupos_y = [y[factor == n] for n in niveles]
    gm = y.mean()
    ss_e = float(sum(len(g) * (g.mean() - gm) ** 2 for g in grupos_y))
    ss_t = float(np.sum((y - gm) ** 2))
    ss_d = ss_t - ss_e
    if ss_d <= 0:
        return None
    F, p = f_oneway(*grupos_y)
    return dict(ss_e=ss_e, ss_d=ss_d, ss_t=ss_t, gl_e=gl_e, gl_d=gl_d, gl_t=len(y) - 1,
                cm_e=ss_e / gl_e, cm_d=ss_d / gl_d, F=float(F), p=float(p))


def letras_tukey(muestras):
    """Letras de Tukey (dict nombre -> letra) para muestras {nombre: array}: se ordenan de
    menor a mayor media y se cambia de letra cuando un nivel difiere (p < 0.05) del anterior.
    Misma letra = sin diferencia significativa entre esos niveles."""
    nombres = list(muestras)
    if len(nombres) < 2:
        return {n: "a" for n in nombres}
    tk = tukey_hsd(*[muestras[n] for n in nombres])
    orden = sorted(nombres, key=lambda n: np.mean(muestras[n]))
    letras, actual = {orden[0]: "a"}, "a"
    for i in range(1, len(orden)):
        if tk.pvalue[nombres.index(orden[i]), nombres.index(orden[i - 1])] < 0.05:
            actual = chr(ord(actual) + 1)
        letras[orden[i]] = actual
    return letras


def fmt_num(v):
    """Número corto para tablas ANOVA: 4 cifras significativas, sin notación científica
    (valores prácticamente cero -> '≈ 0')."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if abs(v) < 1e-4:
        return "≈ 0"
    if abs(v) >= 1e4:
        return f"{v:,.0f}"
    return f"{v:.4g}"


def _unir(elementos):
    """['a', 'b', 'c'] -> 'a, b y c'."""
    elementos = list(elementos)
    return elementos[0] if len(elementos) == 1 else ", ".join(elementos[:-1]) + " y " + elementos[-1]


def _fmt_signo(v, dec=1):
    return f"{v:+.{dec}f}".replace("-", "−")


def fig_residuos_dia(RES, variable, grupo, modelos):
    """ANOVA residuo ~ día para cada modelo de un grupo. Devuelve (fig, filas, frases) o None.
    filas = [(modelo, anova)] para la tabla; frases = "Qué dice aquí" en markdown."""
    unidad = UNIDADES[variable]
    validos = [m for m in modelos if RES[variable][grupo][m]["residuos"] is not None]
    if not validos:
        return None
    color = COLOR_GRUPO[grupo]
    fig = make_subplots(rows=1, cols=len(validos), horizontal_spacing=0.05, shared_yaxes=True)
    lim = max(float(np.max(np.abs(RES[variable][grupo][m]["residuos"]))) for m in validos) * 1.15 or 1.0
    filas, frases = [], []
    dias_todos = sorted(set().union(*[set(RES[variable][grupo][m]["t_flat"].tolist()) for m in validos]))
    for col, m in enumerate(validos, start=1):
        t, r = RES[variable][grupo][m]["t_flat"], RES[variable][grupo][m]["residuos"]
        dd = np.unique(t)
        medias = np.array([r[t == d].mean() for d in dd])
        fig.add_hline(y=0, line=dict(color=G_INK, width=1), row=1, col=col)
        fig.add_trace(go.Box(x=t, y=r, marker=dict(color=color, size=4), line=dict(color=color, width=1.3),
                             fillcolor="rgba(0,0,0,0)", boxpoints="all", jitter=0.4, pointpos=0, showlegend=False,
                             hovertemplate=f"Día %{{x:.0f}}<br>residuo %{{y:+.2f}} {unidad}<extra>{m}</extra>"),
                      row=1, col=col)
        fig.add_trace(go.Scatter(x=dd, y=medias, mode="lines+markers", showlegend=False,
                                 line=dict(color=G_INK, width=2),
                                 marker=dict(size=7, color=G_INK, symbol="diamond", line=dict(color="white", width=1.5)),
                                 hovertemplate=f"Día %{{x:.0f}}<br>residuo medio %{{y:+.2f}} {unidad}<extra></extra>"),
                      row=1, col=col)
        xr, yr = _ref_ejes(col)
        fig.add_annotation(xref=f"{xr} domain", yref=f"{yr} domain", x=0, y=1.02, xanchor="left", yanchor="bottom",
                           showarrow=False, text=f"<b>{m}</b>",
                           font=dict(family=FUENTE_PUBLICACION, size=15, color=COLOR_MODELO_TEXTO[m]))
        a = anova_un_factor(r, t)
        rango_txt = (f"residuo medio de **{_fmt_signo(medias.min())} {unidad}** (día {dd[np.argmin(medias)]:.0f}) "
                     f"a **{_fmt_signo(medias.max())} {unidad}** (día {dd[np.argmax(medias)]:.0f})")
        if a is None:
            sello_veredicto(fig, col, True, "sin prueba", "faltan réplicas por día")
            frases.append(dict(titulo=m, ok=None, etiqueta="sin prueba",
                               detalle=f"{rango_txt}; hace falta más de una planta por día para el ANOVA."))
            continue
        a["fuente_e"], a["fuente_d"] = "Entre días", "Dentro de días (réplicas)"
        filas.append((m, a))
        ok = a["p"] >= 0.05
        sello_veredicto(fig, col, ok, "sin patrón" if ok else "patrón sistemático",
                        f"F = {a['F']:.2f} · {formatear_p(a['p'])}")
        frases.append(dict(
            titulo=m, ok=ok, etiqueta="sin patrón" if ok else "patrón sistemático",
            detalle=(f"{formatear_p(a['p'])} · {rango_txt}. " +
                     ("Esas diferencias son solo ruido entre plantas: **sigue bien la curva**." if ok else
                      "Es más que el ruido entre plantas: **se equivoca igual en ciertas etapas**."))))
    for col in range(1, len(validos) + 1):
        fig.update_xaxes(title_text="Días después del trasplante", row=1, col=col,
                         **({"tickvals": dias_todos} if len(dias_todos) <= 8 else {}))
        fig.update_yaxes(range=[-lim, lim * 1.45], row=1, col=col)
    fig.update_yaxes(title_text=f"Residuo ({unidad})<br><span style='font-size:11px'>medido − predicho</span>",
                     row=1, col=1)
    malos = [m for m, a in filas if a["p"] < 0.05]
    g_txt = texto_grupo(grupo)
    if not filas:
        titulo = f"{g_txt}: residuos por día (sin réplicas suficientes para el ANOVA)"
    elif malos:
        titulo = (f"{g_txt}: los residuos de {_unir(malos)} cambian según el día "
                  f"({'patrón sistemático' if len(malos) == 1 else 'patrones sistemáticos'})")
    else:
        titulo = f"{g_txt}: ningún modelo deja patrón en los residuos (el error es solo ruido)"
    estilo_publicacion(fig, width=1200, height=520, titulo=titulo, mostrar_leyenda=False, left_margin=90,
                       subtitulo=f"{NOMBRE_VARIABLE[variable]} · {NOMBRE_GRUPO[grupo]} · ANOVA de un factor sobre "
                                 "los residuos (respuesta = residuo, factor = día) · ◆ = residuo medio del día")
    return fig, filas, frases


def fig_residuos_modelos(RES, variable, modelos, grupos):
    """ANOVA |residuo| ~ modelo por grupo, con letras de Tukey. Devuelve (fig, filas, frases) o
    None si no hay al menos 2 modelos con residuos en algún grupo."""
    unidad = UNIDADES[variable]
    grupos_ok = [g for g in grupos if sum(RES[variable][g][m]["residuos"] is not None for m in modelos) >= 2]
    if not grupos_ok:
        return None
    fig = make_subplots(rows=1, cols=len(grupos_ok), horizontal_spacing=0.08, shared_yaxes=True)
    ymax = max(float(np.max(np.abs(RES[variable][g][m]["residuos"])))
               for g in grupos_ok for m in modelos if RES[variable][g][m]["residuos"] is not None) * 1.25 or 1.0
    filas, frases, peores_global = [], [], set()
    for col, g in enumerate(grupos_ok, start=1):
        muestras = {m: np.abs(RES[variable][g][m]["residuos"]) for m in modelos
                    if RES[variable][g][m]["residuos"] is not None}
        y = np.concatenate(list(muestras.values()))
        fac = np.concatenate([[m] * len(v) for m, v in muestras.items()])
        a = anova_un_factor(y, fac)
        letras = letras_tukey(muestras)
        medias = {m: float(v.mean()) for m, v in muestras.items()}
        xr, yr = _ref_ejes(col)
        for m, v in muestras.items():
            fig.add_trace(go.Box(x=[m] * len(v), y=v, name=m, marker=dict(color=MODELO_ESTILO[m]["color"], size=4),
                                 line=dict(color=MODELO_ESTILO[m]["color"], width=1.4), fillcolor="rgba(0,0,0,0)",
                                 boxpoints="all", jitter=0.45, pointpos=0, boxmean=True, showlegend=False,
                                 hovertemplate=f"{m}<br>|residuo| %{{y:.2f}} {unidad}<extra></extra>"), row=1, col=col)
            fig.add_annotation(x=m, y=float(v.max()), yshift=14, xref=xr, yref=yr, showarrow=False,
                               font=dict(family=FUENTE_PUBLICACION, size=14, color=G_INK), text=f"<b>{letras[m]}</b>")
            fig.add_annotation(x=m, y=0, yshift=-2, yanchor="top", xref=xr, yref=yr, showarrow=False,
                               font=dict(family=FUENTE_PUBLICACION, size=11, color=G_MUTED),
                               text=f"media {medias[m]:.3g} {unidad}")
        fig.add_annotation(xref=f"{xr} domain", yref=f"{yr} domain", x=0, y=1.02, xanchor="left", yanchor="bottom",
                           showarrow=False, font=dict(family=FUENTE_PUBLICACION, size=15, color=COLOR_GRUPO[g]),
                           text=f"<b>({'ab'[col - 1]}) {texto_grupo(g)} · {NOMBRE_GRUPO[g]}</b>")
        fig.update_yaxes(range=[-ymax * 0.08, ymax], row=1, col=col)
        if a is None:
            continue
        a["fuente_e"], a["fuente_d"] = "Entre modelos", "Dentro de modelos"
        filas.append((texto_grupo(g), a))
        ok = a["p"] >= 0.05
        sello_veredicto(fig, col, ok, "sin diferencias" if ok else "los modelos difieren",
                        f"F = {a['F']:.2f} · {formatear_p(a['p'])}", y=0.99)
        orden = sorted(muestras, key=lambda m: medias[m])
        mejor = orden[0]
        empatados = [m for m in orden if letras[m] == letras[mejor]]
        peores = [m for m in orden if letras[m] != letras[mejor]]
        peores_global.update(peores)
        errores_txt = " · ".join(f"{m} **{medias[m]:.2f} {unidad}** ({letras[m]})" for m in orden)
        if ok or not peores:
            frases.append(dict(titulo=f"{texto_grupo(g)} · {NOMBRE_GRUPO[g]}", ok=True, etiqueta="sin diferencias",
                               detalle=f"{formatear_p(a['p'])} · error medio: {errores_txt}. "
                                       "**Los modelos se equivocan lo mismo.**"))
        else:
            frases.append(dict(
                titulo=f"{texto_grupo(g)} · {NOMBRE_GRUPO[g]}", ok=False, etiqueta="los modelos difieren",
                detalle=f"{formatear_p(a['p'])} · error medio: {errores_txt}. **{_unir(peores)} se "
                        f"equivoca{'' if len(peores) == 1 else 'n'} más** que {_unir(empatados)}."))
    fig.update_yaxes(title_text=f"Error absoluto |residuo| ({unidad})", row=1, col=1)
    fig.update_xaxes(showline=False, ticks="")
    if peores_global and len(peores_global) < len(modelos):
        mejores_txt = [m for m in modelos if m not in peores_global]
        titulo = (f"{_unir(mejores_txt)} se {'equivoca' if len(mejores_txt) == 1 else 'equivocan'} "
                  f"menos que {_unir(sorted(peores_global, key=modelos.index))}")
    elif filas and all(a["p"] >= 0.05 for _, a in filas):
        titulo = "Los modelos se equivocan en promedio lo mismo"
    else:
        titulo = "¿Qué modelo se equivoca menos?"
    estilo_publicacion(fig, width=1200, height=540, titulo=titulo, mostrar_leyenda=False, left_margin=90,
                       subtitulo=f"{NOMBRE_VARIABLE[variable]} · ANOVA de un factor sobre los residuos (respuesta = "
                                 "|residuo|, el tamaño del error; factor = modelo) · letras = prueba de Tukey")
    return fig, filas, frases


def tabla_anova_df(filas, primera_col, texto_ok, texto_mal):
    """Tabla ANOVA clásica (una fila por fuente de variación) como DataFrame para la app."""
    registros = []
    for etiqueta, a in filas:
        ok = a["p"] >= 0.05
        registros += [
            {primera_col: etiqueta, "Fuente de variación": a["fuente_e"], "SC": a["ss_e"], "gl": a["gl_e"],
             "CM": a["cm_e"], "F": a["F"], "Valor p": formatear_p(a["p"]),
             "Interpretación": ("✓ " + texto_ok) if ok else ("✗ " + texto_mal)},
            {primera_col: "", "Fuente de variación": a["fuente_d"], "SC": a["ss_d"], "gl": a["gl_d"],
             "CM": a["cm_d"], "F": np.nan, "Valor p": "", "Interpretación": ""},
            {primera_col: "", "Fuente de variación": "Total", "SC": a["ss_t"], "gl": a["gl_t"],
             "CM": np.nan, "F": np.nan, "Valor p": "", "Interpretación": ""},
        ]
    return pd.DataFrame(registros)


def fig_tabla_anova(filas, primera_col, texto_ok, texto_mal, titulo):
    """La misma tabla ANOVA como figura (para el PNG descargable y el PDF)."""
    cols = [[] for _ in range(8)]
    fondo, color_v = [], []
    for i, (etiqueta, a) in enumerate(filas):
        ok = a["p"] >= 0.05
        bloque = [
            (f"<b>{etiqueta}</b>", a["fuente_e"], fmt_num(a["ss_e"]), a["gl_e"], fmt_num(a["cm_e"]),
             f"<b>{a['F']:.2f}</b>", f"<b>{formatear_p(a['p'])}</b>",
             ("<b>✓</b> " + texto_ok) if ok else ("<b>✗</b> " + texto_mal)),
            ("", a["fuente_d"], fmt_num(a["ss_d"]), a["gl_d"], fmt_num(a["cm_d"]), "", "", ""),
            ("", "<i>Total</i>", f"<i>{fmt_num(a['ss_t'])}</i>", f"<i>{a['gl_t']}</i>", "", "", "", ""),
        ]
        for b in bloque:
            for k, x in enumerate(b):
                cols[k].append(x)
            fondo.append("white" if i % 2 == 0 else "#FBF9F6")
        color_v += [T["VERDE"] if ok else T["ROJO"], G_INK, G_INK]
    alinear = ["left", "left"] + ["right"] * 5 + ["left"]
    fig = go.Figure(go.Table(
        columnwidth=[1.05, 1.5, 0.75, 0.4, 0.75, 0.6, 0.85, 2.9],
        header=dict(values=[f"<b>{primera_col}</b>", "<b>Fuente de variación</b>", "<b>SC</b>", "<b>gl</b>",
                            "<b>CM</b>", "<b>F</b>", "<b>Valor p</b>", "<b>Interpretación</b>"],
                    fill_color="#F1ECE4", line_color="white", align=alinear,
                    font=dict(family=FUENTE_PUBLICACION, size=12.5, color=G_INK), height=30),
        cells=dict(values=cols, align=alinear, height=27, fill_color=[fondo], line_color="#EEE9E1",
                   font=dict(family=FUENTE_PUBLICACION, size=12.5, color=[[G_INK] * len(fondo)] * 7 + [color_v]))))
    fig.update_layout(width=1200, height=30 + 27 * 3 * len(filas) + 22 * len(filas) + 70,
                      margin=dict(l=80, r=80, t=50, b=6), paper_bgcolor="white",
                      title=dict(text=f"<b>{titulo}</b>", x=0.067, xanchor="left", y=0.985, yanchor="top",
                                 font=dict(family=FUENTE_PUBLICACION, size=16, color=G_INK)))
    return fig


ANOVA_TEXTOS = {
    "dia": {
        "ok": "El residuo medio no cambia entre días: el modelo sigue bien la curva",
        "mal": "El residuo medio cambia según el día: el modelo se desvía en ciertas etapas",
        "como_leer": [
            ("Residuo", "medido − predicho. Positivo = el modelo se quedó corto (subestima); negativo = se pasó "
                        "(sobreestima)."),
            ("Puntos y caja", "el residuo de cada planta ese día; la caja es la mitad central de esos valores."),
            ("◆ y línea", "el residuo promedio de cada día."),
            ("Línea en 0", "error cero. Un buen modelo deja los ◆ cerca de ella, subiendo y bajando al azar."),
            ("Qué buscar", "si los ◆ dibujan una forma (una «U», una onda, una subida), el modelo falla siempre "
                           "igual en ciertas etapas. El ANOVA dice si esa forma es real (p < 0.05) o puro azar."),
        ],
        "glosario": [
            ("Modelo", "la curva evaluada."),
            ("Fuente de variación", "**Entre días** = cuánto cambia el residuo promedio de un día a otro (el "
                                    "patrón). **Dentro de días** = cuánto varían las plantas del mismo día (ruido "
                                    "natural). **Total** = la suma de las dos."),
            ("SC", "suma de cuadrados: cuánta variación aporta cada fuente."),
            ("gl", "grados de libertad: entre días = nº de días − 1; dentro = nº de plantas − nº de días."),
            ("CM", "cuadrado medio = SC ÷ gl (la variación «promedio» de cada fuente)."),
            ("F", "CM entre días ÷ CM dentro de días. F ≈ 1 → sin patrón; F mucho mayor que 1 → hay patrón."),
            ("Valor p", "probabilidad de que sea azar. **p < 0.05** → el patrón es real; **p ≥ 0.05** → no hay "
                        "evidencia de patrón."),
            ("Interpretación", "el resultado en palabras (✓ bien · ✗ revisar)."),
        ],
    },
    "modelo": {
        "ok": "Los modelos se equivocan en promedio lo mismo",
        "mal": "Al menos un modelo se equivoca más que los otros (ver letras de Tukey)",
        "como_leer": [
            ("|residuo|", "el tamaño del error de cada planta, sin importar si fue por arriba o por abajo."),
            ("Puntos y caja", "el error de cada planta (todas las fechas); la caja es la mitad central. "
                              "Raya punteada = promedio, escrito abajo como «media»."),
            ("Más abajo = mejor", "una caja baja significa que el modelo se equivoca poco."),
            ("Letras (a, b…)", "prueba de Tukey: **misma letra = sin diferencia real**; letra distinta = sí "
                               "la hay."),
            ("Qué buscar", "el recuadro de cada panel (ANOVA) dice si algún modelo difiere; las letras dicen "
                           "cuál."),
        ],
        "glosario": [
            ("Grupo", "−M (sin micorriza) o +M (inoculado); un ANOVA por grupo."),
            ("Fuente de variación", "**Entre modelos** = cuánto difiere el error promedio de un modelo a otro. "
                                    "**Dentro de modelos** = cuánto varía el error de planta a planta. "
                                    "**Total** = la suma de las dos."),
            ("SC", "suma de cuadrados: cuánta variación aporta cada fuente."),
            ("gl", "grados de libertad: entre modelos = nº de modelos − 1; dentro = nº de errores − nº de "
                   "modelos."),
            ("CM", "cuadrado medio = SC ÷ gl (la variación «promedio» de cada fuente)."),
            ("F", "CM entre modelos ÷ CM dentro de modelos. F ≈ 1 → se equivocan igual; F mucho mayor que 1 → "
                  "no."),
            ("Valor p", "probabilidad de que sea azar. **p < 0.05** → la diferencia es real; **p ≥ 0.05** → no "
                        "hay evidencia de diferencia."),
            ("Interpretación", "el resultado en palabras (✓ bien · ✗ revisar)."),
        ],
    },
}


def glosario_anova(tipo):
    """Lista (término, definición en markdown) de las columnas de la tabla ANOVA."""
    return ANOVA_TEXTOS[tipo]["glosario"]


def _sin_markdown(texto):
    return texto.replace("**", "")


# --- Composición del PNG descargable del ANOVA (PIL): bloques ordenados, no texto corrido ---
_FUENTES_PNG = {}


def _fuente_png(tam, negrita=False):
    clave = (tam, negrita)
    if clave not in _FUENTES_PNG:
        import matplotlib.font_manager as fm
        ruta = fm.findfont(fm.FontProperties(family="DejaVu Sans", weight="bold" if negrita else "normal"))
        _FUENTES_PNG[clave] = ImageFont.truetype(ruta, tam)
    return _FUENTES_PNG[clave]


def _rgb(hex_color):
    return tuple(int(hex_color[k:k + 2], 16) for k in (1, 3, 5))


def _lineas_rich(texto, ancho, tam, draw):
    """Parte un texto con **negritas** en líneas que caben en `ancho` px. Cada línea es una
    lista de (palabra, fuente)."""
    f_r, f_b = _fuente_png(tam), _fuente_png(tam, True)
    tokens = []
    for k, seg in enumerate(re.split(r"\*\*", texto)):
        if seg[:1].isspace() and tokens:
            tokens[-1] = (tokens[-1][0] + " ", tokens[-1][1])
        for w in re.findall(r"\S+\s*", seg):
            tokens.append((w, f_b if k % 2 else f_r))
    lineas, linea, x = [], [], 0
    for w, f in tokens:
        wl = draw.textlength(w, font=f)
        if linea and x + wl - draw.textlength(" ", font=f) > ancho:
            lineas.append(linea)
            linea, x = [], 0
        linea.append((w, f))
        x += wl
    if linea:
        lineas.append(linea)
    return lineas


def _dibujar_rich(draw, lineas, x, y, interlineado, color):
    for linea in lineas:
        xx = x
        for w, f in linea:
            draw.text((xx, y), w, font=f, fill=color)
            xx += draw.textlength(w, font=f)
        y += interlineado
    return y


def _bloque_tarjetas(veredictos, ancho, margen):
    """Fila de tarjetas «Qué dice aquí»: una por modelo (o grupo), borde verde/rojo con ✓/✗."""
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    n = max(len(veredictos), 1)
    gap = 24
    ancho_t = (ancho - 2 * margen - gap * (n - 1)) // n
    pad, tam = 26, 25
    inter = int(tam * 1.45)
    contenidos = [_lineas_rich(v["detalle"], ancho_t - 2 * pad, tam, tmp) for v in veredictos]
    alto_t = pad + 40 + max(len(c) for c in contenidos) * inter + pad
    titulo_h = 58
    img = Image.new("RGB", (ancho, titulo_h + alto_t + 30), "white")
    d = ImageDraw.Draw(img)
    d.text((margen, 8), "Qué dice aquí", font=_fuente_png(30, True), fill=_rgb(G_INK))
    for k, (v, lineas) in enumerate(zip(veredictos, contenidos)):
        x0 = margen + k * (ancho_t + gap)
        y0 = titulo_h
        color = _rgb(T["VERDE"] if v["ok"] else (T["ROJO"] if v["ok"] is False else G_MUTED))
        fondo = tuple(int(c * 0.07 + 255 * 0.93) for c in color)
        d.rounded_rectangle([x0, y0, x0 + ancho_t, y0 + alto_t], radius=14, fill=fondo, outline=color, width=3)
        icono = "✓" if v["ok"] else ("✗" if v["ok"] is False else "•")
        d.text((x0 + pad, y0 + pad - 4), f"{icono} {v['titulo']}", font=_fuente_png(27, True), fill=color)
        ancho_tit = d.textlength(f"{icono} {v['titulo']}", font=_fuente_png(27, True))
        d.text((x0 + pad + ancho_tit + 14, y0 + pad), v["etiqueta"], font=_fuente_png(23), fill=color)
        _dibujar_rich(d, lineas, x0 + pad, y0 + pad + 44, inter, _rgb(G_INK))
    return img


def _bloque_dos_columnas(izq, der, ancho, margen):
    """Dos recuadros lado a lado: «Cómo leer esta gráfica» y «Qué significa cada columna».
    Cada lado es (título, [(término, texto)])."""
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    gap, pad, tam = 28, 30, 23
    inter = int(tam * 1.45)
    ancho_c = (ancho - 2 * margen - gap) // 2
    sang = 250

    def preparar(items):
        return [(t, _lineas_rich(txt, ancho_c - 2 * pad - sang, tam, tmp)) for t, txt in items]

    lados = [(izq[0], preparar(izq[1])), (der[0], preparar(der[1]))]
    alto = max(pad + 52 + sum(max(len(l), 1) * inter + 12 for _, l in items) + pad for _, items in lados)
    img = Image.new("RGB", (ancho, alto + 30), "white")
    d = ImageDraw.Draw(img)
    for k, (titulo, items) in enumerate(lados):
        x0 = margen + k * (ancho_c + gap)
        d.rounded_rectangle([x0, 0, x0 + ancho_c, alto], radius=14, fill=_rgb("#FAF8F5"),
                            outline=_rgb("#E4DFD6"), width=2)
        d.rectangle([x0, 12, x0 + 7, alto - 12], fill=_rgb(T["ACCENT"] if k == 0 else G_MUTED))
        d.text((x0 + pad, pad - 4), titulo, font=_fuente_png(28, True), fill=_rgb(G_INK))
        y = pad + 52
        for termino, lineas in items:
            tl = _lineas_rich(f"**{termino}**", sang - 16, tam, d)
            _dibujar_rich(d, tl, x0 + pad, y, inter, _rgb(G_INK))
            y_fin = _dibujar_rich(d, lineas, x0 + pad + sang, y, inter, _rgb("#3C3832"))
            y = max(y_fin, y + len(tl) * inter) + 12
    return img


def png_anova_explicado(fig, fig_tabla, tipo, veredictos, nota=None, scale=2, incluir_guia=True):
    """PNG descargable del ANOVA, ordenado en bloques: gráfica → «Qué dice aquí» (tarjetas
    ✓/✗) → tabla ANOVA → «Cómo leer esta gráfica» | «Qué significa cada columna»."""
    im_fig = Image.open(io.BytesIO(fig.to_image(format="png", scale=scale))).convert("RGB")
    im_tab = Image.open(io.BytesIO(fig_tabla.to_image(format="png", scale=scale))).convert("RGB")
    ancho = im_fig.width
    margen = int(80 * scale)
    partes = [im_fig, Image.new("RGB", (ancho, 20), "white"),
              _bloque_tarjetas(veredictos, ancho, margen), im_tab, Image.new("RGB", (ancho, 24), "white")]
    if incluir_guia:
        partes.append(_bloque_dos_columnas(("Cómo leer esta gráfica", ANOVA_TEXTOS[tipo]["como_leer"]),
                                           ("Qué significa cada columna de la tabla", glosario_anova(tipo)),
                                           ancho, margen))
    if nota:
        tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        lineas = _lineas_rich(nota, ancho - 2 * margen, 21, tmp)
        img_n = Image.new("RGB", (ancho, len(lineas) * 31 + 30), "white")
        _dibujar_rich(ImageDraw.Draw(img_n), lineas, margen, 6, 31, _rgb(G_MUTED))
        partes.append(img_n)
    lienzo = Image.new("RGB", (ancho, sum(p.height for p in partes)), "white")
    y = 0
    for p_ in partes:
        lienzo.paste(p_, ((ancho - p_.width) // 2, y))
        y += p_.height
    buf = io.BytesIO()
    lienzo.save(buf, format="PNG")
    return buf.getvalue()


def calcular_banda_confianza(func, popt, pcov, t_eval, n_muestras=400, semilla_mc=7):
    if popt is None or pcov is None or np.any(np.isnan(pcov)):
        return None, None
    rng = np.random.default_rng(semilla_mc)
    try:
        muestras = rng.multivariate_normal(popt, pcov, size=n_muestras)
    except np.linalg.LinAlgError:
        return None, None
    curvas = np.array([func(t_eval, *m) for m in muestras])
    banda_baja = np.nanpercentile(curvas, 2.5, axis=0)
    banda_alta = np.nanpercentile(curvas, 97.5, axis=0)
    return banda_baja, banda_alta


def badge_r2(r2, insuficiente=False, dias_disponibles=None, dias_requeridos=None):
    if insuficiente:
        return (f'<span class="badge badge-ambar">{ESTADO_SIN_DIAS} · {dias_disponibles}/{dias_requeridos} '
                f'necesarios para este modelo</span>')
    if r2 is None or np.isnan(r2):
        return f'<span class="badge badge-rojo">{ESTADO_NO_CONVERGIO}</span>'
    if r2 >= 0.9:
        return f'<span class="badge badge-verde">Ajuste fuerte · R² {r2:.3f}</span>'
    if r2 >= 0.7:
        return f'<span class="badge badge-ambar">Ajuste moderado · R² {r2:.3f}</span>'
    return f'<span class="badge badge-rojo">Ajuste débil · R² {r2:.3f}</span>'


def barra_valor_p(p, significativo):
    """HTML de una mini barra que ubica el valor p frente al umbral 0.05 (solo visual, no reemplaza el numero)."""
    escala_max = 0.15
    pos_pct = min(p / escala_max, 1.0) * 100
    umbral_pct = 0.05 / escala_max * 100
    color = T["VERDE"] if significativo else T["AMBAR"]
    return f'''<div style="position:relative; height:20px; margin:0.5rem 0 0.15rem 0;">
        <div style="position:absolute; top:8px; left:0; right:0; height:4px; background:{T['BORDER']}; border-radius:2px;"></div>
        <div style="position:absolute; top:2px; left:{umbral_pct:.1f}%; width:1px; height:16px; background:{T['INK_MUTED']};"></div>
        <div style="position:absolute; top:4px; left:calc({pos_pct:.1f}% - 6px); width:12px; height:12px; border-radius:50%;
            background:{color}; box-shadow:0 0 0 2px {T['CARD']};"></div>
    </div>
    <div style="display:flex; justify-content:space-between; font-family:'IBM Plex Mono',monospace; font-size:0.6rem; color:{T['INK_MUTED']};">
        <span>p = 0</span><span>umbral 0.05</span><span>&ge; {escala_max:.2f}</span>
    </div>'''


def generar_sugerencias(fuente_datos):
    """Lista de sugerencias de mejora, adaptada segun si se esta usando
    datos simulados o datos reales cargados por el usuario."""
    universales = [
        "Validación cruzada (ajustar con una parte de los datos, comprobar con el resto).",
        "Documentar todos los supuestos explícitamente en la metodología.",
    ]
    if fuente_datos == "real":
        especificas = [
            "Validación externa con un segundo estudio publicado, idealmente con series de tiempo más largas.",
            "Ampliar el número de días de muestreo si el estudio de campo continúa, para cubrir también la "
            "fase de desaceleración del crecimiento (necesaria para que Logístico y Gompertz converjan de forma estable).",
            "Las réplicas individuales cargadas son sintéticas (generadas para reproducir la media y desviación "
            "estándar reportadas en el paper, no mediciones planta por planta) — tenerlo en cuenta al interpretar "
            "los intervalos de confianza.",
        ]
    else:
        especificas = [
            "Reemplazar los datos simulados por mediciones reales (sección *Datos de prueba*).",
        ]
    return especificas + universales


def generar_ilustracion_plantas(datos, fuente_datos="simulado"):
    """Ilustracion esquematica (NO fotografica) que compara -M vs +M usando
    los valores reales del ultimo dia de muestreo disponible. Devuelve bytes
    PNG, o None si no hay ninguna variable relevante en `datos`."""
    variables_relevantes = ["altura", "area_foliar", "biomasa", "hojas"]
    if not any(v in datos for v in variables_relevantes):
        return None

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    valores = {}
    for var in variables_relevantes:
        if var not in datos:
            continue
        valores[var] = {}
        for grupo in ("-M", "+M"):
            if grupo in datos[var]:
                _, medias, _, _ = media_sd_por_dia(datos[var][grupo])
                valores[var][grupo] = float(medias[-1])

    alturas = valores.get("altura", {"-M": 20.0, "+M": 20.0})
    areas = valores.get("area_foliar", {"-M": 100.0, "+M": 100.0})
    biomasas = valores.get("biomasa", {})
    hojas_n = valores.get("hojas", {})
    max_altura = max(alturas.values()) or 1.0
    max_area = max(areas.values()) or 1.0

    colores = {"-M": "#8C8578", "+M": "#A8432B"}
    nombres_grupo = {"-M": "-M (control)", "+M": "+M (inoculado)"}

    fig, axes = plt.subplots(1, 2, figsize=(9, 6.2))
    for ax, grupo in zip(axes, ["-M", "+M"]):
        color = colores[grupo]
        rng = np.random.default_rng(1 if grupo == "-M" else 2)
        alto_tallo = alturas.get(grupo, max_altura) / max_altura * 5.0 + 1.5
        escala_hoja = (areas.get(grupo, max_area) / max_area) ** 0.5

        ax.axhspan(-3.6, 0, color="#E4DFD6", zorder=0)
        ax.axhline(0, color="#8C8578", linewidth=1.2, zorder=1)
        ax.plot([0, 0], [0, alto_tallo], color="#5B4636", linewidth=3, zorder=2)

        for i in range(6):
            frac = (i + 1) / 7
            y = frac * alto_tallo
            lado = 1 if i % 2 == 0 else -1
            ancho, alto = 0.55 * escala_hoja, 0.22 * escala_hoja
            elip = mpatches.Ellipse((lado * ancho * 0.6, y), width=ancho, height=alto,
                                     angle=25 * lado, facecolor=color, edgecolor="none",
                                     alpha=0.85, zorder=3)
            ax.add_patch(elip)

        for _ in range(5):
            dx = rng.uniform(-1.2, 1.2)
            profundidad = rng.uniform(1.2, 2.2)
            ax.plot([0, dx], [0, -profundidad], color="#7A5C3E", linewidth=1.3, alpha=0.8, zorder=2)
            dx2 = dx + rng.uniform(-0.4, 0.4)
            ax.plot([dx, dx2], [-profundidad, -profundidad - rng.uniform(0.3, 0.6)],
                    color="#7A5C3E", linewidth=1.0, alpha=0.7, zorder=2)

        if grupo == "+M":
            for _ in range(16):
                dx = rng.uniform(-2.3, 2.3)
                profundidad = rng.uniform(1.6, 3.3)
                ax.plot([0, dx], [-0.3, -profundidad], color="#C9922E", linewidth=0.5, alpha=0.6, zorder=1)
            ax.text(0, -3.75, "red de hifas micorrízicas", ha="center", va="top",
                    fontsize=7.5, style="italic", color="#8A6A1E")

        ax.set_xlim(-2.7, 2.7)
        ax.set_ylim(-4.6, 7.2)
        ax.axis("off")
        ax.set_title(nombres_grupo[grupo], fontsize=13, fontweight="bold", color=color, pad=10)

        lineas_valor = []
        if "altura" in valores:
            lineas_valor.append(f"Altura: {alturas[grupo]:.1f} {UNIDADES['altura']}")
        if "area_foliar" in valores:
            lineas_valor.append(f"Área foliar: {areas[grupo]:.1f} {UNIDADES['area_foliar']}")
        if grupo in biomasas:
            lineas_valor.append(f"Biomasa: {biomasas[grupo]:.2f} {UNIDADES['biomasa']}")
        if grupo in hojas_n:
            lineas_valor.append(f"Hojas: {hojas_n[grupo]:.1f}")
        ax.text(0, -4.1, "\n".join(lineas_valor) if lineas_valor else "Sin datos reales disponibles",
                ha="center", va="top", fontsize=9, family="monospace", color="#201C18")

    origen_txt = "datos reales cargados" if fuente_datos == "real" else "datos de prueba simulados"
    fig.suptitle("ILUSTRACIÓN CONCEPTUAL A ESCALA — NO ES UNA FOTOGRAFÍA REAL",
                 fontsize=11.5, fontweight="bold", color="#9A3324", y=0.995)
    fig.text(0.5, 0.945, f"Comparación esquemática según el último día de muestreo disponible en los {origen_txt}",
              ha="center", fontsize=9, color="#6B6459")

    plt.tight_layout(rect=[0, 0.03, 1, 0.92])
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ==============================================================================
# 2b. FORMATO LARGO (para plantilla / carga de datos reales / exportación)
# ==============================================================================
def datos_a_formato_largo(datos):
    filas = []
    for variable, grupos in datos.items():
        for grupo, datos_dia in grupos.items():
            for dia, valores in datos_dia.items():
                for i, v in enumerate(valores, start=1):
                    filas.append({"variable": variable, "grupo": grupo, "dat": int(dia),
                                   "replica": i, "valor": round(float(v), 4)})
    return pd.DataFrame(filas)


def generar_plantilla_excel():
    df = datos_a_formato_largo(generar_datos(42))
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="datos", index=False)
        instrucciones = pd.DataFrame({
            "Instrucciones": [
                "Columna 'variable': altura o biomasa (en minúsculas, tal cual).",
                "Columna 'grupo': -M (sin inocular) o +M (inoculado).",
                "Columna 'dat': día después del trasplante (número entero).",
                "Columna 'replica': número de repetición/planta para ese día y grupo (1, 2, 3...).",
                "Columna 'valor': la medición (cm para altura, g para biomasa).",
                "No hace falta el mismo número de réplicas en todos los días, pero se recomienda.",
                "Esta hoja trae datos de EJEMPLO (simulados) solo para mostrar el formato esperado.",
            ]
        })
        instrucciones.to_excel(writer, sheet_name="instrucciones", index=False)
    return buffer.getvalue()


def cargar_datos_desde_archivo(archivo):
    """Lee un CSV/Excel en formato largo y lo convierte a la estructura
    DATOS[variable][grupo][dia] = array. Devuelve (datos, error)."""
    try:
        if archivo.name.lower().endswith(".csv"):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo, sheet_name=0)
    except Exception as e:
        return None, f"No se pudo leer el archivo: {e}"

    df.columns = [c.strip().lower() for c in df.columns]
    columnas_esperadas = {"variable", "grupo", "dat", "valor"}
    faltantes = columnas_esperadas - set(df.columns)
    if faltantes:
        return None, f"Faltan columnas obligatorias: {', '.join(sorted(faltantes))}. Usa la plantilla."

    df["variable"] = df["variable"].astype(str).str.strip().str.lower()
    df["grupo"] = df["grupo"].astype(str).str.strip()
    variables_validas = {"altura", "biomasa", "diametro", "hojas", "area_foliar"}
    grupos_validos = {"-M", "+M"}
    if not set(df["variable"].unique()).issubset(variables_validas):
        return None, f"La columna 'variable' solo admite: {variables_validas}. Encontrado: {set(df['variable'].unique())}"
    if not set(df["grupo"].unique()).issubset(grupos_validos):
        return None, f"La columna 'grupo' solo admite: {grupos_validos}. Encontrado: {set(df['grupo'].unique())}"

    try:
        df["dat"] = df["dat"].astype(int)
        df["valor"] = df["valor"].astype(float)
    except Exception:
        return None, "Las columnas 'dat' y 'valor' deben ser numéricas."

    variables_presentes = sorted(df["variable"].unique())
    datos = {v: {"-M": {}, "+M": {}} for v in variables_presentes}
    for (variable, grupo, dia), grupo_df in df.groupby(["variable", "grupo", "dat"]):
        datos[variable][grupo][int(dia)] = grupo_df["valor"].to_numpy()

    for variable in datos:
        for grupo in datos[variable]:
            if len(datos[variable][grupo]) == 0:
                return None, f"No hay datos para variable='{variable}', grupo='{grupo}'."

    advertir_dias_insuficientes(datos)
    return datos, None


def advertir_dias_insuficientes(datos):
    """Avisa de inmediato (al cargar el archivo, no al ajustar) si alguna
    combinación variable/grupo no tiene suficientes días distintos (dat)
    para identificar alguno de los modelos de crecimiento."""
    avisos = []
    for variable in datos:
        for grupo in datos[variable]:
            n_dias = len(datos[variable][grupo])
            modelos_insuf = [f"{m} (necesita ≥{len(info['nombres_param'])})"
                              for m, info in MODELOS.items() if n_dias < len(info["nombres_param"])]
            if modelos_insuf:
                avisos.append((variable, grupo, n_dias, modelos_insuf))

    if not avisos:
        return

    lineas = [
        f"- **{NOMBRE_VARIABLE.get(variable, variable)}** `{grupo}`: {n_dias} día(s) distinto(s) de muestreo "
        f"→ no alcanza para: {', '.join(modelos_insuf)}."
        for variable, grupo, n_dias, modelos_insuf in avisos
    ]
    st.warning(
        "**Días de muestreo insuficientes para algunos modelos.** Un modelo de crecimiento necesita "
        "medir la misma variable en varios días distintos para poder estimar sus parámetros "
        "(Exponencial: mínimo 2 días; Logístico y Gompertz: mínimo 3 días). Con un solo día de datos "
        "solo se puede comparar el valor puntual entre grupos, no ajustar una curva.\n\n"
        + "\n".join(lineas) +
        f"\n\nEsas combinaciones se mostrarán como **'{ESTADO_SIN_DIAS}'** en vez de un R² una vez "
        "que ajustes los modelos — no es un error, es una limitación real de estos datos hasta que se "
        "agreguen más fechas de muestreo.",
        icon="⚠️",
    )


def obtener_datos_activos():
    if st.session_state.fuente_datos == "real" and st.session_state.datos_reales is not None:
        return st.session_state.datos_reales
    return generar_datos(st.session_state.semilla)


DATOS = obtener_datos_activos()


# ==============================================================================
# VALIDACIÓN EXTERNA — datos independientes de un paper, cargados en «Datos de prueba».
# Los modelos se ajustan a los datos reales activos (o, si no hay, con el Excel real del
# repositorio) y se comparan con los datos del paper, que el modelo nunca vio.
#
# Excel del paper — hoja «datos», una fila por variable, grupo y fecha:
#   variable (altura | hojas | diametro | biomasa | area_foliar), grupo (-M | +M), dia,
#   media, de (opcional), n (opcional)
# También acepta réplicas: variable, grupo, dia (o dat), replica, valor -> se calculan media, DE y n.
# Hoja «info» (opcional, columnas campo | valor): cita, origen_tiempo (trasplante | siembra |
# inoculacion), desfase_dias (días a SUMAR para pasar al eje ddt de la app).
# ==============================================================================
VE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "datos_reales")
VE_XLSX_BASE = os.path.join(VE_DIR, "datos_reales_coffea_2023.xlsx")
VE_XLSX_EJEMPLO = os.path.join(VE_DIR, "validacion_externa", "aguirre_medina_2011.xlsx")
VE_VARIABLES = ("altura", "hojas", "diametro", "biomasa", "area_foliar")
VE_ORIGENES = ("trasplante", "siembra", "inoculacion")
VE_MIN_FECHAS_HOLDOUT = 4   # 3 para ajustar Logístico/Gompertz + 1 para predecir
VE_MIN_FECHAS_EFECTO = 3
VE_NOMBRE = {"altura": "Altura", "hojas": "Número de hojas", "diametro": "Diámetro del tallo",
             "biomasa": "Biomasa total", "area_foliar": "Área foliar"}
VE_UNIDAD = {"altura": "cm", "hojas": "hojas", "diametro": "mm", "biomasa": "g", "area_foliar": "cm²"}
VE_VENTANA_DEFECTO = (28, 112)
VE_GRUPO_TXT = {"-M": "−M (sin inocular)", "+M": "+M (inoculado)"}
VE_SIMBOLO = {"-M": "circle", "+M": "triangle-up"}
VE_OPCIONES_MODELO = ["Mejor R²", "Exponencial", "Logístico", "Gompertz"]


# --- Lectura y revisión del Excel del paper ---------------------------------------------
def _ve_texto(x):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else str(x).strip()


def ve_leer_paper(archivo):
    """Lee el Excel/CSV del paper (ruta o archivo subido). Devuelve (paper, error), con
    paper = {"datos": {variable: {grupo: {dia: {"media", "de", "n"}}}}, "cita", "origen", "desfase"}."""
    nombre = archivo if isinstance(archivo, str) else getattr(archivo, "name", "")
    try:
        if str(nombre).lower().endswith(".csv"):
            hojas = {"datos": pd.read_csv(archivo)}
        else:
            hojas = pd.read_excel(archivo, sheet_name=None)
    except Exception as e:
        return None, f"No se pudo leer el archivo: {e}"
    hojas = {str(k).strip().lower(): v for k, v in hojas.items()}
    df = hojas.get("datos", next(iter(hojas.values()))).copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={"dat": "dia", "día": "dia", "dds": "dia", "ddt": "dia", "sd": "de", "ds": "de"})

    if not {"variable", "grupo", "dia"} <= set(df.columns):
        return None, "Faltan columnas obligatorias: «variable», «grupo» y «dia». Usa la plantilla."
    if "media" not in df.columns and "valor" not in df.columns:
        return None, "Falta la columna «media» (medias publicadas) o «valor» (réplicas). Usa la plantilla."
    df = df.dropna(subset=["variable", "grupo", "dia"])
    if df.empty:
        return None, "La hoja «datos» no tiene filas."
    df["variable"] = df["variable"].astype(str).str.strip().str.lower()
    df["grupo"] = df["grupo"].astype(str).str.strip().str.replace("−", "-", regex=False).str.upper()
    malas = sorted(set(df["variable"]) - set(VE_VARIABLES))
    if malas:
        return None, f"Variables no reconocidas: {malas}. Usa: {', '.join(VE_VARIABLES)}."
    malos = sorted(set(df["grupo"]) - {"-M", "+M"})
    if malos:
        return None, f"Grupos no reconocidos: {malos}. Usa «-M» (sin inocular) o «+M» (inoculado)."
    try:
        df["dia"] = pd.to_numeric(df["dia"]).astype(float)
        for col in ("media", "valor", "de", "n"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col])
    except Exception:
        return None, "Las columnas «dia», «media»/«valor», «de» y «n» deben ser numéricas."

    if "media" in df.columns:
        if df.duplicated(["variable", "grupo", "dia"]).any():
            return None, ("Hay filas repetidas (misma variable, grupo y día). Con columna «media» va una sola "
                          "fila por fecha; si tienes réplicas, usa la columna «valor».")
        resumen = df.assign(de=df["de"] if "de" in df.columns else np.nan,
                            n=df["n"] if "n" in df.columns else np.nan)
    else:
        resumen = (df.groupby(["variable", "grupo", "dia"])["valor"]
                   .agg(media="mean", de=lambda s: s.std(ddof=1) if len(s) > 1 else np.nan, n="count")
                   .reset_index())
    if resumen["media"].isna().any():
        return None, "Hay filas sin valor en «media»."
    if (resumen["media"] <= 0).any():
        return None, "Todas las medias deben ser mayores que 0."

    datos = {}
    for r in resumen.itertuples():
        datos.setdefault(r.variable, {}).setdefault(r.grupo, {})[float(r.dia)] = {
            "media": float(r.media),
            "de": float(r.de) if pd.notna(r.de) and r.de > 0 else None,
            "n": int(r.n) if pd.notna(r.n) and r.n >= 2 else None,
        }

    info = {}
    if "info" in hojas and hojas["info"].shape[1] >= 2:
        hi = hojas["info"]
        info = {_ve_texto(k).lower(): v for k, v in zip(hi.iloc[:, 0], hi.iloc[:, 1]) if _ve_texto(k)}
    origen = (_ve_texto(info.get("origen_tiempo")) or "trasplante").lower()
    origen = origen.replace("ó", "o").replace("inoculación", "inoculacion")
    if origen not in VE_ORIGENES:
        return None, f"En la hoja «info», origen_tiempo debe ser: {', '.join(VE_ORIGENES)}."
    desfase = None
    if _ve_texto(info.get("desfase_dias")):
        try:
            desfase = float(info["desfase_dias"])
        except (TypeError, ValueError):
            return None, "En la hoja «info», desfase_dias debe ser un número (o quedar vacío)."
    return {"datos": datos, "cita": _ve_texto(info.get("cita")), "origen": origen, "desfase": desfase}, None


def ve_plantilla_excel():
    buffer = io.BytesIO()
    ejemplo = pd.DataFrame([
        ("altura", "-M", 30, 7.5, 0.6, 6), ("altura", "+M", 30, 8.1, 0.7, 6),
        ("altura", "-M", 60, 10.2, 0.9, 6), ("altura", "+M", 60, 11.6, 1.0, 6),
        ("hojas", "-M", 30, 2.0, 0.3, 6), ("hojas", "+M", 30, 2.4, 0.4, 6),
    ], columns=["variable", "grupo", "dia", "media", "de", "n"])
    info = pd.DataFrame([("cita", "Autor et al. (año). Título. Revista vol(n):páginas."),
                         ("origen_tiempo", "trasplante"), ("desfase_dias", "")], columns=["campo", "valor"])
    instrucciones = pd.DataFrame({"Instrucciones": [
        "Hoja «datos»: una fila por variable, grupo y fecha, con los valores REALES publicados en el paper.",
        "variable: altura, hojas, diametro, biomasa o area_foliar (las variables de más del paper se omiten).",
        "grupo: -M = sin inocular (testigo); +M = inoculado con hongos micorrízicos.",
        "dia: el día de la medición, tal como lo da el paper. media: valor publicado (> 0).",
        "de y n (opcionales): desviación estándar y número de plantas. Permiten la prueba t del efecto del hongo.",
        "Si tienes réplicas planta por planta: usa columnas variable, grupo, dia, replica, valor (sin «media»).",
        "Hoja «info»: origen_tiempo = desde cuándo cuenta los días el paper (trasplante, siembra o inoculacion).",
        "Si no es «trasplante», la app estima el desfase comparando el tamaño de las plantas; o escríbelo en desfase_dias.",
        "Para «Fechas no vistas» hacen falta al menos 4 fechas por grupo; para el efecto del hongo, -M y +M.",
    ]})
    with pd.ExcelWriter(buffer, engine="openpyxl") as w:
        ejemplo.to_excel(w, sheet_name="datos", index=False)
        info.to_excel(w, sheet_name="info", index=False)
        instrucciones.to_excel(w, sheet_name="instrucciones", index=False)
    return buffer.getvalue()


@st.cache_data
def ve_leer_base(ruta):
    df = pd.read_excel(ruta, sheet_name="datos")
    datos = {}
    for (v, g, d), s in df.groupby(["variable", "grupo", "dat"]):
        datos.setdefault(v, {}).setdefault(g, {})[int(d)] = s["valor"].to_numpy()
    return datos


def ve_datos_base():
    """Datos a los que se AJUSTAN los modelos: los datos reales activos en la app o, si no hay, el Excel real del repositorio."""
    if st.session_state.fuente_datos == "real" and st.session_state.datos_reales is not None:
        cita = st.session_state.cita_datos_reales or "datos reales cargados en «Datos de prueba»"
        return st.session_state.datos_reales, cita
    if os.path.exists(VE_XLSX_BASE):
        return ve_leer_base(VE_XLSX_BASE), "datos_reales_coffea_2023.xlsx (Aguirre-Medina et al. 2023)"
    return None, None


def ve_capacidades(datos_paper, datos_base):
    """Qué validaciones permite cada variable del paper."""
    filas = []
    for v in VE_VARIABLES:
        if v not in datos_paper:
            continue
        grupos = datos_paper[v]
        n_m, n_p = len(grupos.get("-M", {})), len(grupos.get("+M", {}))
        en_base = datos_base is not None and v in datos_base
        filas.append({
            "Variable": VE_NOMBRE[v], "Fechas −M": n_m, "Fechas +M": n_p,
            "Predicho vs real": "✔" if en_base else "✗ no está en los datos ajustados",
            "Fechas no vistas": ("✔" if max(n_m, n_p) >= VE_MIN_FECHAS_HOLDOUT
                                 else f"✗ necesita ≥ {VE_MIN_FECHAS_HOLDOUT} fechas"),
            "Efecto del hongo": ("✔" if min(n_m, n_p) >= VE_MIN_FECHAS_EFECTO
                                 else "✗ necesita −M y +M" if min(n_m, n_p) == 0
                                 else f"✗ necesita ≥ {VE_MIN_FECHAS_EFECTO} fechas por grupo"),
        })
    return pd.DataFrame(filas)


def ve_parece_mismo_dataset(datos_paper, datos_base):
    comunes = iguales = 0
    for v, grupos in datos_paper.items():
        for g, serie in grupos.items():
            base = (datos_base or {}).get(v, {}).get(g, {})
            for d, x in serie.items():
                if d in base:
                    comunes += 1
                    iguales += abs(float(np.mean(base[d])) - x["media"]) <= 1e-6 * max(1.0, abs(x["media"]))
    return comunes >= 3 and iguales / comunes >= 0.9


# --- Modelos -------------------------------------------------------------------------------
def ve_valido(r):
    """Un ajuste sirve solo si convergió y su R² no es negativo (R² < 0 = la curva explica
    peor que una línea horizontal: ajuste degenerado)."""
    return (r is not None and not r.get("insuficiente") and r["params"] is not None
            and r["r2"] is not None and np.isfinite(r["r2"]) and r["r2"] >= 0)


def ve_elegir(res_vg, eleccion):
    ok = {m: r for m, r in res_vg.items() if ve_valido(r)}
    if not ok:
        return None, None
    if eleccion == "Mejor R²":
        m = max(ok, key=lambda k: ok[k]["r2"])
        return m, ok[m]
    return (eleccion, ok[eleccion]) if eleccion in ok else (None, None)


def ve_predecir(modelo, r, t):
    return MODELOS[modelo]["func"](np.asarray(t, dtype=float), *r["params"])


def ve_metricas(real, pred):
    real, pred = np.asarray(real, float), np.asarray(pred, float)
    if len(real) == 0:
        return dict(n=0, r2=np.nan, rmse=np.nan, mae=np.nan, mape=np.nan, sesgo=np.nan)
    ss_tot = np.sum((real - real.mean()) ** 2)
    return dict(n=len(real),
                r2=1 - np.sum((real - pred) ** 2) / ss_tot if len(real) >= 3 and ss_tot > 0 else np.nan,
                rmse=float(np.sqrt(np.mean((real - pred) ** 2))),
                mae=float(np.mean(np.abs(real - pred))),
                mape=float(np.mean(np.abs((pred - real) / real)) * 100),
                sesgo=float(np.mean(pred - real)))


def ve_desfase_estimado(paper, res_base):
    """Días a sumar al eje del paper para llevarlo a ddt. Devuelve (desfase, explicación)."""
    if paper["desfase"] is not None:
        return paper["desfase"], "indicado en la hoja «info» del Excel"
    if paper["origen"] == "trasplante":
        return 0.0, "el paper cuenta desde el trasplante, igual que la app"
    for v in ("altura", "biomasa", "hojas", "area_foliar", "diametro"):
        for g in ("-M", "+M"):
            serie = paper["datos"].get(v, {}).get(g)
            if not serie or v not in res_base or g not in res_base[v]:
                continue
            m, r = ve_elegir(res_base[v][g], "Mejor R²")
            if m is None:
                continue
            d0 = min(serie)
            try:
                t_eq = brentq(lambda t: ve_predecir(m, r, t) - serie[d0]["media"], 0.0, 400.0)
            except ValueError:
                continue
            return float(t_eq - d0), (f"estimada por tamaño: {VE_NOMBRE[v].lower()} {g} del paper el día "
                                      f"{d0:g} = la de sus plantas a {t_eq:.0f} ddt")
    return 0.0, "no se pudo estimar por tamaño; ajústela a mano"


def ve_ajustar_paper(serie, variable, grupo, desfase, dias):
    """Los 3 modelos de la app ajustados a las medias del paper, con el eje alineado a ddt."""
    datos = {variable: {grupo: {int(round(d + desfase)): np.array([serie[d]["media"]]) for d in dias}}}
    return ajustar_todos_los_modelos(datos)[variable][grupo]


def ve_calidad(mape):
    if not np.isfinite(mape):
        return "—"
    return "muy buena" if mape < 10 else "aceptable" if mape < 20 else "pobre"


# --- Gráficas ------------------------------------------------------------------------------
def ve_figura(titulo, eje_x, eje_y, alto=520, subtitulo=None, leyenda=True):
    """Figura base de Validación externa, con el mismo estilo que el resto de la app: título que
    dice la conclusión, subtítulo que explica cómo leerla, ejes limpios y leyenda abajo."""
    fig = go.Figure()
    fig.update_xaxes(title_text=eje_x)
    fig.update_yaxes(title_text=eje_y, rangemode="tozero")
    estilo_publicacion(fig, height=alto, titulo=titulo, subtitulo=subtitulo, mostrar_leyenda=leyenda,
                       espacio_leyenda_px=40)
    return fig


def ve_color(g):
    return COLOR_GRUPO[g]


def ve_barras(serie, dias):
    de = [serie[d]["de"] if serie[d]["de"] is not None else np.nan for d in dias]
    return None if all(np.isnan(de)) else de


def ve_trazar_real(fig, g, x, y, de=None, nombre="real", hover=None, relleno=False, row=None, col=None):
    """Medias reales: marcador hueco (o relleno), con ± DE si el Excel la trae."""
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers", name=f"{texto_grupo(g)} · {nombre}", legendgroup=g,
        marker=dict(symbol=VE_SIMBOLO[g], size=12, color=ve_color(g) if relleno else "white",
                    line=dict(color="white" if relleno else ve_color(g), width=1.5 if relleno else 2.4)),
        error_y=dict(type="data", array=de, color=ve_color(g), thickness=1.2, width=4) if de is not None else None,
        customdata=hover, hovertemplate="%{customdata}<extra></extra>" if hover is not None else None),
        row=row, col=col)


def ve_trazar_curva(fig, g, t, y, nombre, row=None, col=None, dash="solid"):
    fig.add_trace(go.Scatter(x=t, y=y, mode="lines", name=f"{texto_grupo(g)} · {nombre}", legendgroup=g,
                             line=dict(color=ve_color(g), width=2.6, dash=dash), hoverinfo="skip"),
                  row=row, col=col)


def ve_segmentos_error(fig, x, y_real, y_pred, g=None, row=None, col=None):
    """Línea punteada vertical entre lo real y lo predicho (el tamaño del error en cada fecha)."""
    xs, ys = [], []
    for xi, a, b in zip(x, y_real, y_pred):
        xs += [xi, xi, None]
        ys += [a, b, None]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", showlegend=False, hoverinfo="skip",
                             line=dict(color=ve_color(g) if g else G_MUTED, width=1.2, dash="dot")),
                  row=row, col=col)


def ve_zona(fig, x0, x1, texto, row=None, col=None):
    """Zona sombreada con su rótulo arriba (p. ej. «extrapolación», «fechas que el modelo no vio»)."""
    kw = dict(row=row, col=col) if row else {}
    fig.add_vrect(x0=x0, x1=x1, fillcolor="#F3EEE6", line_width=0, layer="below", **kw)
    xr = "x" if not col or col == 1 else f"x{col}"
    yr = "y" if not col or col == 1 else f"y{col}"
    fig.add_annotation(x=(x0 + x1) / 2, y=1, xref=xr, yref=f"{yr} domain", yanchor="top", showarrow=False,
                       text=texto, font=dict(family=FUENTE_PUBLICACION, size=11, color=G_MUTED))


def ve_cita_corta(cita):
    """'Ibarra-Puón JC, … (2014). Título…' -> 'Ibarra-Puón JC, … (2014)' (hasta el año)."""
    if not cita:
        return "paper cargado"
    m = re.search(r"\(\d{4}[a-z]?\)", cita)
    corta = cita[:m.end()] if m else cita
    return corta if len(corta) <= 90 else corta[:87] + "…"


def ve_texto_calidad(mape):
    q = ve_calidad(mape)
    color = {"muy buena": T["VERDE"], "aceptable": T["AMBAR"], "pobre": T["ROJO"]}.get(q, G_MUTED)
    return f"<span style='color:{color}'>({q})</span>"


def ve_fig_predicho_vs_real(var, series, ventana, t_max, cita):
    """Pestaña 2 en una sola figura: (a) curva predicha vs medias del paper, con el error de cada
    fecha y la zona de extrapolación; (b) predicho vs real, con la diagonal de predicción perfecta
    y una franja de ±10 %. `series` = {g: dict(m, r, x, real, pred, de, dias)}."""
    unidad = VE_UNIDAD[var]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.58, 0.42], horizontal_spacing=0.11)
    t0 = min(0, min(float(np.min(d["x"])) for d in series.values()))
    t = np.linspace(t0, t_max, 300)
    todos, mapes, etiquetas, peor = [], {}, [], None
    for g, d in series.items():
        ve_trazar_curva(fig, g, t, ve_predecir(d["m"], d["r"], t), f"predicho ({d['m']})", row=1, col=1)
        ve_segmentos_error(fig, d["x"], d["real"], d["pred"], g, row=1, col=1)
        hover = [f"{texto_grupo(g)} · día {dp_:g} del paper = {xd:.0f} ddt<br>real {y:.3g} · predicho {p:.3g} {unidad}"
                 for dp_, xd, y, p in zip(d["dias"], d["x"], d["real"], d["pred"])]
        ve_trazar_real(fig, g, d["x"], d["real"], d["de"], "media publicada ± DE", hover, row=1, col=1)
        err = (d["pred"] - d["real"]) / d["real"] * 100
        mapes[g] = float(np.mean(np.abs(err)))
        k = int(np.argmax(np.abs(err)))
        if peor is None or abs(err[k]) > abs(peor[3]):
            peor = (g, d["x"][k], d["real"][k], err[k])
        etiquetas.append((f"<b>{texto_grupo(g)}</b> · {d['m']}", t[-1], float(ve_predecir(d["m"], d["r"], t[-1]))))
        fig.add_trace(go.Scatter(
            x=d["real"], y=d["pred"], mode="markers+text", showlegend=False,
            marker=dict(symbol=VE_SIMBOLO[g], size=12, color=ve_color(g), line=dict(color="white", width=1.5)),
            text=[f"{xd:.0f} d" for xd in d["x"]], textposition="middle right" if g == "-M" else "middle left",
            textfont=dict(family=FUENTE_PUBLICACION, size=10.5, color=G_MUTED),
            hovertemplate=f"{texto_grupo(g)}<br>real %{{x:.3g}} · predicho %{{y:.3g}} {unidad}<extra></extra>"),
            row=1, col=2)
        todos += list(d["real"]) + list(d["pred"])
    if peor is not None and abs(peor[3]) >= 10:
        fig.add_annotation(x=peor[1], y=peor[2], xref="x", yref="y", ax=-60, ay=-40, showarrow=True, arrowhead=0,
                           arrowcolor=G_MUTED, arrowwidth=1, bgcolor="rgba(255,255,255,0.85)",
                           font=dict(family=FUENTE_PUBLICACION, size=11, color=G_INK),
                           text=f"día {peor[1]:.0f}: el modelo<br>{'sobreestima' if peor[3] > 0 else 'subestima'} "
                                f"{abs(peor[3]):.0f} %")
    y_max = max(todos) * 1.15
    rango_y = (0, y_max)
    etiquetas_fin_de_linea(fig, 1, etiquetas, rango_y, separacion_frac=0.06)
    if t_max > ventana[1]:
        ve_zona(fig, ventana[1], t_max, "extrapolación<br>(fuera de sus datos)", row=1, col=1)
    fig.add_annotation(x=(ventana[0] + ventana[1]) / 2, y=1, xref="x", yref="y domain", yanchor="top",
                       showarrow=False, text=f"rango de sus datos ({ventana[0]:.0f}–{ventana[1]:.0f} ddt)",
                       font=dict(family=FUENTE_PUBLICACION, size=11, color=G_MUTED))
    fig.update_xaxes(title_text="Días después del trasplante", range=[t0, t_max], row=1, col=1)
    fig.update_yaxes(title_text=f"{VE_NOMBRE[var]} ({unidad})", range=[0, y_max], row=1, col=1)

    tope = max(todos) * 1.12
    lin = np.array([0, tope])
    fig.add_trace(go.Scatter(x=np.r_[lin, lin[::-1]], y=np.r_[lin * 1.1, (lin * 0.9)[::-1]], mode="lines",
                             fill="toself", fillcolor="rgba(63,125,69,0.10)", line_width=0, showlegend=False,
                             hoverinfo="skip"), row=1, col=2)
    fig.add_trace(go.Scatter(x=lin, y=lin, mode="lines", showlegend=False, hoverinfo="skip",
                             line=dict(color=G_INK, width=1.2, dash="dash")), row=1, col=2)
    for x, y, txt, anc, color in ((0.03, 0.97, "▲ por encima: el modelo <b>sobreestima</b>", "left", G_MUTED),
                                  (0.97, 0.04, "▼ por debajo: el modelo <b>subestima</b>", "right", G_MUTED),
                                  (0.97, 0.97, "franja verde = error < 10 %", "right", T["VERDE"])):
        fig.add_annotation(x=x, y=y, xref="x2 domain", yref="y2 domain", xanchor=anc, showarrow=False, text=txt,
                           yanchor="top" if y > 0.5 else "bottom",
                           font=dict(family=FUENTE_PUBLICACION, size=11, color=color))
    fig.update_xaxes(title_text=f"Real, medido en el paper ({unidad})", range=[0, tope], row=1, col=2)
    fig.update_yaxes(title_text=f"Predicho por el modelo ({unidad})", range=[0, tope], row=1, col=2)

    peor_mape = max(mapes.values())
    titulo = (f"El modelo predice {VE_NOMBRE[var].lower()} de otro experimento con un error menor al 10 %"
              if peor_mape < 10 else
              f"El modelo predice {VE_NOMBRE[var].lower()} de otro experimento con un error medio de hasta "
              f"{peor_mape:.0f} %")
    chips = "   ·   ".join(f"<b>{texto_grupo(g)}</b> error medio <b>{v:.0f} %</b> {ve_texto_calidad(v)}"
                           for g, v in mapes.items())
    estilo_publicacion(fig, width=1200, height=640, titulo=titulo, right_margin=110, left_margin=80,
                       mostrar_leyenda=False,
                       subtitulo=f"Modelos ajustados a <b>sus datos</b>, sin cambiar parámetros, predicen un experimento "
                                 f"que <b>nunca vieron</b> ({cita})<br>{chips}", espacio_leyenda_px=40)
    for col, txt, sub in ((1, "(a) Curva predicha vs datos del paper",
                           "línea = predicción · marcador = media publicada ± DE · punteado = error"),
                          (2, "(b) Predicho vs real", "cada punto = una fecha del paper")):
        xr, yr = _ref_ejes(col)
        fig.add_annotation(xref=f"{xr} domain", yref=f"{yr} domain", x=0, y=1.03, xanchor="left", yanchor="bottom",
                           showarrow=False, align="left", font=dict(family=FUENTE_PUBLICACION, size=14, color=G_INK),
                           text=f"<b>{txt}</b><br><span style='font-size:11.5px;color:{G_MUTED}'>{sub}</span>")
    fig.update_layout(margin=dict(t=fig.layout.margin.t + 40))
    return fig, mapes


def ve_tabla(df, formato):
    st.dataframe(df.style.format(formato, na_rep="—"), hide_index=True, width="stretch")


def ve_ir_a_datos_de_prueba(clave):
    if st.button("Ir a Datos de prueba", key=clave):
        st.session_state.seccion = "Datos de prueba"
        st.rerun()


# --- Sección -------------------------------------------------------------------------------
def ve_render():
    st.markdown("### Validación externa")
    paper = st.session_state.ve_paper
    if paper is None:
        st.markdown("Compara lo que **predicen** los modelos con los datos **reales** de un experimento "
                    "independiente (un paper) que el modelo nunca vio.")
        st.info("Todavía no hay datos de un paper cargados. En **Datos → Datos de prueba**, bloque "
                "«Datos externos para validación», descarga la plantilla y sube el Excel del paper, "
                "o carga el ejemplo de Aguirre-Medina et al. (2011).")
        ve_ir_a_datos_de_prueba("ve_ir_sin_paper")
        return
    datos_base, origen_base = ve_datos_base()
    if datos_base is None:
        st.warning("No hay datos reales a los cuales ajustar los modelos. Cárgalos en «Datos de prueba».")
        ve_ir_a_datos_de_prueba("ve_ir_sin_base")
        return

    dp = paper["datos"]
    st.markdown(f"Datos reales del paper: **{paper['cita'] or 'paper sin cita (agrégala en la hoja «info»)'}**. "
                f"Modelos ajustados a: **{origen_base}**.")
    if ve_parece_mismo_dataset(dp, datos_base):
        st.warning("Los datos del paper coinciden con los datos a los que se ajustaron los modelos. Para que sea una validación **externa**, "
                   "deben venir de un experimento distinto.")

    res_base = ajustar_todos_los_modelos(datos_base)
    d_est, explicacion = ve_desfase_estimado(paper, res_base)
    dias_base = sorted({d for v in datos_base.values() for g in v.values() for d in g})
    ventana = (dias_base[0], dias_base[-1]) if dias_base else VE_VENTANA_DEFECTO

    c1, c2 = st.columns(2)
    eleccion = c1.selectbox("Modelo", VE_OPCIONES_MODELO, key="ve_modelo",
                            help="«Mejor R²» usa, en cada grupo, el modelo que mejor ajusta.")
    desfase = c2.slider("Alineación del tiempo (días)", -200, 200, int(round(d_est)),
                        key=f"ve_desfase_{st.session_state.ve_paper_id}",
                        help="Días que se suman al eje del paper para llevarlo a días después del trasplante (ddt).")
    st.caption(f"El paper cuenta desde: **{paper['origen']}**. Alineación sugerida: **{d_est:+.0f} días** "
               f"({explicacion}).")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["1 · Lo que predice el modelo", "2 · Predicho vs real",
                                            "3 · Fechas no vistas", "4 · Efecto del hongo", "5 · Datos del paper"])

    # --- 1 · Predicción del modelo ajustado ---------------------------------------------
    with tab1:
        st.markdown("#### ¿Qué valores predice el modelo?")
        st.write("Elija una variable y un día: el modelo ajustado a sus datos devuelve el valor predicho "
                 "para cada grupo.")
        vars_base = [v for v in VE_VARIABLES if v in res_base and {"-M", "+M"} <= set(res_base[v])]
        a, b = st.columns(2)
        var1 = a.selectbox("Variable", vars_base, key="ve_var1",
                           format_func=lambda v: f"{VE_NOMBRE[v]} ({VE_UNIDAD[v]})")
        dia1 = b.number_input("Día a predecir (ddt)", min_value=0, max_value=400, value=100, step=1, key="ve_dia1")
        modelos1 = {g: ve_elegir(res_base[var1][g], eleccion) for g in ("-M", "+M")}
        if any(m is None for m, _ in modelos1.values()):
            st.warning(f"«{eleccion}» no tiene un ajuste válido para {VE_NOMBRE[var1].lower()} en algún grupo. "
                       "Pruebe con «Mejor R²».")
        else:
            pred1 = {g: float(ve_predecir(m, r, dia1)) for g, (m, r) in modelos1.items()}
            k1, k2, k3 = st.columns(3)
            k1.metric(f"{VE_NOMBRE[var1]} predicha · −M", f"{pred1['-M']:.2f} {VE_UNIDAD[var1]}",
                      help=f"Modelo {modelos1['-M'][0]}")
            k2.metric(f"{VE_NOMBRE[var1]} predicha · +M", f"{pred1['+M']:.2f} {VE_UNIDAD[var1]}",
                      help=f"Modelo {modelos1['+M'][0]}")
            k3.metric("Efecto predicho del hongo", f"{100 * (pred1['+M'] - pred1['-M']) / pred1['-M']:+.1f} %")
            if not ventana[0] <= dia1 <= ventana[1]:
                st.info(f"El día {dia1} está fuera de la ventana medida ({ventana[0]}-{ventana[1]} ddt): "
                        "es una **extrapolación**, menos confiable.")
            filas = []
            for d in sorted(set(dias_base) | {int(dia1)}):
                pm, pp = (float(ve_predecir(*modelos1[g], d)) for g in ("-M", "+M"))
                filas.append({"Día (ddt)": d, f"−M predicho ({VE_UNIDAD[var1]})": pm,
                              f"+M predicho ({VE_UNIDAD[var1]})": pp, "Efecto (%)": 100 * (pp - pm) / pm,
                              "Tramo": "medido" if ventana[0] <= d <= ventana[1] else "extrapolación"})
            ve_tabla(pd.DataFrame(filas), {f"−M predicho ({VE_UNIDAD[var1]})": "{:.3f}",
                                           f"+M predicho ({VE_UNIDAD[var1]})": "{:.3f}", "Efecto (%)": "{:+.1f}"})
            efecto1 = 100 * (pred1["+M"] - pred1["-M"]) / pred1["-M"]
            fig = ve_figura(
                f"El día {dia1}, el modelo predice {pred1['+M']:.3g} {VE_UNIDAD[var1]} con micorriza y "
                f"{pred1['-M']:.3g} sin ella ({_fmt_signo(efecto1, 0)} %)",
                "Días después del trasplante", f"{VE_NOMBRE[var1]} ({VE_UNIDAD[var1]})", leyenda=False,
                subtitulo="Líneas = lo que predice el modelo ajustado a sus datos · marcadores = media ± DE de sus "
                          "datos · ✕ = el día que usted eligió")
            t = np.linspace(0, max(ventana[1] + 18, dia1 + 10), 300)
            etiquetas1 = []
            for g, (m, r) in modelos1.items():
                y_t = ve_predecir(m, r, t)
                ve_trazar_curva(fig, g, t, y_t, f"predicho ({m})")
                dias, medias, sds, _ = media_sd_por_dia(datos_base[var1][g])
                ve_trazar_real(fig, g, dias, medias, sds, "media de sus datos")
                fig.add_trace(go.Scatter(x=[dia1], y=[pred1[g]], mode="markers+text", showlegend=False,
                                         marker=dict(symbol="x", size=13, color=ve_color(g)),
                                         text=[f"{pred1[g]:.3g}"], textposition="middle left",
                                         textfont=dict(family=FUENTE_PUBLICACION, size=11, color=G_INK),
                                         hovertemplate=f"{VE_GRUPO_TXT[g]}<br>día {dia1}: {pred1[g]:.2f} "
                                                       f"{VE_UNIDAD[var1]}<extra></extra>"))
                etiquetas1.append((f"<b>{texto_grupo(g)}</b> · {m}", t[-1], float(y_t[-1])))
            y_vals = [v for g in modelos1 for v in ve_predecir(*modelos1[g], t)]
            etiquetas_fin_de_linea(fig, 1, etiquetas1, (0, max(y_vals)), separacion_frac=0.06)
            if t[-1] > ventana[1]:
                ve_zona(fig, ventana[1], t[-1], "extrapolación<br>(fuera de sus datos)")
            fig.update_layout(margin=dict(r=130))
            st.plotly_chart(fig, width="stretch")

    # --- 2 · El modelo ajustado predice el paper (validación externa estricta) --------------
    with tab2:
        st.markdown("#### Predicho por el modelo vs. real del paper")
        st.write("El modelo ajustado a **sus datos**, sin cambiar sus parámetros, predice los días del paper "
                 "**sin haberlos visto**, y se compara con lo que midieron los autores.")
        vars2 = [v for v in VE_VARIABLES if v in dp and v in res_base
                 and any(g in res_base[v] for g in dp[v])]
        if not vars2:
            st.info("Ninguna variable del paper está en los datos a los que se ajustaron los modelos, así que no hay nada que predecir. "
                    f"Variables del paper: {', '.join(VE_NOMBRE[v] for v in dp)}.")
        else:
            var2 = st.radio("Variable", vars2, horizontal=True, key="ve_var2",
                            format_func=lambda v: f"{VE_NOMBRE[v]} ({VE_UNIDAD[v]})")
            grupos2 = [g for g in ("-M", "+M") if g in dp[var2] and g in res_base[var2]]
            modelos2 = {g: ve_elegir(res_base[var2][g], eleccion) for g in grupos2}
            modelos2 = {g: mr for g, mr in modelos2.items() if mr[0] is not None}
            if not modelos2:
                st.warning("El modelo elegido no tiene un ajuste válido para esta variable. Pruebe con «Mejor R²».")
            else:
                filas, resumen, series2 = [], [], {}
                t_max = max(max(max(dp[var2][g]) for g in modelos2) + desfase, ventana[1]) + 10
                sesgos = []
                for g, (m, r) in modelos2.items():
                    serie = dp[var2][g]
                    dias = sorted(serie)
                    x = np.array(dias) + desfase
                    real = np.array([serie[d]["media"] for d in dias])
                    pred = ve_predecir(m, r, x)
                    for d, xd, y, p in zip(dias, x, real, pred):
                        filas.append({"Grupo": VE_GRUPO_TXT[g], "Día paper": d, "Día app (ddt)": round(xd),
                                      f"Predicho ({VE_UNIDAD[var2]})": p, f"Real ({VE_UNIDAD[var2]})": y,
                                      "Error (%)": 100 * (p - y) / y,
                                      "Tramo": "medido" if ventana[0] <= xd <= ventana[1] else "extrapolación"})
                    mt = ve_metricas(real, pred)
                    sesgos.append(mt["sesgo"])
                    resumen.append({"Grupo": VE_GRUPO_TXT[g], "Modelo": m, "Fechas": mt["n"], "R²": mt["r2"],
                                    "RMSE": mt["rmse"], "MAE": mt["mae"], "Error medio (%)": mt["mape"],
                                    "Calidad": ve_calidad(mt["mape"])})
                    series2[g] = dict(m=m, r=r, x=x, real=real, pred=pred, de=ve_barras(serie, dias), dias=dias)
                fig, _ = ve_fig_predicho_vs_real(var2, series2, ventana, t_max,
                                                 ve_cita_corta(paper["cita"]))
                st.plotly_chart(fig, width="stretch")
                ve_tabla(pd.DataFrame(filas), {"Día paper": "{:g}", f"Predicho ({VE_UNIDAD[var2]})": "{:.3f}",
                                               f"Real ({VE_UNIDAD[var2]})": "{:.3f}", "Error (%)": "{:+.1f}"})
                st.markdown("**Resumen del error**")
                ve_tabla(pd.DataFrame(resumen), {"R²": "{:.3f}", "RMSE": "{:.3f}", "MAE": "{:.3f}",
                                                 "Error medio (%)": "{:.1f}"})
                peor = max(r_["Error medio (%)"] for r_ in resumen)
                if peor < 10:
                    st.success("**Lectura:** el modelo ajustado a sus datos predice este experimento independiente "
                               "con un error menor al 10%: **los parámetros se transfieren** a estas condiciones.")
                elif peor < 20:
                    st.info("**Lectura:** el modelo predice este experimento con un error aceptable (10-20%).")
                else:
                    sentido = "sobreestima" if np.mean(sesgos) > 0 else "subestima"
                    st.info(f"**Lectura:** el modelo ajustado a sus datos **{sentido}** este experimento. Es "
                            "esperable si las condiciones (variedad, sustrato, manejo) difieren de las de sus datos: "
                            "**los parámetros no se transfieren** a otro vivero. Revise también la alineación del "
                            "tiempo, y la pestaña 3, que pone a prueba los modelos con el propio paper.")

    # --- 3 · Ajustar con las primeras fechas del paper, predecir las últimas -------------
    with tab3:
        st.markdown("#### Predicción de fechas que el modelo no vio")
        st.write("Los modelos se ajustan solo a las **primeras fechas** del paper y predicen las **últimas**, que se "
                 "ocultan. Así se pone a prueba la forma de los modelos sin depender de sus datos.")
        vars3 = [v for v in VE_VARIABLES if v in dp
                 and max(len(s) for s in dp[v].values()) >= VE_MIN_FECHAS_HOLDOUT]
        if not vars3:
            st.info(f"Ninguna variable del paper tiene al menos {VE_MIN_FECHAS_HOLDOUT} fechas en un grupo "
                    "(3 para ajustar y 1 para predecir).")
        else:
            a, b = st.columns(2)
            var3 = a.radio("Variable", vars3, horizontal=True, key="ve_var3",
                           format_func=lambda v: f"{VE_NOMBRE[v]} ({VE_UNIDAD[v]})")
            grupos3 = [g for g in ("-M", "+M") if len(dp[var3].get(g, {})) >= VE_MIN_FECHAS_HOLDOUT]
            n_max = min(len(dp[var3][g]) for g in grupos3) - 1
            if n_max > 3:
                n_ent = b.slider("Fechas usadas en el ajuste", 3, n_max, n_max,
                                 key=f"ve_nent_{st.session_state.ve_paper_id}_{var3}",
                                 help="Logístico y Gompertz necesitan al menos 3 fechas.")
            else:
                n_ent = 3
                b.caption("Con 4 fechas: se ajusta con las 3 primeras y se predice la última.")
            omitidos = [VE_GRUPO_TXT[g] for g in ("-M", "+M") if g in dp[var3] and g not in grupos3]
            if omitidos:
                st.caption(f"{', '.join(omitidos)}: menos de {VE_MIN_FECHAS_HOLDOUT} fechas, no se incluye.")
            filas, resumen, ajustes3 = [], [], {}
            for g in grupos3:
                serie = dp[var3][g]
                dias = sorted(serie)
                ent, pru = dias[:n_ent], dias[n_ent:]
                m, r = ve_elegir(ve_ajustar_paper(serie, var3, g, desfase, ent), eleccion)
                ajustes3[g] = (m, r, ent, pru)
                if m is None:
                    continue
                for d in dias:
                    y = serie[d]["media"]
                    p = float(ve_predecir(m, r, d + desfase))
                    filas.append({"Grupo": VE_GRUPO_TXT[g], "Día paper": d,
                                  "Uso": "ajuste" if d in ent else "A PREDECIR",
                                  f"Predicho ({VE_UNIDAD[var3]})": p, f"Real ({VE_UNIDAD[var3]})": y,
                                  "Error (%)": 100 * (p - y) / y})
                mt = ve_metricas([serie[d]["media"] for d in pru], ve_predecir(m, r, np.array(pru) + desfase))
                resumen.append({"Grupo": VE_GRUPO_TXT[g], "Modelo": m, "R² del ajuste": r["r2"],
                                "Fechas predichas": mt["n"], "Error medio en lo no visto (%)": mt["mape"],
                                "Calidad": ve_calidad(mt["mape"])})
            sin_ajuste = [VE_GRUPO_TXT[g] for g, (m, *_) in ajustes3.items() if m is None]
            if sin_ajuste:
                st.warning(f"Sin ajuste válido para {', '.join(sin_ajuste)} con «{eleccion}» y {n_ent} fechas. "
                           "Pruebe con «Mejor R²» o con más fechas en el ajuste.")
            if filas:
                ve_tabla(pd.DataFrame(filas), {"Día paper": "{:g}", f"Predicho ({VE_UNIDAD[var3]})": "{:.3f}",
                                               f"Real ({VE_UNIDAD[var3]})": "{:.3f}", "Error (%)": "{:+.1f}"})
                st.markdown("**Resumen: error en las fechas no vistas**")
                ve_tabla(pd.DataFrame(resumen), {"R² del ajuste": "{:.3f}",
                                                 "Error medio en lo no visto (%)": "{:.1f}"})
                errores3 = [r_["Error medio en lo no visto (%)"] for r_ in resumen
                            if np.isfinite(r_["Error medio en lo no visto (%)"])]
                titulo3 = (f"Ajustado con las primeras {n_ent} fechas, el modelo predice las siguientes con un "
                           f"error medio de hasta {max(errores3):.0f} %" if errores3 else
                           f"{VE_NOMBRE[var3]}: predicción de fechas no vistas")
                fig = ve_figura(titulo3, "Días después del trasplante (alineado)",
                                f"{VE_NOMBRE[var3]} ({VE_UNIDAD[var3]})", leyenda=False,
                                subtitulo="Marcadores huecos = fechas usadas para ajustar · rellenos = fechas que el "
                                          "modelo <b>no vio</b> y tuvo que predecir · punteado = error de la predicción")
                corte, x_fin, etiquetas3 = None, None, []
                for g, (m, r, ent, pru) in ajustes3.items():
                    if m is None:
                        continue
                    serie = dp[var3][g]
                    todos = np.array(ent + pru, dtype=float) + desfase
                    t = np.linspace(todos.min(), todos.max(), 300)
                    y_t = ve_predecir(m, r, t)
                    ve_trazar_curva(fig, g, t, y_t, f"modelo ({m})")
                    ve_trazar_real(fig, g, np.array(ent) + desfase, [serie[d]["media"] for d in ent],
                                   ve_barras(serie, ent), "real (usada en el ajuste)")
                    ve_trazar_real(fig, g, np.array(pru) + desfase, [serie[d]["media"] for d in pru],
                                   ve_barras(serie, pru), "real (a predecir)", relleno=True)
                    ve_segmentos_error(fig, np.array(pru) + desfase, [serie[d]["media"] for d in pru],
                                       ve_predecir(m, r, np.array(pru) + desfase), g)
                    corte = (ent[-1] + pru[0]) / 2 + desfase
                    x_fin = max(x_fin or todos.max(), todos.max())
                    etiquetas3.append((f"<b>{texto_grupo(g)}</b> · {m}", t[-1], float(y_t[-1])))
                if corte is not None:
                    margen_x = 0.04 * (x_fin - corte) + 2
                    ve_zona(fig, corte, x_fin + margen_x, "fechas que el<br>modelo no vio")
                    y_max3 = max(max(serie_["media"] for serie_ in dp[var3][g].values()) for g in ajustes3)
                    etiquetas_fin_de_linea(fig, 1, etiquetas3, (0, y_max3), separacion_frac=0.06)
                    fig.update_layout(margin=dict(r=130))
                st.plotly_chart(fig, width="stretch")

    # --- 4 · Efecto del hongo: real vs. modelado ------------------------------------------
    with tab4:
        st.markdown("#### Efecto de la inoculación: real vs. modelado")
        st.write("La app modela **todas** las fechas del paper para cada grupo y calcula cuánto más crece +M que −M "
                 "en cada fecha. Se compara con el efecto real que midieron los autores.")
        vars4 = [v for v in VE_VARIABLES if v in dp
                 and min(len(dp[v].get("-M", {})), len(dp[v].get("+M", {}))) >= VE_MIN_FECHAS_EFECTO]
        if not vars4:
            st.info(f"Hace falta al menos una variable con −M y +M y {VE_MIN_FECHAS_EFECTO} o más fechas por grupo.")
        else:
            var4 = st.radio("Variable", vars4, horizontal=True, key="ve_var4",
                            format_func=lambda v: f"{VE_NOMBRE[v]} ({VE_UNIDAD[v]})")
            series4 = {g: dp[var4][g] for g in ("-M", "+M")}
            ajustes4 = {g: ve_elegir(ve_ajustar_paper(series4[g], var4, g, desfase, sorted(series4[g])), eleccion)
                        for g in ("-M", "+M")}
            if any(m is None for m, _ in ajustes4.values()):
                st.warning("El modelo elegido no tiene un ajuste válido para esta variable. Pruebe con «Mejor R²».")
            else:
                comunes = sorted(set(series4["-M"]) & set(series4["+M"]))
                filas = []
                for d in comunes:
                    xm, xp = series4["-M"][d], series4["+M"][d]
                    rm, rp = xm["media"], xp["media"]
                    mm, mp = (float(ve_predecir(*ajustes4[g], d + desfase)) for g in ("-M", "+M"))
                    ef_r, ef_m = 100 * (rp - rm) / rm, 100 * (mp - mm) / mm
                    if None not in (xm["de"], xp["de"], xm["n"], xp["n"]):
                        p = ttest_ind_from_stats(rp, xp["de"], xp["n"], rm, xm["de"], xm["n"], equal_var=False).pvalue
                    else:
                        p = np.nan
                    coincide = ("sin diferencia real" if abs(ef_r) < 1 else
                                "✔ misma dirección" if np.sign(ef_r) == np.sign(ef_m) else "✗ dirección opuesta")
                    filas.append({"Día paper": d, "−M real": rm, "+M real": rp, "Efecto real (%)": ef_r,
                                  "−M modelado": mm, "+M modelado": mp, "Efecto modelado (%)": ef_m,
                                  "¿Coincide?": coincide, "p real (Welch)": p,
                                  "¿Significativo?": "—" if np.isnan(p) else ("sí" if p < 0.05 else "no")})
                df4 = pd.DataFrame(filas)
                con_dif = df4[df4["¿Coincide?"] != "sin diferencia real"] if not df4.empty else df4
                k1, k2, k3 = st.columns(3)
                k1.metric("Fechas con la misma dirección",
                          f"{(con_dif['¿Coincide?'] == '✔ misma dirección').sum()} de {len(con_dif)}"
                          if len(con_dif) else "—")
                k2.metric("R² de la app · −M", f"{ajustes4['-M'][1]['r2']:.3f}", help=ajustes4["-M"][0])
                k3.metric("R² de la app · +M", f"{ajustes4['+M'][1]['r2']:.3f}", help=ajustes4["+M"][0])
                if df4.empty:
                    st.info("−M y +M no se midieron en las mismas fechas, así que no hay efecto real que comparar.")
                else:
                    ve_tabla(df4, {"Día paper": "{:g}", "−M real": "{:.3f}", "+M real": "{:.3f}",
                                   "Efecto real (%)": "{:+.1f}", "−M modelado": "{:.3f}", "+M modelado": "{:.3f}",
                                   "Efecto modelado (%)": "{:+.1f}", "p real (Welch)": "{:.3f}"})
                todos = np.array(sorted(set(series4["-M"]) | set(series4["+M"])), dtype=float) + desfase
                t = np.linspace(todos.min(), todos.max(), 300)
                y = {g: ve_predecir(m, r, t) for g, (m, r) in ajustes4.items()}
                fig = ve_figura(f"{VE_NOMBRE[var4]} en el paper: datos reales y curvas ajustadas por la app",
                                "Días después del trasplante (alineado)", f"{VE_NOMBRE[var4]} ({VE_UNIDAD[var4]})",
                                leyenda=False,
                                subtitulo="Marcadores = media publicada ± DE · líneas = modelo ajustado a todas las "
                                          "fechas del paper, por grupo")
                etiquetas4 = []
                for g, (m, r) in ajustes4.items():
                    dias = sorted(series4[g])
                    ve_trazar_curva(fig, g, t, y[g], f"modelado ({m})")
                    ve_trazar_real(fig, g, np.array(dias) + desfase, [series4[g][d]["media"] for d in dias],
                                   ve_barras(series4[g], dias), "real")
                    etiquetas4.append((f"<b>{texto_grupo(g)}</b> · {m}", t[-1], float(y[g][-1])))
                etiquetas_fin_de_linea(fig, 1, etiquetas4, (0, max(float(np.max(v)) for v in y.values())),
                                       separacion_frac=0.06)
                fig.update_layout(margin=dict(r=130))
                st.plotly_chart(fig, width="stretch")

                efecto_t = 100 * (y["+M"] - y["-M"]) / y["-M"]
                if not df4.empty:
                    u = df4.iloc[-1]
                    titulo4 = (f"Efecto del hongo el día {u['Día paper']:g} del paper: real {_fmt_signo(u['Efecto real (%)'], 0)} %"
                               f" · modelado {_fmt_signo(u['Efecto modelado (%)'], 0)} %")
                else:
                    titulo4 = "Efecto del hongo (+M sobre −M) modelado por la app"
                fig2 = ve_figura(titulo4, "Días después del trasplante (alineado)", "+M sobre −M (%)", leyenda=True,
                                 subtitulo="Cuánto más (o menos) crece +M que −M · línea = lo que calcula la app · "
                                           "puntos = lo que midieron los autores · * = diferencia real significativa")
                fig2.add_hline(y=0, line=dict(color=G_INK, width=1))
                fig2.add_annotation(x=1, y=0, xref="x domain", yref="y", xanchor="right", yanchor="bottom",
                                    showarrow=False, text="0 % = sin efecto",
                                    font=dict(family=FUENTE_PUBLICACION, size=11, color=G_MUTED))
                fig2.add_trace(go.Scatter(x=t, y=efecto_t, mode="lines", name="efecto modelado por la app",
                                          line=dict(color=T["ACCENT"], width=2.6),
                                          hovertemplate="Día %{x:.0f}: %{y:+.1f} %<extra>modelado</extra>"))
                if not df4.empty:
                    fig2.add_trace(go.Scatter(
                        x=df4["Día paper"] + desfase, y=df4["Efecto real (%)"], mode="markers+text",
                        name="efecto real (paper)", marker=dict(size=11, color=G_INK, line=dict(color="white", width=1.5)),
                        text=["*" if s_ == "sí" else "" for s_ in df4["¿Significativo?"]], textposition="top center",
                        textfont=dict(size=18, color=G_INK),
                        hovertemplate="Día %{x:.0f}: %{y:+.1f} %<extra>real</extra>"))
                fig2.update_yaxes(rangemode="normal", ticksuffix=" %")
                st.plotly_chart(fig2, width="stretch")
                st.caption("\\* = diferencia real significativa (prueba t de Welch con la DE y el n del Excel). "
                           "Si el Excel no trae DE y n, no se calcula.")

    # --- 5 · Datos del paper ---------------------------------------------------------------
    with tab5:
        st.markdown("#### Datos reales cargados del paper")
        st.markdown(f"**Cita:** {paper['cita'] or '—'}  \n**Los días cuentan desde:** {paper['origen']}")
        st.markdown("**Qué permite validar cada variable**")
        st.dataframe(ve_capacidades(dp, datos_base), hide_index=True, width="stretch")
        for v in VE_VARIABLES:
            if v not in dp:
                continue
            st.markdown(f"**{VE_NOMBRE[v]} ({VE_UNIDAD[v]})**")
            dias = sorted(set().union(*[set(s) for s in dp[v].values()]))
            tabla = {"Día paper": dias}
            for g in ("-M", "+M"):
                if g in dp[v]:
                    s = dp[v][g]
                    tabla[f"{g} media"] = [s[d]["media"] if d in s else np.nan for d in dias]
                    tabla[f"{g} DE"] = [s[d]["de"] if d in s and s[d]["de"] is not None else np.nan for d in dias]
                    tabla[f"{g} n"] = [s[d]["n"] if d in s and s[d]["n"] is not None else np.nan for d in dias]
            df = pd.DataFrame(tabla)
            ve_tabla(df, {c: ("{:g}" if c == "Día paper" or c.endswith(" n") else "{:.3f}") for c in df.columns})
        ve_ir_a_datos_de_prueba("ve_ir_cambiar")


def ve_bloque_datos_de_prueba():
    """Bloque de «Datos de prueba» para cargar los datos independientes de un paper."""
    st.write("")
    st.markdown("### Datos externos para validación (paper)")
    st.markdown("Datos **independientes** de otro experimento publicado, con plantas sin inocular (−M) y/o "
                "inoculadas (+M). No reemplazan tus datos: se usan solo en **Análisis → Validación externa**, donde "
                "los modelos ajustados a tus datos reales se comparan con estos.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("Descargar plantilla del paper (Excel)", data=ve_plantilla_excel(),
                           file_name="plantilla_validacion_externa.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           width="stretch")
    with c2:
        if st.button("Cargar ejemplo: Aguirre-Medina et al. (2011)", width="stretch",
                     disabled=not os.path.exists(VE_XLSX_EJEMPLO)):
            paper, error = ve_leer_paper(VE_XLSX_EJEMPLO)
            if error:
                st.error(error)
            else:
                st.session_state.ve_paper, st.session_state.ve_paper_id = paper, "ejemplo"
                st.toast("Ejemplo cargado. Ve a Análisis → Validación externa.")
    with c3:
        if st.session_state.ve_paper is not None and st.button("Quitar datos del paper", width="stretch"):
            st.session_state.ve_paper, st.session_state.ve_paper_id = None, None
            st.rerun()

    archivo = st.file_uploader("Subir Excel del paper (.xlsx o .csv)", type=["xlsx", "csv"], key="uploader_paper")
    if archivo is not None and archivo.file_id != st.session_state.ve_ultimo_archivo:
        st.session_state.ve_ultimo_archivo = archivo.file_id
        paper, error = ve_leer_paper(archivo)
        if error:
            st.error(error)
        else:
            st.session_state.ve_paper, st.session_state.ve_paper_id = paper, archivo.file_id
            st.success(f"Datos del paper cargados ({', '.join(VE_NOMBRE[v] for v in VE_VARIABLES if v in paper['datos'])}).")

    paper = st.session_state.ve_paper
    if paper is not None:
        datos_base, _ = ve_datos_base()
        st.markdown(f"**Paper cargado:** {paper['cita'] or 'sin cita'} · días contados desde **{paper['origen']}**")
        st.dataframe(ve_capacidades(paper["datos"], datos_base), hide_index=True, width="stretch")
        if st.button("Ir a Validación externa", type="primary"):
            st.session_state.seccion = "Validación externa"
            st.rerun()


# ==============================================================================
# 3. BARRA LATERAL — navegación agrupada
# ==============================================================================
def nav_item(nombre):
    activo = st.session_state.seccion == nombre
    if st.button(nombre, key=f"nav_{nombre}", type=("primary" if activo else "secondary"), width='stretch'):
        st.session_state.seccion = nombre
        st.rerun()

with st.sidebar:
    st.markdown('<span class="eyebrow">Panel de control</span>', unsafe_allow_html=True)
    st.markdown(
        f'''<div style="display:flex; align-items:center; gap:0.45rem; margin:0 0 0.2rem 0;">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="{T['ACCENT']}"
             stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 20C4 10 10 4 20 4C20 14 14 20 4 20Z"/>
            <path d="M4 20C9 15 13 11 20 4"/>
        </svg>
        <span style="font-family:'Fraunces',serif; font-weight:600; font-size:1.3rem; color:{T['INK']};">Coffea arabica</span>
        </div>''',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="rule">', unsafe_allow_html=True)

    st.markdown('<span class="field-label">Principal</span>', unsafe_allow_html=True)
    nav_item("Resumen")

    st.markdown('<span class="field-label">Modelos</span>', unsafe_allow_html=True)
    nav_item("Ajustar modelos")

    st.markdown('<span class="field-label">Análisis</span>', unsafe_allow_html=True)
    nav_item("Metodología")
    nav_item("Resultados")
    nav_item("Gráficas de barras")
    nav_item("Resultados esperados")
    nav_item("Estadística")
    nav_item("Residuos")
    nav_item("Discusión y conclusiones")
    nav_item("Validación externa")

    st.markdown('<span class="field-label">Datos</span>', unsafe_allow_html=True)
    nav_item("Datos de prueba")
    nav_item("Exportar reporte")

    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    st.markdown('<span class="tag tag-control">−M control</span><span class="tag tag-tratado">+M inoculado</span>',
                unsafe_allow_html=True)
    fuente_txt = "Datos reales cargados" if st.session_state.fuente_datos == "real" else "Datos simulados de prueba"
    st.caption(f"Fuente actual: {fuente_txt}")
    if st.session_state.fuente_datos == "real" and st.session_state.cita_datos_reales:
        st.caption(f"📄 {st.session_state.cita_datos_reales}")

seccion = st.session_state.seccion
variables_a_mostrar = st.session_state.variables_incluidas
modelos_a_mostrar = st.session_state.modelos_incluidos


# ==============================================================================
# 4. BARRA SUPERIOR
# ==============================================================================
etiqueta_lote = ("Datos reales" if st.session_state.fuente_datos == "real" else f"Lote de datos #{st.session_state.lote}")
st.markdown(f"""
<div class="topbar">
    <span class="topbar-brand">Coffea IA · Modelado de crecimiento</span>
    <span class="topbar-tag">{etiqueta_lote} · Fase de prueba</span>
</div>
""", unsafe_allow_html=True)


# ==============================================================================
# SECCIÓN · RESUMEN
# ==============================================================================
if seccion == "Resumen":
    st.markdown("""<style>
    @keyframes entradaMetrica { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    [data-testid="stMetric"] { animation: entradaMetrica 0.45s ease-out both; }
    [data-testid="column"]:nth-of-type(1) [data-testid="stMetric"] { animation-delay: 0.00s; }
    [data-testid="column"]:nth-of-type(2) [data-testid="stMetric"] { animation-delay: 0.07s; }
    [data-testid="column"]:nth-of-type(3) [data-testid="stMetric"] { animation-delay: 0.14s; }
    [data-testid="column"]:nth-of-type(4) [data-testid="stMetric"] { animation-delay: 0.21s; }
    </style>""", unsafe_allow_html=True)
    st.title("Modelos matemáticos de crecimiento")
    st.markdown(
        f"Efecto de la inoculación con Hongos Micorrízicos Arbusculares (HMA) sobre el crecimiento en vivero — "
        f"<span style='color:{T['CONTROL']}'>plantas sin inocular (−M)</span> frente a "
        f"<span style='color:{T['ACCENT']}'>plantas inoculadas (+M)</span>.",
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="rule">', unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Duración del ensayo", "120 días")
    k2.metric("Réplicas por día", f"{N_REPLICAS}")
    k3.metric("Fuente de datos", "Real" if st.session_state.fuente_datos == "real" else "Simulada")
    if st.session_state.fuente_datos == "real" and st.session_state.cita_datos_reales:
        st.caption(f"📄 Fuente: {st.session_state.cita_datos_reales}")

    if st.session_state.ajustado:
        RES = st.session_state.resultados
        combos_validos = [
            (v, g, m, RES[v][g][m]["r2"]) for v in variables_a_mostrar for g in DATOS[v] for m in modelos_a_mostrar
            if RES[v][g][m]["r2"] is not None
        ]
        if combos_validos:
            mejor_global = max(combos_validos, key=lambda x: x[3])
            k4.metric("Estado del modelo", "Ajustado ✓", f"Mejor R² {mejor_global[3]:.3f}")
        else:
            k4.metric("Estado del modelo", "Ajustado ✓", "Sin curvas válidas")
    else:
        k4.metric("Estado del modelo", "Sin ajustar", "Ve a Modelos")

    st.write("")
    if not st.session_state.ajustado:
        with st.container(border=True):
            st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
            st.markdown('<span class="eyebrow">Siguiente paso</span>', unsafe_allow_html=True)
            st.markdown(
                "Todavía no se ha ejecutado el ajuste de los modelos. Ve a **Modelos → Ajustar "
                "modelos**, elige qué variables y modelos incluir, y presiona el botón."
            )
            if st.button("Ir a Ajustar modelos", type="primary"):
                st.session_state.seccion = "Ajustar modelos"
                st.rerun()
    else:
        with st.container(border=True):
            st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
            st.markdown('<span class="eyebrow">Estado</span>', unsafe_allow_html=True)
            st.markdown(
                f"Los modelos están ajustados sobre **{etiqueta_lote.lower()}** para: "
                f"{', '.join(NOMBRE_VARIABLE[v] for v in variables_a_mostrar)} · {', '.join(modelos_a_mostrar)}. "
                f"Consulta **Resultados**, **Estadística** o **Residuos** en el menú, o exporta el "
                f"**Reporte PDF** desde la categoría Datos."
            )


# ==============================================================================
# SECCIÓN · AJUSTAR MODELOS
# ==============================================================================
elif seccion == "Ajustar modelos":
    st.markdown("### Ajustar modelos")
    st.markdown(
        "Elige qué variables y qué modelos incluir, y presiona el botón para correr el ajuste. "
        "**Método:** mínimos cuadrados no lineales (`scipy.optimize.curve_fit`) sobre las "
        f"{N_REPLICAS} réplicas de cada día — no es una red neuronal ni requiere épocas/tasa de "
        "aprendizaje, porque estamos ajustando una curva matemática conocida."
    )
    st.write("")

    with st.container(border=True):
        st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Configuración del ajuste</span>', unsafe_allow_html=True)
        col_v, col_m = st.columns(2)
        with col_v:
            st.markdown('<span class="field-label">Variables a incluir</span>', unsafe_allow_html=True)
            chk_altura = st.checkbox("Altura", value="altura" in st.session_state.variables_incluidas, key="chk_var_altura")
            chk_biomasa = st.checkbox("Biomasa total (TDM)", value="biomasa" in st.session_state.variables_incluidas, key="chk_var_biomasa")
            chk_diametro = st.checkbox("Diámetro del tallo", value="diametro" in st.session_state.variables_incluidas, key="chk_var_diametro")
            chk_hojas = st.checkbox("Número de hojas", value="hojas" in st.session_state.variables_incluidas, key="chk_var_hojas")
            chk_area = st.checkbox("Área foliar", value="area_foliar" in st.session_state.variables_incluidas, key="chk_var_area")
        with col_m:
            st.markdown('<span class="field-label">Modelos a incluir</span>', unsafe_allow_html=True)
            chk_exp = st.checkbox("Exponencial", value="Exponencial" in st.session_state.modelos_incluidos, key="chk_mod_exp")
            chk_log = st.checkbox("Logístico", value="Logístico" in st.session_state.modelos_incluidos, key="chk_mod_log")
            chk_gom = st.checkbox("Gompertz", value="Gompertz" in st.session_state.modelos_incluidos, key="chk_mod_gom")

        st.write("")
        if st.button("Ajustar modelos", type="primary", width='stretch'):
            nuevas_vars = [v for v, on in [("altura", chk_altura), ("biomasa", chk_biomasa),
                                            ("diametro", chk_diametro), ("hojas", chk_hojas),
                                            ("area_foliar", chk_area)] if on]
            nuevos_mods = [m for m, on in [("Exponencial", chk_exp), ("Logístico", chk_log), ("Gompertz", chk_gom)] if on]
            if not nuevas_vars or not nuevos_mods:
                st.error("Selecciona al menos una variable y un modelo antes de ajustar.")
            else:
                with st.spinner("Ajustando modelos por mínimos cuadrados..."):
                    resultados = ajustar_todos_los_modelos(DATOS)
                st.session_state.resultados = resultados
                st.session_state.variables_incluidas = nuevas_vars
                st.session_state.modelos_incluidos = nuevos_mods
                st.session_state.ajustado = True
                st.session_state.recien_ajustado = True
                st.success(f"Modelos ajustados sobre {etiqueta_lote.lower()}.")

    if st.session_state.ajustado:
        st.write("")
        RES = st.session_state.resultados
        vars_ok = st.session_state.variables_incluidas
        mods_ok = st.session_state.modelos_incluidos

        if st.session_state.recien_ajustado:
            st.markdown(f"""<style>
            @keyframes pulsoAjuste {{ from {{ box-shadow: 0 0 0 3px {T['ACCENT']}55; }} to {{ box-shadow: 0 0 0 0 {T['ACCENT']}00; }} }}
            .pulso-ajuste {{ display: inline-block; animation: pulsoAjuste 1.1s ease-out both; border-radius: 4px; }}
            </style>""", unsafe_allow_html=True)
            st.markdown('<span class="eyebrow pulso-ajuste">Resultado inmediato del ajuste</span>', unsafe_allow_html=True)
            st.session_state.recien_ajustado = False
        else:
            st.markdown('<span class="eyebrow">Resultado inmediato del ajuste</span>', unsafe_allow_html=True)
        for variable in vars_ok:
            with st.container(border=True):
                st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
                st.markdown(f'<span class="card-title">{NOMBRE_VARIABLE[variable]}</span>', unsafe_allow_html=True)
                cols = st.columns(min(len(mods_ok) * 2, 6))
                idx = 0
                for grupo in DATOS[variable]:
                    for nombre_modelo in mods_ok:
                        res = RES[variable][grupo][nombre_modelo]
                        with cols[idx % len(cols)]:
                            clase_tag = "tag-control" if grupo == "-M" else "tag-tratado"
                            st.markdown(f'<span class="tag {clase_tag}">{grupo}</span> **{nombre_modelo}**',
                                        unsafe_allow_html=True)
                            st.markdown(badge_r2(res["r2"], res.get("insuficiente", False),
                                                  res.get("dias_disponibles"), res.get("dias_requeridos")),
                                        unsafe_allow_html=True)
                        idx += 1

                fig = go.Figure()
                todos_x, todos_y = [], []
                for grupo in DATOS[variable]:
                    mejor_m = max(mods_ok, key=lambda m: RES[variable][grupo][m]["r2"] if RES[variable][grupo][m]["r2"] is not None else -np.inf)
                    res = RES[variable][grupo][mejor_m]
                    if res["params"] is None:
                        continue
                    t_flat = res["t_flat"]
                    y_obs = np.array([v for d in sorted(DATOS[variable][grupo].keys()) for v in DATOS[variable][grupo][d]])
                    y_pred = MODELOS[mejor_m]["func"](t_flat, *res["params"])
                    fig.add_trace(go.Scatter(x=y_obs, y=y_pred, mode="markers",
                                              name=f"{texto_grupo(grupo)} · {mejor_m}",
                                              marker=dict(color=COLOR_GRUPO[grupo], size=8, opacity=0.75,
                                                          symbol="circle" if grupo == "-M" else "triangle-up",
                                                          line=dict(color="white", width=1))))
                    todos_x.extend(y_obs); todos_y.extend(y_pred)
                if todos_x:
                    lo, hi = float(min(todos_x + todos_y)), float(max(todos_x + todos_y))
                    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="Predicción perfecta",
                                              line=dict(color=G_INK, dash="dash", width=1.2)))
                if todos_x:
                    fig.update_layout(xaxis_title=f"Valor real ({UNIDADES[variable]})",
                                       yaxis_title=f"Valor predicho ({UNIDADES[variable]})")
                    estilo_publicacion(fig, height=400, titulo=f"Real vs. predicho — {NOMBRE_VARIABLE[variable]}",
                                       subtitulo="Cada punto = una planta, con el mejor modelo de su grupo · "
                                                 "mientras más cerca de la línea, mejor predice")
                    st.plotly_chart(fig, width='stretch')
                else:
                    st.info(
                        f"No se dibuja el gráfico Real vs. predicho para **{NOMBRE_VARIABLE[variable]}**: "
                        "ningún grupo tiene suficientes días distintos para ajustar una curva con los "
                        "modelos seleccionados (ver badges arriba)."
                    )
        st.caption("Para ver las curvas completas, la tabla de parámetros y la discusión, usa el menú de la izquierda.")


# ==============================================================================
# GUARDIA
# ==============================================================================
elif seccion in ("Resultados", "Gráficas de barras", "Resultados esperados", "Estadística", "Residuos",
                  "Discusión y conclusiones", "Exportar reporte") and not st.session_state.ajustado:
    st.markdown(f"### {seccion}")
    with st.container(border=True):
        st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
        st.markdown(
            "Aún no se ha ajustado ningún modelo. Ve a **Modelos → Ajustar modelos** para calcular "
            "los parámetros antes de ver esta sección."
        )
        if st.button("Ir a Ajustar modelos", type="primary"):
            st.session_state.seccion = "Ajustar modelos"
            st.rerun()


# ==============================================================================
# SECCIÓN · METODOLOGÍA
# ==============================================================================
elif seccion == "Metodología":
    st.markdown(f"""<style>
    /* Tratamiento editorial: numeral gigante y tenue de fondo en cada tarjeta de modelo */
    .numeral-fondo {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 7rem; color: {T['INK']};
        opacity: 0.05; position: absolute; right: 0.8rem; top: -0.5rem; line-height: 1;
        pointer-events: none; z-index: 0; }}
    </style>""", unsafe_allow_html=True)
    st.markdown("### ¿Por qué se comparan varios modelos?")
    st.markdown(
        "No sabemos de antemano cuál de las curvas clásicas de crecimiento describe mejor el "
        "comportamiento real de *Coffea arabica* con y sin HMA. Se ajustan varios modelos a los "
        "mismos datos y se comparan con métricas de bondad de ajuste (**R²** y **RMSE**) antes de "
        "elegir el definitivo."
    )
    st.write("")

    for nombre_modelo in MODELOS:
        info_txt = TEXTOS_MODELOS[nombre_modelo]
        with st.container(border=True):
            st.markdown(f'<span class="ficha-marca"></span><span class="numeral-fondo">{info_txt["num"]}</span>',
                        unsafe_allow_html=True)
            st.markdown(f'<span class="eyebrow">Modelo {info_txt["num"]}</span>', unsafe_allow_html=True)
            st.markdown(f"### {nombre_modelo}")
            col_eq, col_txt = st.columns([1, 2])
            with col_eq:
                st.latex(info_txt["ecuacion"])
                st.markdown('<span class="field-label">Parámetros</span>', unsafe_allow_html=True)
                for nombre_p, desc_p in info_txt["parametros"]:
                    st.markdown(f"`{nombre_p}` — {desc_p}")
            with col_txt:
                st.markdown('<span class="field-label">Supuesto biológico</span>', unsafe_allow_html=True)
                st.markdown(info_txt["supuesto"])
                st.markdown('<span class="field-label">Cuándo conviene usarlo?</span>', unsafe_allow_html=True)
                st.markdown(info_txt["cuando_usar"])
                st.markdown('<span class="field-label">Limitación</span>', unsafe_allow_html=True)
                st.markdown(info_txt["limitacion"])
        st.write("")

    with st.container(border=True):
        st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Origen de los datos</span>', unsafe_allow_html=True)
        st.markdown("### Naturaleza del dataset actual")
        st.markdown(
            f"""
- **t final = 120 días** (≈4 meses), duración típica de un ensayo de vivero.
- **{N_REPLICAS} réplicas por día y por grupo**, simuladas con ruido aleatorio para poder probar
  una prueba t/ANOVA real, mientras se consiguen los datos reales.
- **Con datos reales**, súbelos en formato largo desde *Datos de prueba* usando la plantilla.
- **Limitación a declarar:** los parámetros de forma (k, Ti) dependen de qué tan buena sea la
  cobertura temporal real de tus mediciones.
            """
        )


# ==============================================================================
# SECCIÓN · RESULTADOS
# ==============================================================================
elif seccion == "Resultados":
    st.markdown(f"""<style>
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .ficha-marca) {{
        transition: box-shadow 0.18s ease, border-color 0.18s ease, transform 0.18s ease; }}
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .ficha-marca):hover {{
        border-color: {T['ACCENT']}66 !important; transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(32,28,24,0.09); }}
    </style>""", unsafe_allow_html=True)
    RES = st.session_state.resultados

    st.caption(f"Mostrando {etiqueta_lote.lower()} · "
               f"{', '.join(NOMBRE_VARIABLE[v] for v in variables_a_mostrar)} · {', '.join(modelos_a_mostrar)}")

    for variable in variables_a_mostrar:
        st.markdown('<span class="eyebrow">Variable</span>', unsafe_allow_html=True)
        st.markdown(f"### {NOMBRE_VARIABLE[variable]} · {UNIDADES[variable]}")

        # Si NINGUN modelo seleccionado puede ajustarse en NINGUN grupo (dias
        # insuficientes), mostrar una comparacion simple del valor final real
        # en vez de un panel de graficos vacios. dias_disponibles es igual
        # para todos los modelos de una misma variable/grupo, así que basta
        # con leerlo del primero para el texto informativo.
        primer_modelo = modelos_a_mostrar[0]
        sin_curva = all(RES[variable][g][m].get("insuficiente", False)
                         for g in DATOS[variable] for m in modelos_a_mostrar)

        if sin_curva:
            dias_g, medias_g, _, ns_g = media_sd_por_dia(DATOS[variable]["-M"])
            dias_p, medias_p, _, ns_p = media_sd_por_dia(DATOS[variable]["+M"])
            dia_final = int(dias_g[-1])
            val_m, val_p = medias_g[-1], medias_p[-1]
            diff_pct = (val_p - val_m) / val_m * 100 if val_m != 0 else float("nan")

            with st.container(border=True):
                st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
                st.markdown(f'<span class="field-label">Comparación directa · día {dia_final} '
                             f'(sin curva: solo hay {int(RES[variable]["-M"][primer_modelo]["dias_disponibles"])} '
                             f'día de datos, se necesitan más para ajustar una curva)</span>', unsafe_allow_html=True)
                col_m, col_flecha, col_p = st.columns([2, 1, 2])
                with col_m:
                    st.metric(f"−M (control)", f"{val_m:.2f} {UNIDADES[variable]}",
                               help=f"n={int(ns_g[-1])} réplicas" if ns_g[-1] > 1 else None)
                with col_flecha:
                    st.markdown(f"<div style='text-align:center; padding-top:22px; font-family:IBM Plex Mono, monospace; "
                                f"color:{T['ACCENT']}; font-weight:700;'>{diff_pct:+.1f}%</div>", unsafe_allow_html=True)
                with col_p:
                    st.metric(f"+M (inoculado)", f"{val_p:.2f} {UNIDADES[variable]}",
                               help=f"n={int(ns_p[-1])} réplicas" if ns_p[-1] > 1 else None)
                if st.session_state.fuente_datos == "real" and st.session_state.cita_datos_reales:
                    st.caption(f"📄 Fuente: {st.session_state.cita_datos_reales}")
            st.write("")
            continue

        fig, pie = fig_curvas_publicacion(DATOS, RES, variable, modelos_a_mostrar, st.session_state.fuente_datos)
        st.plotly_chart(fig, width='stretch')
        mostrar_pie_streamlit(pie)
        st.download_button(
            f"Descargar PNG — Curvas {NOMBRE_VARIABLE[variable]}",
            data=componer_png_con_pie(fig.to_image(format="png", scale=3), pie),
            file_name=f"curvas_{variable}.png", mime="image/png", key=f"png_curvas_{variable}",
        )

        with st.expander(f"Tasas de crecimiento (AGR/RGR) — {NOMBRE_VARIABLE[variable]}"):
            st.caption(
                "Opcional: AGR (dP/dt) y RGR ((1/P)·dP/dt) del modelo con mejor R² en cada grupo, "
                "calculadas analíticamente a partir de los parámetros ya ajustados (sin reajustar)."
            )
            fig_tasas, pie_tasas_o_motivo = fig_tasas_crecimiento(
                DATOS, RES, variable, modelos_a_mostrar, st.session_state.fuente_datos)
            if fig_tasas is None:
                st.info(pie_tasas_o_motivo)
            else:
                st.plotly_chart(fig_tasas, width='stretch')
                mostrar_pie_streamlit(pie_tasas_o_motivo)
                st.download_button(
                    f"Descargar PNG — Tasas {NOMBRE_VARIABLE[variable]}",
                    data=componer_png_con_pie(fig_tasas.to_image(format="png", scale=3), pie_tasas_o_motivo),
                    file_name=f"tasas_{variable}.png", mime="image/png", key=f"png_tasas_{variable}",
                )

        filas = []
        for grupo in DATOS[variable]:
            for nombre_modelo in modelos_a_mostrar:
                res = RES[variable][grupo][nombre_modelo]
                estado = estado_de_ajuste(res)
                filas.append({"Grupo": grupo, "Modelo": nombre_modelo, "Estado": estado,
                               "R²": round(res["r2"], 4) if not pd.isna(res["r2"]) else np.nan,
                               "RMSE": round(res["rmse"], 4) if not pd.isna(res["rmse"]) else np.nan,
                               "MAE": round(res["mae"], 4) if not pd.isna(res.get("mae")) else np.nan})
        df_tabla = pd.DataFrame(filas)
        with st.container(border=True):
            st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
            st.markdown('<span class="field-label">Tabla de ajuste</span>', unsafe_allow_html=True)
            estilo_tabla = (
                df_tabla.style
                .format(na_rep="–", precision=4, subset=["R²", "RMSE", "MAE"])
                .background_gradient(subset=["R²"], cmap="Greens", vmin=0.5, vmax=1.0)
                .map(lambda v: f"background-color: {T['CARD']}; color: {T['INK']};" if pd.isna(v) else "", subset=["R²"])
            )
            st.dataframe(estilo_tabla, width='stretch', hide_index=True)
            st.caption("'–': el modelo no convergió o no tuvo suficientes días de muestreo para este grupo/variable (ver columna Estado).")
        st.write("")


# ==============================================================================
# SECCIÓN · GRÁFICAS DE BARRAS
# ==============================================================================
elif seccion == "Gráficas de barras":
    RES = st.session_state.resultados
    st.markdown("### Gráficas de barras")
    st.markdown(
        "Comparación de medias por día (barras agrupadas −M vs +M), independiente de las curvas de "
        "crecimiento ya ajustadas en **Resultados**. Cada figura se puede descargar en PNG."
    )
    st.write("")

    for variable in variables_a_mostrar:
        fig_var, pie_var = fig_barras_variable(DATOS, variable, st.session_state.fuente_datos)
        st.plotly_chart(fig_var, width='stretch')
        mostrar_pie_streamlit(pie_var)
        st.download_button(
            f"Descargar PNG — {NOMBRE_VARIABLE[variable]}",
            data=componer_png_con_pie(fig_var.to_image(format="png", scale=3), pie_var),
            file_name=f"barras_{variable}.png", mime="image/png", key=f"png_barras_{variable}",
        )
        st.write("")

    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    st.markdown("### Resumen: efecto de la micorriza al final del ensayo")
    fig_resumen, pie_resumen = fig_resumen_efecto_final(DATOS, variables_a_mostrar, st.session_state.fuente_datos)
    if fig_resumen is None:
        st.info(pie_resumen)
    else:
        st.plotly_chart(fig_resumen, width='stretch')
        mostrar_pie_streamlit(pie_resumen)
        st.download_button(
            "Descargar PNG — Resumen del efecto",
            data=componer_png_con_pie(fig_resumen.to_image(format="png", scale=3), pie_resumen),
            file_name="barras_resumen_efecto.png", mime="image/png", key="png_barras_resumen",
        )

    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    st.markdown("### Comparación de R² por modelo")
    fig_r2, pie_r2 = fig_barras_r2_comparacion(RES, DATOS, variables_a_mostrar, modelos_a_mostrar)
    st.plotly_chart(fig_r2, width='stretch')
    mostrar_pie_streamlit(pie_r2)
    st.download_button(
        "Descargar PNG — Comparación de R²",
        data=componer_png_con_pie(fig_r2.to_image(format="png", scale=3), pie_r2),
        file_name="barras_r2_comparacion.png", mime="image/png", key="png_barras_r2",
    )
    st.caption("Estas gráficas también se incluyen en el reporte PDF (sección Exportar reporte).")


# ==============================================================================
# SECCIÓN · RESULTADOS ESPERADOS
# ==============================================================================
elif seccion == "Resultados esperados":
    RES = st.session_state.resultados
    st.markdown("### Resultados esperados")
    st.markdown(
        "Generado automáticamente a partir de los datos y el último ajuste. Cubre los dos resultados "
        "esperados del proyecto que se pueden calcular directamente con estos datos: **(1)** el modelo "
        "de crecimiento que mejor describe cada variable, y **(2)** el efecto de la inoculación "
        "micorrízica (+M vs −M). Los demás resultados esperados del proyecto (manuscrito para revista "
        "indexada, taller de capacitación, publicación colaborativa, guía técnica, ponencia) son "
        "entregables de gestión/difusión y no se calculan a partir de estos datos."
    )
    st.write("")

    if st.session_state.fuente_datos == "real":
        st.info(
            "**Nota metodológica.** Los datos provienen de Aguirre-Medina et al. (2023), Revista "
            "Fitotecnia Mexicana. Las réplicas individuales fueron generadas sintéticamente a partir "
            "de las medias y el CV% publicados en el artículo (no son mediciones planta por planta).",
            icon="📄",
        )
        st.write("")

    st.markdown('<span class="eyebrow">Resultado esperado 1 · Modelo que mejor describe cada variable</span>',
                unsafe_allow_html=True)
    if len(modelos_a_mostrar) < 3:
        st.caption(
            "Nota: el último ajuste solo incluyó " + ", ".join(modelos_a_mostrar) + ". Para comparar "
            "los tres modelos, vuelve a *Ajustar modelos* con Exponencial, Logístico y Gompertz activados."
        )
    st.caption("'–': el modelo no convergió o no tuvo suficientes días de muestreo (ver columna Nota).")
    for variable in variables_a_mostrar:
        filas_modelo, mejores = calcular_tabla_modelo(RES, DATOS, variable, modelos_a_mostrar)
        st.markdown(f"**{NOMBRE_VARIABLE[variable]}**")
        df_modelo = pd.DataFrame([{
            "Grupo": f["grupo"], "Modelo": f["modelo"],
            "R²": f"{f['r2']:.4f}" if f["r2"] is not None else "–",
            "RMSE": f"{f['rmse']:.4f}" if f["rmse"] is not None else "–",
            "MAE": f"{f['mae']:.4f}" if f["mae"] is not None else "–",
            "Mejor modelo": "⭐" if f["mejor"] else "", "Nota": f["nota"],
        } for f in filas_modelo])
        st.dataframe(df_modelo, width='stretch', hide_index=True)
        for grupo, mejor in mejores.items():
            st.caption(f"{grupo}: " + (f"mejor modelo = **{mejor}**." if mejor
                                        else "ningún modelo convergió con los datos actuales."))
        if any(f["nota"] == ESTADO_NO_CONVERGIO for f in filas_modelo):
            st.caption(f"ℹ️ {NOTA_NO_CONVERGENCIA_K}")
        st.write("")

    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Resultado esperado 2 · Efecto de la inoculación micorrízica (+M vs −M)</span>',
                unsafe_allow_html=True)
    for variable in variables_a_mostrar:
        filas_efecto = calcular_efecto_micorriza(DATOS, variable)
        st.markdown(f"**{NOMBRE_VARIABLE[variable]}**")
        if not filas_efecto:
            st.caption("No hay suficientes réplicas en ambos grupos para calcular el efecto.")
            continue
        df_efecto = pd.DataFrame([{
            "Día (ddt)": int(f["dia"]),
            f"Media −M ({UNIDADES[variable]})": round(f["media_control"], 2),
            f"Media +M ({UNIDADES[variable]})": round(f["media_tratado"], 2),
            "Incremento +M vs −M (%)": round(f["incremento_pct"], 1),
            "t (Welch)": round(f["t"], 3), "p": round(f["p"], 4),
            "Significativo (p<0.05)": "Sí" if f["significativo"] else "No",
        } for f in filas_efecto])
        st.dataframe(df_efecto, width='stretch', hide_index=True)
        st.markdown(texto_interpretativo_efecto(variable, filas_efecto[-1]))
        st.write("")

    st.caption("Ambos resultados se incluyen en el reporte PDF (sección Exportar reporte).")


# ==============================================================================
# SECCIÓN · ESTADÍSTICA
# ==============================================================================
elif seccion == "Estadística":
    RES = st.session_state.resultados
    st.markdown("### Rigor estadístico del ajuste")
    st.markdown(
        "Dos cosas que un R² alto no te dice por sí solo: **qué tan preciso es cada parámetro "
        "estimado** (intervalos de confianza) y **si la diferencia entre −M y +M es "
        "estadísticamente significativa o podría deberse al azar** (prueba t con réplicas reales)."
    )
    st.write("")

    st.markdown('<span class="eyebrow">Prueba t independiente (Welch) · −M vs +M</span>', unsafe_allow_html=True)
    dias_comunes = sorted(set(DATOS[variables_a_mostrar[0]]["-M"].keys()))
    dia_sel = st.select_slider("Día (DAT) para comparar", options=dias_comunes, value=st.session_state.dia_ttest
                                if st.session_state.dia_ttest in dias_comunes else dias_comunes[-1], key="dia_ttest")

    for variable in variables_a_mostrar:
        resultado_t = prueba_t_independiente(DATOS, variable, dia_sel)
        with st.container(border=True):
            st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
            if resultado_t is None:
                st.markdown(f"**{NOMBRE_VARIABLE[variable]}** — no hay suficientes réplicas en el día {dia_sel} para esta prueba.")
                continue
            col_izq, col_der = st.columns([2, 1], gap="medium")
            with col_izq:
                st.markdown(f'<span class="card-title" style="font-size:1.1rem">{NOMBRE_VARIABLE[variable]}</span>',
                            unsafe_allow_html=True)
                st.caption(f"Día {dia_sel} DAT")
                interpretacion = (
                    f"Diferencia **estadísticamente significativa** entre −M y +M ({formatear_p(resultado_t['p'])} < 0.05)."
                    if resultado_t["significativo"] else
                    f"Diferencia **no significativa** entre −M y +M en este día ({formatear_p(resultado_t['p'])} ≥ 0.05)."
                )
                st.markdown(interpretacion)
                st.caption(
                    f"−M: {resultado_t['media_control']:.2f} ± {resultado_t['sd_control']:.2f} {UNIDADES[variable]} "
                    f"(n={resultado_t['n_control']}) · +M: {resultado_t['media_tratado']:.2f} ± {resultado_t['sd_tratado']:.2f} "
                    f"{UNIDADES[variable]} (n={resultado_t['n_tratado']}). Prueba t de Welch (dos muestras independientes)."
                )
            with col_der:
                m_t, m_p = st.columns(2)
                m_t.metric("Estadístico t", f"{resultado_t['t']:.3f}")
                m_p.metric("Valor p", f"{resultado_t['p']:.4f}")
            st.markdown(barra_valor_p(resultado_t["p"], resultado_t["significativo"]), unsafe_allow_html=True)
    st.write("")

    st.markdown('<span class="eyebrow">Intervalos de confianza (95%) de los parámetros</span>', unsafe_allow_html=True)
    for variable in variables_a_mostrar:
        st.markdown(f'<span class="card-title">{NOMBRE_VARIABLE[variable]}</span>', unsafe_allow_html=True)
        filas_ci = []
        for grupo in DATOS[variable]:
            for nombre_modelo in modelos_a_mostrar:
                res = RES[variable][grupo][nombre_modelo]
                if res["params"] is None:
                    filas_ci.append({"Grupo": grupo, "Modelo": nombre_modelo, "Parámetro": estado_de_ajuste(res),
                                      "Valor": "–", "IC 95% (inferior)": "–", "IC 95% (superior)": "–"})
                    continue
                nombres_p = MODELOS[nombre_modelo]["nombres_param"]
                for i, nombre_p in enumerate(nombres_p):
                    filas_ci.append({
                        "Grupo": grupo, "Modelo": nombre_modelo, "Parámetro": nombre_p,
                        "Valor": f"{res['params'][i]:.4f}",
                        "IC 95% (inferior)": f"{res['ci_bajo'][i]:.4f}",
                        "IC 95% (superior)": f"{res['ci_alto'][i]:.4f}",
                    })
        st.dataframe(pd.DataFrame(filas_ci), width='stretch', hide_index=True)
        st.caption("'–': el modelo no convergió o no tuvo suficientes días de muestreo.")
        st.write("")


# ==============================================================================
# SECCIÓN · RESIDUOS
# ==============================================================================
elif seccion == "Residuos":
    RES = st.session_state.resultados
    st.markdown("### Análisis de residuos")
    st.markdown(
        "El **residuo** es la diferencia entre lo que se midió en cada planta y lo que predice el modelo ese día "
        "(`residuo = medido − predicho`). Aquí se le aplica un **ANOVA a los residuos** para responder dos "
        "preguntas: **(1)** ¿el error del modelo cambia según el día (patrón sistemático)? y **(2)** ¿qué modelo "
        "se equivoca menos?"
    )

    def mostrar_explicacion_anova(tipo, frases, filas, primera_col):
        """Debajo de cada gráfica, en orden: «Qué dice aquí» (una tarjeta ✓/✗ por modelo o grupo),
        la tabla ANOVA, y lado a lado «Cómo leer esta gráfica» | «Qué significa cada columna»."""
        st.markdown('<span class="field-label">Qué dice aquí</span>', unsafe_allow_html=True)
        for col_st, v in zip(st.columns(len(frases)), frases):
            color = T["VERDE"] if v["ok"] else (T["ROJO"] if v["ok"] is False else T["INK_MUTED"])
            icono = "✓" if v["ok"] else ("✗" if v["ok"] is False else "•")
            detalle = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", v["detalle"])
            col_st.markdown(
                f"<div style='border:2px solid {color}; background:{color}10; border-radius:10px; "
                f"padding:0.7rem 0.9rem; height:100%;'>"
                f"<div style='color:{color}; font-weight:700; margin-bottom:0.3rem;'>{icono} {v['titulo']} "
                f"<span style='font-weight:500; font-size:0.85rem;'>· {v['etiqueta']}</span></div>"
                f"<div style='font-size:0.9rem; line-height:1.45;'>{detalle}</div></div>",
                unsafe_allow_html=True)
        if filas:
            st.write("")
            st.markdown('<span class="field-label">Tabla ANOVA</span>', unsafe_allow_html=True)
            df = tabla_anova_df(filas, primera_col, ANOVA_TEXTOS[tipo]["ok"], ANOVA_TEXTOS[tipo]["mal"])
            estilo_df = (df.style
                         .format({"SC": fmt_num, "CM": fmt_num, "F": "{:.2f}"}, na_rep="")
                         .map(lambda v: f"color: {T['VERDE']}; font-weight: 600;" if str(v).startswith("✓")
                              else (f"color: {T['ROJO']}; font-weight: 600;" if str(v).startswith("✗") else ""),
                              subset=["Interpretación"]))
            st.dataframe(estilo_df, hide_index=True, width="stretch")
        c_leer, c_glos = st.columns(2)
        with c_leer.container(border=True):
            st.markdown('<span class="field-label">Cómo leer esta gráfica</span>', unsafe_allow_html=True)
            st.markdown("\n".join(f"- **{t}:** {d}" for t, d in ANOVA_TEXTOS[tipo]["como_leer"]))
        if filas:
            with c_glos.container(border=True):
                st.markdown('<span class="field-label">Qué significa cada columna de la tabla</span>',
                            unsafe_allow_html=True)
                st.markdown("\n".join(f"- **{t}:** {d}" for t, d in glosario_anova(tipo)))

    tabs_var = st.tabs([NOMBRE_VARIABLE[v] for v in variables_a_mostrar])
    for tab, variable in zip(tabs_var, variables_a_mostrar):
        with tab:
            grupos_v = [g for g in ("-M", "+M") if g in DATOS[variable]]
            st.markdown('<span class="eyebrow">1 · ¿El error cambia según el día? · ANOVA residuo ~ día</span>',
                        unsafe_allow_html=True)
            for grupo in grupos_v:
                salida = fig_residuos_dia(RES, variable, grupo, modelos_a_mostrar)
                if salida is None:
                    st.info(f"{texto_grupo(grupo)}: ningún modelo convergió, no hay residuos que analizar.")
                    continue
                fig, filas, frases = salida
                st.plotly_chart(fig, width="stretch")
                mostrar_explicacion_anova("dia", frases, filas, "Modelo")
                if filas:
                    tabla = fig_tabla_anova(filas, "Modelo", ANOVA_TEXTOS["dia"]["ok"], ANOVA_TEXTOS["dia"]["mal"],
                                            "Tabla ANOVA · residuo ~ día")
                    st.download_button(
                        f"Descargar PNG — Residuos por día {texto_grupo(grupo)}",
                        data=png_anova_explicado(fig, tabla, "dia", frases),
                        file_name=f"anova_residuos_dia_{variable}_{'control' if grupo == '-M' else 'inoculado'}.png",
                        mime="image/png", key=f"png_anova_dia_{variable}_{grupo}")
                st.write("")

            st.markdown('<hr class="rule">', unsafe_allow_html=True)
            st.markdown('<span class="eyebrow">2 · ¿Qué modelo se equivoca menos? · ANOVA |residuo| ~ modelo</span>',
                        unsafe_allow_html=True)
            salida = fig_residuos_modelos(RES, variable, modelos_a_mostrar, grupos_v)
            if salida is None:
                st.info("Hacen falta al menos dos modelos ajustados en un grupo para compararlos.")
            else:
                fig, filas, frases = salida
                st.plotly_chart(fig, width="stretch")
                mostrar_explicacion_anova("modelo", frases, filas, "Grupo")
                if filas:
                    tabla = fig_tabla_anova(filas, "Grupo", ANOVA_TEXTOS["modelo"]["ok"],
                                            ANOVA_TEXTOS["modelo"]["mal"], "Tabla ANOVA · |residuo| ~ modelo")
                    st.download_button(
                        "Descargar PNG — Comparación de modelos",
                        data=png_anova_explicado(fig, tabla, "modelo", frases),
                        file_name=f"anova_residuos_modelos_{variable}.png", mime="image/png",
                        key=f"png_anova_modelos_{variable}")
            st.caption(
                "Limitaciones: el ANOVA por día no descuenta los parámetros que ya ajustó el modelo, así que marca "
                "«patrón» con algo más de facilidad que una prueba formal de falta de ajuste. En la comparación de "
                "modelos, las mismas plantas se usan para los tres modelos (los errores no son totalmente "
                "independientes): tómela como orientativa."
                + (" Con datos reales de pocas fechas (p. ej. 4 días), la prueba por día tiene pocos grados de "
                   "libertad y menos poder para detectar patrones." if st.session_state.fuente_datos == "real" else "")
            )


# ==============================================================================
# SECCIÓN · DISCUSIÓN Y CONCLUSIONES
# ==============================================================================
elif seccion == "Discusión y conclusiones":
    st.markdown(f"""<style>
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .ficha-marca) {{
        transition: box-shadow 0.18s ease, border-color 0.18s ease, transform 0.18s ease; }}
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .ficha-marca):hover {{
        border-color: {T['ACCENT']}66 !important; transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(32,28,24,0.09); }}
    </style>""", unsafe_allow_html=True)
    RES = st.session_state.resultados
    st.markdown("### Interpretación de los resultados")

    for variable in variables_a_mostrar:
        with st.container(border=True):
            st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
            st.markdown(f'<span class="eyebrow">{NOMBRE_VARIABLE[variable]}</span>', unsafe_allow_html=True)
            mejor_por_grupo = {}
            for grupo in DATOS[variable]:
                mejor = max(modelos_a_mostrar,
                            key=lambda m: RES[variable][grupo][m]["r2"] if RES[variable][grupo][m]["r2"] is not None else -np.inf)
                mejor_por_grupo[grupo] = mejor
            for grupo, mejor in mejor_por_grupo.items():
                r2_val = RES[variable][grupo][mejor]["r2"]
                if r2_val is None:
                    st.markdown(f"- Grupo **{grupo}**: no hay suficientes días de datos para ajustar una curva "
                                f"(se necesita más de un punto de tiempo).")
                else:
                    st.markdown(f"- Grupo **{grupo}**: mejor ajuste con **{mejor}** (R² = {r2_val:.3f}).")

            modelo_referencia = mejor_por_grupo["+M"]
            func_ref = MODELOS[modelo_referencia]["func"]
            val_final = {}
            for grupo in DATOS[variable]:
                params = RES[variable][grupo][modelo_referencia]["params"]
                val_final[grupo] = func_ref(120, *params) if params is not None else np.nan
            if all(not np.isnan(v) for v in val_final.values()) and val_final["-M"] > 0:
                diferencia_pct = (val_final["+M"] - val_final["-M"]) / val_final["-M"] * 100
                st.markdown(
                    f"- Con el modelo **{modelo_referencia}**, al día 120 la {NOMBRE_VARIABLE[variable].lower()} "
                    f"estimada es **{val_final['-M']:.2f} {UNIDADES[variable]}** (−M) frente a "
                    f"**{val_final['+M']:.2f} {UNIDADES[variable]}** (+M) — diferencia de **{diferencia_pct:+.1f}%**."
                )

            resultado_t = prueba_t_independiente(DATOS, variable, max(DATOS[variable]["-M"].keys()))
            if resultado_t is not None:
                st.markdown(
                    f"- La prueba t (día final) {'confirma' if resultado_t['significativo'] else 'no confirma'} "
                    f"que la diferencia sea estadísticamente significativa ({formatear_p(resultado_t['p'])})."
                )

    st.write("")
    with st.container(border=True):
        st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Conclusiones</span>', unsafe_allow_html=True)
        st.markdown(
            """
1. Los tres modelos se ajustan razonablemente, pero **Logístico y Gompertz** superan de forma
   consistente al **Exponencial** en R².
2. La elección final entre Logístico y Gompertz debe basarse en cuál describe mejor el patrón
   biológico observado, no solo en R²/RMSE.
3. El grupo **+M** muestra consistentemente valores más altos que **−M**, lo que —con datos
   reales— apoyaría la hipótesis de que la inoculación con HMA favorece el crecimiento.
            """
        )
    with st.container(border=True):
        st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Sugerencias</span>', unsafe_allow_html=True)
        st.markdown("\n".join(f"- {s}" for s in generar_sugerencias(st.session_state.fuente_datos)))


# ==============================================================================
# SECCIÓN · VALIDACIÓN EXTERNA
# ==============================================================================
elif seccion == "Validación externa":
    ve_render()


# ==============================================================================
# SECCIÓN · DATOS DE PRUEBA
# ==============================================================================
elif seccion == "Datos de prueba":
    st.markdown("### Generador de datos de prueba")
    st.markdown(
        f"Genera un nuevo lote de datos aleatorios ({N_REPLICAS} réplicas por día) para **altura** "
        "y **biomasa**. Al generar uno nuevo, el ajuste anterior queda invalidado."
    )
    st.write("")

    col_gen, col_real = st.columns(2)
    with col_gen:
        if st.button("Generar nuevo lote de datos aleatorios", type="primary", width='stretch'):
            st.session_state.semilla = int(np.random.randint(1, 999_999))
            st.session_state.lote += 1
            st.session_state.ajustado = False
            st.session_state.resultados = None
            st.session_state.fuente_datos = "simulado"
            st.session_state.datos_reales = None
            st.toast(f"Lote #{st.session_state.lote} generado. Ve a Ajustar modelos para recalcular.")
            st.rerun()
    with col_real:
        if st.session_state.fuente_datos == "real":
            if st.button("Volver a datos simulados", width='stretch'):
                st.session_state.fuente_datos = "simulado"
                st.session_state.ajustado = False
                st.session_state.resultados = None
                st.rerun()

    st.write("")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Fuente actual", "Real" if st.session_state.fuente_datos == "real" else f"Lote #{st.session_state.lote}")
    variable_kpi = "altura" if "altura" in DATOS else next(iter(DATOS))
    _, med_kpi_m, _, _ = media_sd_por_dia(DATOS[variable_kpi]["-M"])
    _, med_kpi_p, _, _ = media_sd_por_dia(DATOS[variable_kpi]["+M"])
    k2.metric(f"{NOMBRE_VARIABLE[variable_kpi]} final (−M)", f"{med_kpi_m[-1]:.2f} {UNIDADES[variable_kpi]}")
    k3.metric(f"{NOMBRE_VARIABLE[variable_kpi]} final (+M)", f"{med_kpi_p[-1]:.2f} {UNIDADES[variable_kpi]}")
    k4.metric("Réplicas por día", f"{N_REPLICAS}")

    st.write("")
    variables_todas = list(DATOS.keys())
    for fila_vars in [variables_todas[i:i+2] for i in range(0, len(variables_todas), 2)]:
        cols = st.columns(len(fila_vars))
        for col, variable in zip(cols, fila_vars):
            with col:
                st.markdown(f'<span class="field-label">Tabla · {NOMBRE_VARIABLE[variable]} (media ± DE por día)</span>', unsafe_allow_html=True)
                filas = []
                for grupo in DATOS[variable]:
                    dias_g, medias_g, sds_g, ns_g = media_sd_por_dia(DATOS[variable][grupo])
                    for d, m, s, n in zip(dias_g, medias_g, sds_g, ns_g):
                        filas.append({"DAT": int(d), "Grupo": grupo, "Media": round(m, 2), "DE": round(s, 2), "n": int(n)})
                df_resumen = pd.DataFrame(filas).sort_values(["DAT", "Grupo"])
                st.dataframe(df_resumen, width='stretch', hide_index=True, height=280)

    if st.session_state.fuente_datos != "real":
        st.caption(f"Identificador interno del lote (para reproducibilidad): semilla `{st.session_state.semilla}`")

    st.write("")
    st.markdown("### Cargar tus propios datos reales")
    st.markdown(
        "Cuando tengas las mediciones reales, descarga la plantilla, complétala con tus datos "
        "(formato **largo**: una fila por cada planta/réplica medida en cada día) y súbela aquí."
    )
    col_plantilla, col_subir = st.columns(2)
    with col_plantilla:
        st.download_button("Descargar plantilla (Excel)", data=generar_plantilla_excel(),
                            file_name="plantilla_datos_coffea.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width='stretch')
    with col_subir:
        archivo_subido = st.file_uploader("Subir archivo (.csv o .xlsx)", type=["csv", "xlsx"], key="uploader_datos_reales")

    if archivo_subido is not None and archivo_subido.file_id != st.session_state.get("ultimo_archivo_id"):
        datos_cargados, error = cargar_datos_desde_archivo(archivo_subido)
        st.session_state.ultimo_archivo_id = archivo_subido.file_id
        if error:
            st.error(error)
        else:
            st.session_state.datos_reales = datos_cargados
            st.session_state.fuente_datos = "real"
            st.session_state.ajustado = False
            st.session_state.resultados = None
            st.session_state.variables_incluidas = list(datos_cargados.keys())
            st.session_state.cita_datos_reales = ""
            st.success(
                f"Datos reales cargados correctamente ({', '.join(NOMBRE_VARIABLE.get(v, v) for v in datos_cargados)}). "
                "Ve a Modelos → Ajustar modelos para calcular con ellos."
            )

    if st.session_state.fuente_datos == "real":
        st.text_input(
            "Cita de la fuente (aparece en Resumen y en el reporte PDF)",
            key="cita_datos_reales",
            placeholder="Ej: Aguirre-Medina et al. (2023), Revista Fitotecnia Mexicana, DOI 10.35196/rfm.2023.3.273",
        )

    ve_bloque_datos_de_prueba()

    st.write("")
    st.markdown("### Descargar datos actuales")
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
        datos_a_formato_largo(DATOS).to_excel(writer, sheet_name="datos_largo", index=False)
        if st.session_state.ajustado:
            RES = st.session_state.resultados
            for variable in st.session_state.variables_incluidas:
                filas = []
                for grupo in DATOS[variable]:
                    for nombre_modelo in MODELOS:
                        res = RES[variable][grupo][nombre_modelo]
                        fila = {"Grupo": grupo, "Modelo": nombre_modelo, "Estado": estado_de_ajuste(res),
                                "R2": res["r2"], "RMSE": res["rmse"]}
                        if res["params"] is not None:
                            for np_, vp_ in zip(MODELOS[nombre_modelo]["nombres_param"], res["params"]):
                                fila[np_] = vp_
                        filas.append(fila)
                pd.DataFrame(filas).to_excel(writer, sheet_name=f"parametros_{variable}", index=False)

    st.download_button("Descargar Excel — datos" + (" y parámetros" if st.session_state.ajustado else ""),
                        data=buffer_excel.getvalue(), file_name="datos_coffea.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ==============================================================================
# SECCIÓN · EXPORTAR REPORTE (PDF)
# ==============================================================================
elif seccion == "Exportar reporte":
    RES = st.session_state.resultados
    st.markdown("### Exportar reporte en PDF")
    st.write("")

    with st.container(border=True):
        st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Reporte listo para anexar</span>', unsafe_allow_html=True)
        st.markdown(
            "Genera un PDF con el resumen del ajuste actual, listo para anexar a tu documento:"
        )
        st.markdown(
            "- Metodología breve de los tres modelos comparados\n"
            "- Tabla de R², RMSE y MAE por grupo y modelo (con el estado de cada ajuste)\n"
            "- Gráficas de curvas ajustadas por variable\n"
            "- Gráficas de barras por variable, resumen del efecto final y tabla de R² por modelo\n"
            "- Tasas de crecimiento (AGR y RGR) del modelo con mejor R² en cada grupo\n"
            "- Análisis de residuos con ANOVA (¿el error cambia según el día? ¿qué modelo se equivoca menos?)\n"
            "- Resultados esperados: mejor modelo por variable y efecto +M vs −M con prueba t\n"
            "- Conclusiones generales"
        )
        generar_pdf = st.button("Generar reporte PDF", type="primary")

    def limpiar_texto(s):
        reemplazos = {
            "−": "-", "·": "-", "→": "->", "²": "2", "±": "+/-", "–": "-", "—": "-",
            "‘": "'", "’": "'", "“": '"', "”": '"', "≥": ">=", "≤": "<=",
            "★": "*", "◇": "rombo", "◆": "rombo", "≈": "~", "÷": "/", "✓ ": "", "✗ ": "", "✓": "", "✗": "",
            "×": "x", "⁻¹": "^-1",
        }
        for a, b in reemplazos.items():
            s = s.replace(a, b)
        return s.encode("latin-1", "replace").decode("latin-1")

    # --- Paleta y helpers de formato del PDF (coherentes con el tema de la app) ---
    PDF_INK = (32, 28, 24)
    PDF_MUTED = (140, 133, 120)
    PDF_ACCENT = (168, 67, 43)
    PDF_HEADER_BG = (32, 28, 24)
    PDF_ROW_ALT = (241, 236, 227)

    class ReportePDF(FPDF):
        def header(self):
            if self.page_no() == 1:
                return
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*PDF_MUTED)
            self.cell(0, 8, limpiar_texto(f"Coffea IA - {etiqueta_lote}"), align="L")
            self.set_x(-40)
            self.cell(30, 8, datetime.now().strftime("%d/%m/%Y"), align="R", ln=1)
            self.set_draw_color(*PDF_MUTED)
            self.set_line_width(0.2)
            self.line(10, 16, 200, 16)
            self.ln(4)
            self.set_text_color(*PDF_INK)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*PDF_MUTED)
            self.cell(0, 10, limpiar_texto(f"Coffea IA - Modelado de crecimiento | Pagina {self.page_no()}/{{nb}}"),
                      align="C")

    def titulo_seccion(pdf, texto):
        if pdf.get_y() > 250:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*PDF_INK)
        pdf.cell(0, 9, limpiar_texto(texto), ln=1)
        pdf.set_draw_color(*PDF_ACCENT)
        pdf.set_line_width(0.8)
        y = pdf.get_y()
        pdf.line(10, y, 55, y)
        pdf.set_line_width(0.2)
        pdf.ln(5)

    def subtitulo_variable(pdf, texto):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*PDF_INK)
        pdf.cell(0, 8, limpiar_texto(texto), ln=1)
        pdf.ln(1)

    def lista_con_vinetas(pdf, items, numerada=False):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*PDF_INK)
        for i, item in enumerate(items, start=1):
            marca = f"{i}." if numerada else "-"
            pdf.set_x(14)
            pdf.multi_cell(0, 5.8, limpiar_texto(f"{marca} {item}"))
            pdf.ln(0.5)
        pdf.ln(2)

    def asegurar_espacio(pdf, alto_mm_necesario):
        if pdf.get_y() + alto_mm_necesario > pdf.page_break_trigger:
            pdf.add_page()

    def insertar_imagen_png(pdf, png_bytes, ancho_mm=190):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            tmp_img.write(png_bytes)
            ruta_img = tmp_img.name
        with Image.open(ruta_img) as im:
            proporcion = im.height / im.width
        alto_mm = ancho_mm * proporcion
        asegurar_espacio(pdf, alto_mm + 6)
        pdf.image(ruta_img, w=ancho_mm)
        pdf.ln(5)

    def insertar_pie_pdf(pdf, pie):
        """Pie de figura como texto debajo de la imagen (principio de diseño: la figura de
        Plotly no lleva pie incrustado -- ver construir_pie/mostrar_pie_streamlit)."""
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*PDF_MUTED)
        pdf.multi_cell(0, 5, limpiar_texto(pie["descripcion"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if pie["notas"]:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, limpiar_texto(pie.get("titulo_notas", "Notas:")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 9)
            for nota in pie["notas"]:
                pdf.set_x(14)
                pdf.multi_cell(0, 5, limpiar_texto(f"- {nota}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if pie["extra"]:
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.multi_cell(0, 5, limpiar_texto(pie["extra"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*PDF_INK)
        pdf.ln(3)

    def tabla_pdf(pdf, encabezados, anchos, filas):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(*PDF_HEADER_BG)
        pdf.set_text_color(255, 255, 255)
        for enc, w in zip(encabezados, anchos):
            pdf.cell(w, 7, limpiar_texto(enc), border=0, align="C", fill=True)
        pdf.ln()
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*PDF_INK)
        for i, fila in enumerate(filas):
            pdf.set_fill_color(*(PDF_ROW_ALT if i % 2 == 0 else (255, 255, 255)))
            for val, w in zip(fila, anchos):
                pdf.cell(w, 6.5, limpiar_texto(str(val)), border=0, align="C", fill=True)
            pdf.ln()
        pdf.ln(4)

    if generar_pdf:
        with st.spinner("Generando PDF..."):
            pdf = ReportePDF()
            pdf.alias_nb_pages()
            pdf.set_auto_page_break(auto=True, margin=18)
            pdf.add_page()

            # --- Portada / encabezado ---
            pdf.set_font("Helvetica", "B", 20)
            pdf.set_text_color(*PDF_INK)
            pdf.cell(0, 12, limpiar_texto("Coffea arabica - Modelos de crecimiento"), ln=1)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*PDF_MUTED)
            fuente_txt = "Datos reales" if st.session_state.fuente_datos == "real" else etiqueta_lote
            pdf.cell(0, 6, limpiar_texto(f"{fuente_txt} | Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}"), ln=1)
            if st.session_state.fuente_datos == "real" and st.session_state.cita_datos_reales:
                pdf.set_font("Helvetica", "I", 9)
                pdf.multi_cell(0, 5, limpiar_texto(f"Fuente: {st.session_state.cita_datos_reales}"))
            pdf.set_text_color(*PDF_INK)
            pdf.set_draw_color(*PDF_ACCENT)
            pdf.set_line_width(1.0)
            pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
            pdf.set_line_width(0.2)
            pdf.ln(10)

            # --- Metodologia ---
            titulo_seccion(pdf, "Metodologia")
            pdf.set_font("Helvetica", "", 10)
            texto_metodo = (
                "Se compararon tres modelos de crecimiento (Exponencial, Logistico, Gompertz) "
                "ajustados por minimos cuadrados no lineales (scipy.optimize.curve_fit) sobre "
                f"{N_REPLICAS} replicas por dia, para dos grupos: -M (sin inocular, control) y "
                "+M (inoculado con hongos micorrizicos arbusculares)."
            )
            pdf.multi_cell(0, 5.8, limpiar_texto(texto_metodo))
            pdf.ln(6)

            # --- Resultados por variable ---
            for variable in variables_a_mostrar:
                asegurar_espacio(pdf, 40)
                titulo_seccion(pdf, f"Resultados - {NOMBRE_VARIABLE[variable]}")

                sin_curva = all(RES[variable][g][m].get("insuficiente", False)
                                 for g in DATOS[variable] for m in modelos_a_mostrar)

                if sin_curva:
                    dias_g, medias_g, _, _ = media_sd_por_dia(DATOS[variable]["-M"])
                    dias_p, medias_p, _, _ = media_sd_por_dia(DATOS[variable]["+M"])
                    dia_final = int(dias_g[-1])
                    val_m, val_p = medias_g[-1], medias_p[-1]
                    diff_pct = (val_p - val_m) / val_m * 100 if val_m != 0 else float("nan")
                    pdf.set_font("Helvetica", "", 10)
                    pdf.multi_cell(0, 5.8, limpiar_texto(
                        f"Comparacion directa, dia {dia_final} (sin curva: dias insuficientes para ajustar un "
                        f"modelo): -M = {val_m:.2f} {UNIDADES[variable]} | +M = {val_p:.2f} {UNIDADES[variable]} "
                        f"| diferencia = {diff_pct:+.1f}%"
                    ))
                    pdf.ln(4)
                    continue

                # Tabla de R2/RMSE/MAE
                anchos = [18, 24, 46, 20, 20, 20]
                encabezados = ["Grupo", "Modelo", "Estado", "R2", "RMSE", "MAE"]
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_fill_color(*PDF_HEADER_BG)
                pdf.set_text_color(255, 255, 255)
                for enc, w in zip(encabezados, anchos):
                    pdf.cell(w, 7, enc, border=0, align="C", fill=True)
                pdf.ln()
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*PDF_INK)
                fila_i = 0
                for grupo in DATOS[variable]:
                    for nombre_modelo in modelos_a_mostrar:
                        res = RES[variable][grupo][nombre_modelo]
                        fila = [grupo, nombre_modelo, estado_de_ajuste(res),
                                f"{res['r2']:.4f}" if not pd.isna(res['r2']) else "-",
                                f"{res['rmse']:.4f}" if not pd.isna(res['rmse']) else "-",
                                f"{res.get('mae'):.4f}" if not pd.isna(res.get('mae')) else "-"]
                        pdf.set_fill_color(*(PDF_ROW_ALT if fila_i % 2 == 0 else (255, 255, 255)))
                        for val, w in zip(fila, anchos):
                            pdf.cell(w, 6.5, limpiar_texto(str(val)), border=0, align="C", fill=True)
                        pdf.ln()
                        fila_i += 1
                pdf.ln(4)

                # Grafica de curvas (misma figura que usa la seccion Resultados de la app),
                # solo si hay al menos un ajuste.
                hay_algun_ajuste = any(
                    RES[variable][g][m]["params"] is not None
                    for g in DATOS[variable] for m in modelos_a_mostrar
                )
                if hay_algun_ajuste:
                    fig_curvas_pdf, pie_curvas_pdf = fig_curvas_publicacion(
                        DATOS, RES, variable, modelos_a_mostrar, st.session_state.fuente_datos)
                    fig_curvas_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white")
                    insertar_imagen_png(pdf, fig_curvas_pdf.to_image(format="png", scale=3))
                    insertar_pie_pdf(pdf, pie_curvas_pdf)
                else:
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(*PDF_MUTED)
                    pdf.multi_cell(0, 5.5, limpiar_texto(
                        "No se dibuja grafica: ningun modelo pudo ajustarse para esta variable."
                    ))
                    pdf.set_text_color(*PDF_INK)
                    pdf.ln(3)

            # --- Graficas de barras (independientes de las curvas ya incluidas arriba) ---
            pdf.add_page()
            titulo_seccion(pdf, "Graficas de barras")
            for variable in variables_a_mostrar:
                asegurar_espacio(pdf, 100)
                subtitulo_variable(pdf, NOMBRE_VARIABLE[variable])
                fig_barra_pdf, pie_barra_pdf = fig_barras_variable(DATOS, variable, st.session_state.fuente_datos)
                fig_barra_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white")
                insertar_imagen_png(pdf, fig_barra_pdf.to_image(format="png", scale=3))
                insertar_pie_pdf(pdf, pie_barra_pdf)

            fig_resumen_pdf, pie_resumen_pdf = fig_resumen_efecto_final(
                DATOS, variables_a_mostrar, st.session_state.fuente_datos)
            if fig_resumen_pdf is not None:
                asegurar_espacio(pdf, 90)
                subtitulo_variable(pdf, "Resumen: efecto de la micorriza al final del ensayo")
                insertar_imagen_png(pdf, fig_resumen_pdf.to_image(format="png", scale=3))
                insertar_pie_pdf(pdf, pie_resumen_pdf)

            asegurar_espacio(pdf, 100)
            subtitulo_variable(pdf, "Comparacion de R2 por modelo")
            fig_r2_pdf, pie_r2_pdf = fig_barras_r2_comparacion(RES, DATOS, variables_a_mostrar, modelos_a_mostrar)
            # No se fuerza "height": la tabla de calor calcula su alto segun el numero de filas.
            fig_r2_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            insertar_imagen_png(pdf, fig_r2_pdf.to_image(format="png", scale=3))
            insertar_pie_pdf(pdf, pie_r2_pdf)

            # --- Tasas de crecimiento (AGR y RGR) -- mismas figuras que el expander opcional
            # de la seccion Resultados en la app, del modelo con mejor R2 en cada grupo. ---
            pdf.add_page()
            titulo_seccion(pdf, "Tasas de crecimiento (AGR y RGR)")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5.5, limpiar_texto(
                "AGR (tasa de crecimiento absoluta, dP/dt) y RGR (tasa de crecimiento relativa, "
                "(1/P)*dP/dt) del modelo con mejor R2 en cada grupo, calculadas analiticamente a "
                "partir de los parametros ya ajustados (sin reajustar). Solo se muestran modelos "
                "convergidos."
            ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)
            for variable in variables_a_mostrar:
                asegurar_espacio(pdf, 100)
                subtitulo_variable(pdf, NOMBRE_VARIABLE[variable])
                fig_tasas_pdf, pie_tasas_pdf_o_motivo = fig_tasas_crecimiento(
                    DATOS, RES, variable, modelos_a_mostrar, st.session_state.fuente_datos)
                if fig_tasas_pdf is None:
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(*PDF_MUTED)
                    pdf.multi_cell(0, 5.5, limpiar_texto(pie_tasas_pdf_o_motivo), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.set_text_color(*PDF_INK)
                    pdf.ln(3)
                else:
                    fig_tasas_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white")
                    insertar_imagen_png(pdf, fig_tasas_pdf.to_image(format="png", scale=3))
                    insertar_pie_pdf(pdf, pie_tasas_pdf_o_motivo)

            # --- Analisis de residuos (ANOVA sobre los residuos) -- mismas figuras y tablas que la
            # seccion Residuos de la app, con su explicacion en texto. ---
            asegurar_espacio(pdf, 60)
            titulo_seccion(pdf, "Analisis de residuos (ANOVA)")
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5.5, limpiar_texto(
                "El residuo es lo que se midio en cada planta menos lo que predice el modelo ese dia. Se aplica "
                "un ANOVA de un factor a los residuos para responder: (1) residuo ~ dia: el error cambia segun "
                "el dia? (si p < 0.05, el modelo se equivoca de forma sistematica en ciertas etapas); "
                "(2) |residuo| ~ modelo: que modelo se equivoca menos? (letras de Tukey: misma letra = sin "
                "diferencia real)."
            ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)
            guia_mostrada = set()
            for variable in variables_a_mostrar:
                grupos_v = [g for g in ("-M", "+M") if g in DATOS[variable]]
                salidas = [("dia", "Modelo", "Tabla ANOVA - residuo ~ dia", fig_residuos_dia(RES, variable, g,
                                                                                         modelos_a_mostrar))
                           for g in grupos_v]
                salidas.append(("modelo", "Grupo", "Tabla ANOVA - |residuo| ~ modelo",
                                fig_residuos_modelos(RES, variable, modelos_a_mostrar, grupos_v)))
                imagenes = []
                for tipo, primera, titulo_tabla, salida in salidas:
                    if salida is None or not salida[1]:
                        continue
                    fig_r, filas_r, frases_r = salida
                    tabla_r = fig_tabla_anova(filas_r, primera, ANOVA_TEXTOS[tipo]["ok"], ANOVA_TEXTOS[tipo]["mal"],
                                              titulo_tabla)
                    imagenes.append(png_anova_explicado(fig_r, tabla_r, tipo, frases_r, scale=2,
                                                        incluir_guia=tipo not in guia_mostrada))
                    guia_mostrada.add(tipo)
                if not imagenes:
                    continue
                # El subtítulo de la variable va en la misma página que su primera imagen.
                with Image.open(io.BytesIO(imagenes[0])) as im0:
                    alto_primera_mm = 190 * im0.height / im0.width
                asegurar_espacio(pdf, alto_primera_mm + 16)
                subtitulo_variable(pdf, NOMBRE_VARIABLE[variable])
                for png_r in imagenes:
                    insertar_imagen_png(pdf, png_r)

            # --- Resultados esperados (modelo que mejor describe cada variable + efecto +M vs -M) ---
            pdf.add_page()
            titulo_seccion(pdf, "Resultados esperados")

            if st.session_state.fuente_datos == "real":
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(*PDF_MUTED)
                pdf.multi_cell(0, 5.2, limpiar_texto(
                    "Nota metodologica: los datos provienen de Aguirre-Medina et al. (2023), Revista "
                    "Fitotecnia Mexicana. Las replicas individuales fueron generadas sinteticamente a "
                    "partir de las medias y el CV% publicados en el articulo (no son mediciones planta "
                    "por planta)."
                ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(*PDF_INK)
                pdf.ln(3)

            subtitulo_variable(pdf, "Resultado esperado 1 - Modelo que mejor describe cada variable")
            hubo_no_convergencia = False
            for variable in variables_a_mostrar:
                filas_modelo, mejores = calcular_tabla_modelo(RES, DATOS, variable, modelos_a_mostrar)
                asegurar_espacio(pdf, 12 + 6.5 * len(filas_modelo))
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 7, limpiar_texto(NOMBRE_VARIABLE[variable]), ln=1)
                encabezados_m = ["Grupo", "Modelo", "R2", "RMSE", "MAE", "Mejor", "Nota"]
                anchos_m = [16, 24, 18, 18, 18, 16, 80]
                filas_pdf_m = [[
                    f["grupo"], f["modelo"],
                    f"{f['r2']:.4f}" if f["r2"] is not None else "-",
                    f"{f['rmse']:.4f}" if f["rmse"] is not None else "-",
                    f"{f['mae']:.4f}" if f["mae"] is not None else "-",
                    "Si" if f["mejor"] else "", f["nota"] or "-",
                ] for f in filas_modelo]
                tabla_pdf(pdf, encabezados_m, anchos_m, filas_pdf_m)
                for grupo, mejor in mejores.items():
                    pdf.set_font("Helvetica", "", 9)
                    pdf.multi_cell(0, 5.2, limpiar_texto(
                        f"{grupo}: " + (f"mejor modelo = {mejor}." if mejor
                                        else "ningun modelo convergio con los datos actuales.")
                    ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                if any(f["nota"] == ESTADO_NO_CONVERGIO for f in filas_modelo):
                    hubo_no_convergencia = True
                pdf.ln(2)
            if hubo_no_convergencia:
                pdf.set_font("Helvetica", "I", 8.5)
                pdf.set_text_color(*PDF_MUTED)
                pdf.multi_cell(0, 5, limpiar_texto(f"Nota: {NOTA_NO_CONVERGENCIA_K}"),
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(*PDF_INK)
            pdf.ln(4)

            subtitulo_variable(pdf, "Resultado esperado 2 - Efecto de la inoculacion micorrizica (+M vs -M)")
            for variable in variables_a_mostrar:
                filas_efecto = calcular_efecto_micorriza(DATOS, variable)
                asegurar_espacio(pdf, 20)
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 7, limpiar_texto(NOMBRE_VARIABLE[variable]), ln=1)
                if not filas_efecto:
                    pdf.set_font("Helvetica", "", 9)
                    pdf.multi_cell(0, 5.5, limpiar_texto(
                        "No hay suficientes replicas en ambos grupos para calcular el efecto."
                    ), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(2)
                    continue
                asegurar_espacio(pdf, 12 + 6.5 * len(filas_efecto))
                encabezados_e = ["Dia", "Media -M", "Media +M", "Increm. %", "t", "p", "Signif."]
                anchos_e = [16, 28, 28, 26, 20, 22, 20]
                filas_pdf_e = [[
                    int(f["dia"]), f"{f['media_control']:.2f}", f"{f['media_tratado']:.2f}",
                    f"{f['incremento_pct']:+.1f}", f"{f['t']:.3f}", f"{f['p']:.4f}",
                    "Si" if f["significativo"] else "No",
                ] for f in filas_efecto]
                tabla_pdf(pdf, encabezados_e, anchos_e, filas_pdf_e)
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5.5, limpiar_texto(texto_interpretativo_efecto(variable, filas_efecto[-1])),
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(3)

            # --- Comparacion visual -M vs +M (ilustracion esquematica) ---
            png_ilustracion = generar_ilustracion_plantas(DATOS, st.session_state.fuente_datos)
            if png_ilustracion is not None:
                pdf.add_page()
                titulo_seccion(pdf, "Comparacion visual -M vs +M")
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*PDF_MUTED)
                origen_pie = "los datos reales cargados" if st.session_state.fuente_datos == "real" else "los datos de prueba simulados"
                pdf.multi_cell(0, 5.2, limpiar_texto(
                    f"Ilustracion conceptual generada a partir de {origen_pie} en el ultimo dia de muestreo "
                    "disponible -- NO es una fotografia del experimento."
                ))
                pdf.set_text_color(*PDF_INK)
                pdf.ln(2)
                insertar_imagen_png(pdf, png_ilustracion)

            # --- Conclusiones ---
            pdf.add_page()
            titulo_seccion(pdf, "Conclusiones")
            conclusiones = [
                "Los tres modelos se ajustan razonablemente, pero conviene comparar R2 y RMSE por variable "
                "antes de elegir el definitivo, en vez de asumir que uno domina siempre.",
                "La eleccion final entre Logistico y Gompertz debe basarse en cual describe mejor el patron "
                "biologico observado, no solo en R2/RMSE.",
                "El grupo +M muestra consistentemente valores mas altos que -M, lo que apoyaria la hipotesis "
                "de que la inoculacion con HMA favorece el crecimiento.",
            ]
            lista_con_vinetas(pdf, conclusiones, numerada=True)

            # --- Sugerencias (dinamicas segun la fuente de datos) ---
            titulo_seccion(pdf, "Sugerencias")
            lista_con_vinetas(pdf, generar_sugerencias(st.session_state.fuente_datos), numerada=False)

            pdf_bytes = bytes(pdf.output())

        st.success("Reporte generado.")
        st.download_button("Descargar reporte PDF", data=pdf_bytes,
                            file_name="reporte_coffea_modelos.pdf", mime="application/pdf")
