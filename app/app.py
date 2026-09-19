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
import tempfile
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from scipy.optimize import curve_fit
from scipy.stats import t as t_dist, ttest_ind
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image

st.set_page_config(page_title="Coffea arabica · Modelos de crecimiento", page_icon="⸙", layout="wide")

UNIDADES = {"altura": "cm", "biomasa": "g", "diametro": "mm", "hojas": "unidades", "area_foliar": "cm²"}
NOMBRE_VARIABLE = {"altura": "Altura", "biomasa": "Biomasa total (TDM)",
                    "diametro": "Diámetro del tallo", "hojas": "Número de hojas",
                    "area_foliar": "Área foliar"}
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
    CONTROL="#8C8578",
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
# (pantalla, PNG y PDF). El template "cuaderno" de arriba define look-and-feel
# del dashboard interactivo, pero sus márgenes (l=10,r=10,b=10) asumen el
# auto-margin del navegador y no funcionan al exportar con kaleido (títulos y
# etiquetas se cortan o se encima). Esta función fija márgenes explícitos y
# saca la leyenda del área del título para que nunca se tapen entre sí.
# ==============================================================================
FUENTE_PUBLICACION = "Arial, Helvetica, sans-serif"


def estilo_publicacion(fig, height=420, right_margin=190, top_margin=70, bottom_margin=70, left_margin=70):
    """Plantilla visual única para toda gráfica exportable: fondo blanco, marco
    negro fino con ticks hacia afuera, cuadrícula tenue solo en Y, leyenda fuera
    del área de trazado (a la derecha), fuente y tamaños consistentes. No toca
    datos ni trazos, solo layout/ejes -- se llama al final de cada fig_*()."""
    # Si la figura no trae titulo propio (varias no lo usan a proposito, para no
    # chocar con subplot_titles), hay que fijar text="" explicitamente: si se deja
    # sin definir, Plotly.js renderiza el titulo como el texto literal "undefined".
    titulo_actual = fig.layout.title.text if fig.layout.title is not None else None
    fig.update_layout(
        font=dict(family=FUENTE_PUBLICACION, size=13, color="#1A1A1A"),
        paper_bgcolor="white", plot_bgcolor="white",
        title=dict(text=titulo_actual or "", font=dict(family=FUENTE_PUBLICACION, size=16, color="#1A1A1A"),
                    x=0.01, xanchor="left"),
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02,
                    bgcolor="rgba(255,255,255,0)", bordercolor="rgba(0,0,0,0)",
                    font=dict(family=FUENTE_PUBLICACION, size=12)),
        margin=dict(l=left_margin, r=right_margin, t=top_margin, b=bottom_margin),
        height=height,
    )
    fig.update_xaxes(
        showgrid=False, zeroline=False, showline=True, linewidth=1.3, linecolor="black", mirror=True,
        ticks="outside", tickwidth=1.2, ticklen=5,
        tickfont=dict(family=FUENTE_PUBLICACION, size=12, color="#1A1A1A"),
        title_font=dict(family=FUENTE_PUBLICACION, size=14, color="#1A1A1A"),
        automargin=True, title_standoff=14,
    )
    fig.update_yaxes(
        showgrid=True, gridcolor="rgba(0,0,0,0.10)", gridwidth=0.6, zeroline=False, showline=True,
        linewidth=1.3, linecolor="black", mirror=True, ticks="outside", tickwidth=1.2, ticklen=5,
        tickfont=dict(family=FUENTE_PUBLICACION, size=12, color="#1A1A1A"),
        title_font=dict(family=FUENTE_PUBLICACION, size=14, color="#1A1A1A"),
        automargin=True, title_standoff=14,
    )
    fig.update_annotations(font=dict(family=FUENTE_PUBLICACION, size=13, color="#1A1A1A"))
    return fig


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

# Patron de trama por grupo para las barras -- redundante con el color -M/+M que ya usa
# la app (T["CONTROL"]/T["ACCENT"]), para que las barras tambien se distingan sin color.
PATRON_GRUPO = {"-M": ".", "+M": "/"}


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


def fig_barras_variable(datos, variable, fuente_datos="simulado"):
    """Barras agrupadas -M vs +M por día: altura de barra = media de réplicas, con barras de
    error = desviación estándar, patrón de trama por grupo (redundante con el color, para que
    se distingan también en blanco y negro) y marcas de significancia (ns/*/**/***) sobre cada
    día -- reutilizando prueba_t_independiente ya existente, sin recalcular nada nuevo.
    Independiente de las curvas de crecimiento ya existentes."""
    dias_comunes = sorted(set(datos[variable].get("-M", {})) | set(datos[variable].get("+M", {})))
    fig = go.Figure()
    n_replicas_vistas = set()
    y_max_con_error = 0.0
    for grupo in ("-M", "+M"):
        if grupo not in datos[variable]:
            continue
        color = T["CONTROL"] if grupo == "-M" else T["ACCENT"]
        dias, medias, sds, ns = media_sd_por_dia(datos[variable][grupo])
        n_replicas_vistas.update(int(n) for n in ns)
        if len(medias):
            y_max_con_error = max(y_max_con_error, float(np.max(medias + sds)))
        fig.add_trace(go.Bar(
            x=[str(int(d)) for d in dias], y=medias, name=grupo,
            error_y=dict(type="data", array=sds, visible=True, color="#1A1A1A", thickness=1.3, width=5),
            marker=dict(color=color, line=dict(color="black", width=1),
                        pattern=dict(shape=PATRON_GRUPO[grupo], fillmode="overlay", fgcolor="#1A1A1A", size=5, solidity=0.3)),
        ))

    # Marcas de significancia sobre cada día con réplicas en ambos grupos: se anota el
    # resultado de la prueba t de Welch ya implementada (prueba_t_independiente), no se
    # calcula una prueba nueva ni se decide un umbral distinto al que ya usa la app (p<0.05).
    if "-M" in datos[variable] and "+M" in datos[variable]:
        y_rango = y_max_con_error if y_max_con_error > 0 else 1.0
        for dia in dias_comunes:
            resultado_t = prueba_t_independiente(datos, variable, dia)
            if resultado_t is None:
                continue
            y_top = max(resultado_t["media_control"] + resultado_t["sd_control"],
                        resultado_t["media_tratado"] + resultado_t["sd_tratado"])
            fig.add_annotation(
                x=str(int(dia)), y=y_top + 0.045 * y_rango, text=texto_significancia(resultado_t["p"]),
                showarrow=False, yanchor="bottom",
                font=dict(family=FUENTE_PUBLICACION, size=13, color="#1A1A1A"),
            )

    fig.update_layout(
        barmode="group",
        title=f"{NOMBRE_VARIABLE[variable]} por día — media ± DE",
        xaxis_title="Día después del trasplante (ddt)",
        yaxis_title=f"{NOMBRE_VARIABLE[variable]} ({UNIDADES[variable]})",
    )
    if y_max_con_error > 0:
        fig.update_yaxes(range=[0, y_max_con_error * 1.25])
    estilo_publicacion(fig, height=440)

    n_reps_txt = "/".join(str(n) for n in sorted(n_replicas_vistas)) if n_replicas_vistas else "?"
    pie = [
        f"{NOMBRE_VARIABLE[variable]} ({UNIDADES[variable]}), media ± DE, n = {n_reps_txt} réplicas por día y grupo.",
        "Significancia (prueba t de Welch, −M vs +M): ns = p ≥ 0.05 · * p < 0.05 · ** p < 0.01 · *** p < 0.001.",
    ]
    if fuente_datos == "real":
        pie.append("Réplicas sintéticas generadas a partir de medias y CV% publicados (Aguirre-Medina et al., 2023).")
    agregar_pie_figura(fig, pie)
    return fig


def fig_barras_resumen_2x2(datos, variables, fuente_datos="simulado"):
    """Figura resumen 2x2 con hasta 4 variables, etiquetas (a)-(d), ejes Y independientes por
    panel (cada variable tiene su propia unidad) y una sola leyenda. Complementa -- no
    reemplaza -- las figuras individuales por variable."""
    letras = ["a", "b", "c", "d"]
    vars_incluidas = variables[:4]
    cols_n = 2
    fig = make_subplots(
        rows=2, cols=cols_n,
        subplot_titles=[f"({letras[i]}) {NOMBRE_VARIABLE[v]}" for i, v in enumerate(vars_incluidas)],
        horizontal_spacing=0.18, vertical_spacing=0.18,
    )
    for idx, variable in enumerate(vars_incluidas):
        fila, col = idx // cols_n + 1, idx % cols_n + 1
        for grupo in ("-M", "+M"):
            if grupo not in datos[variable]:
                continue
            color = T["CONTROL"] if grupo == "-M" else T["ACCENT"]
            dias, medias, sds, _ = media_sd_por_dia(datos[variable][grupo])
            fig.add_trace(go.Bar(
                x=[str(int(d)) for d in dias], y=medias, name=grupo, legendgroup=grupo,
                showlegend=(idx == 0),
                error_y=dict(type="data", array=sds, visible=True, color="#1A1A1A", thickness=1.1, width=4),
                marker=dict(color=color, line=dict(color="black", width=1),
                            pattern=dict(shape=PATRON_GRUPO[grupo], fillmode="overlay", fgcolor="#1A1A1A", size=4, solidity=0.3)),
            ), row=fila, col=col)
        fig.update_xaxes(title_text="Día (ddt)", row=fila, col=col)
        fig.update_yaxes(title_text=UNIDADES[variable], row=fila, col=col)
    fig.update_layout(barmode="group")
    estilo_publicacion(fig, height=680, right_margin=170)
    pie = ["Media ± DE por día y grupo. Ejes Y independientes por panel (unidad propia de cada variable)."]
    if fuente_datos == "real":
        pie.append("Réplicas sintéticas generadas a partir de medias y CV% publicados (Aguirre-Medina et al., 2023).")
    agregar_pie_figura(fig, pie)
    return fig


def fig_barras_r2_comparacion(RES, datos, variables, modelos):
    """Cuadrícula 2x2 (una variable por subplot, no una fila de 4) del R² de cada modelo,
    dejando la barra en 0 con la etiqueta 'No convergió' o 'Sin días suficientes' donde
    corresponda. Eje Y siempre 0-1.15 (las barras parten de 0 -- no se recorta para
    exagerar diferencias). Mismo patrón+color por grupo que el resto de las gráficas."""
    n = len(variables)
    cols_n = min(n, 2)
    filas_n = -(-n // cols_n)  # ceil(n / cols_n)
    fig = make_subplots(rows=filas_n, cols=cols_n, subplot_titles=[NOMBRE_VARIABLE[v] for v in variables],
                         horizontal_spacing=0.12, vertical_spacing=0.16)

    leyenda_mostrada = set()
    for idx, variable in enumerate(variables):
        fila, col = idx // cols_n + 1, idx % cols_n + 1
        for grupo in datos[variable]:
            color = T["CONTROL"] if grupo == "-M" else T["ACCENT"]
            y_num, texto_num, y_nota, texto_nota = [], [], [], []
            for m in modelos:
                res = RES[variable][grupo][m]
                r2 = res["r2"]
                if res.get("insuficiente"):
                    y_num.append(None); texto_num.append("")
                    y_nota.append(0); texto_nota.append(ESTADO_SIN_DIAS)
                elif r2 is None or (isinstance(r2, float) and np.isnan(r2)):
                    y_num.append(None); texto_num.append("")
                    y_nota.append(0); texto_nota.append(ESTADO_NO_CONVERGIO)
                else:
                    y_num.append(round(r2, 3)); texto_num.append(f"{r2:.2f}")
                    y_nota.append(None); texto_nota.append("")
            mostrar_leyenda = grupo not in leyenda_mostrada
            marcador = dict(color=color, line=dict(color="black", width=1),
                             pattern=dict(shape=PATRON_GRUPO[grupo], fillmode="overlay",
                                          fgcolor="#1A1A1A", size=5, solidity=0.3))
            # `textangle` es un escalar por traza (no admite un valor distinto por barra), así
            # que las notas "no convergió"/"sin días suficientes" van en una traza aparte con
            # texto vertical (-90°): con el ángulo horizontal por defecto el texto es más ancho
            # que una sola barra y se encima con las etiquetas de las barras vecinas.
            fig.add_trace(go.Bar(x=modelos, y=y_num, name=grupo, legendgroup=grupo, showlegend=mostrar_leyenda,
                                  marker=marcador, text=texto_num, textposition="outside", cliponaxis=False,
                                  constraintext="none",
                                  textfont=dict(family=FUENTE_PUBLICACION, size=12, color="#1A1A1A")),
                          row=fila, col=col)
            fig.add_trace(go.Bar(x=modelos, y=y_nota, name=grupo, legendgroup=grupo, showlegend=False,
                                  marker=marcador, text=texto_nota, textposition="outside", cliponaxis=False,
                                  constraintext="none", textangle=-90,
                                  textfont=dict(family=FUENTE_PUBLICACION, size=12, color="#1A1A1A")),
                          row=fila, col=col)
            leyenda_mostrada.add(grupo)
        fig.update_yaxes(range=[0, 1.15], row=fila, col=col, tickmode="linear", tick0=0, dtick=0.2,
                          title_text=("R²" if col == 1 else None))
        fig.update_xaxes(row=fila, col=col, tickfont=dict(size=12))

    # Sin título interno: el encabezado "### Comparación de R² por modelo" ya lo pone la
    # sección que llama a esta función -- evita que título y subplot_titles se encimen.
    fig.update_layout(barmode="group", bargap=0.4, bargroupgap=0.3)
    estilo_publicacion(fig, height=460 if filas_n == 1 else 460 * filas_n, right_margin=190)
    return fig


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


def fig_curvas_publicacion(datos, RES, variable, modelos, fuente_datos="simulado"):
    """Curvas de crecimiento estilo publicación: panel (a) = -M, panel (b) = +M, con el mismo
    eje Y compartido. Puntos = TODAS las réplicas observadas (círculos vacíos, con
    transparencia), no solo la media. Un color + tipo de línea por modelo (MODELO_ESTILO,
    paleta colorblind-safe). Los modelos que no convergieron (o sin días suficientes) NO se
    dibujan -- se anotan en el pie de figura, igual que la asíntota K cuando no es plausible.
    No cambia el ajuste ni la regla de insuficiente/no convergió: solo lee RES."""
    grupos = [g for g in ("-M", "+M") if g in datos[variable]]
    dias_todos = sorted(set().union(*[set(datos[variable][g].keys()) for g in grupos]))
    t_fino = np.linspace(dias_todos[0], dias_todos[-1], 300)

    todos_los_valores = [v for g in grupos for vals in datos[variable][g].values() for v in vals]
    y_obs_min, y_obs_max = min(todos_los_valores), max(todos_los_valores)
    dia_min, dia_max = dias_todos[0], dias_todos[-1]

    # Techo/piso del eje Y calculados ANTES de dibujar nada (Tarea 1b): se usan tanto para
    # fijar el rango final del eje como para decidir, por modelo, si su banda de confianza
    # es "estable" (cabe razonablemente en el rango visible) o hay que omitirla en vez de
    # dejar que un pcov mal condicionado pinte un rectangulo solido de borde a borde.
    rango_total = max(y_obs_max - y_obs_min, 1e-6)
    y_bottom_cap = min(0, y_obs_min) - 0.05 * rango_total
    y_top_cap = y_obs_max * 1.25

    etiquetas_panel = {"-M": "(a) −M", "+M": "(b) +M"}
    fig = make_subplots(rows=1, cols=len(grupos), subplot_titles=[etiquetas_panel[g] for g in grupos],
                         horizontal_spacing=0.07, shared_yaxes=True)

    notas = []
    leyenda_mostrada = set()
    for col, grupo in enumerate(grupos, start=1):
        y_max_obs_grupo = max(v for vals in datos[variable][grupo].values() for v in vals)
        t_flat, y_flat = flatten_replicas(datos[variable][grupo])
        fig.add_trace(go.Scatter(
            x=t_flat, y=y_flat, mode="markers", name="Réplicas observadas",
            legendgroup="obs", showlegend=("obs" not in leyenda_mostrada),
            marker=dict(symbol="circle-open", color="#1A1A1A", size=7, opacity=0.55, line=dict(width=1.3)),
            hovertemplate=f"DAT %{{x}}<br>%{{y:.2f}} {UNIDADES[variable]}<extra></extra>",
        ), row=1, col=col)
        leyenda_mostrada.add("obs")

        for modelo in modelos:
            res = RES[variable][grupo][modelo]
            estilo = MODELO_ESTILO[modelo]
            if res.get("insuficiente"):
                notas.append(f"{modelo} ({grupo}): sin suficientes días de muestreo "
                              f"({res['dias_disponibles']}/{res['dias_requeridos']}).")
                continue
            r2 = res["r2"]
            r2_ok = r2 is not None and not (isinstance(r2, float) and np.isnan(r2))
            if res["params"] is None or not r2_ok:
                notas.append(f"{modelo} ({grupo}): no convergió.")
                continue

            func = MODELOS[modelo]["func"]
            y_fino = func(t_fino, *res["params"])
            tiene_k = MODELOS[modelo]["nombres_param"][0] == "K"

            # Si el modelo tiene K, el MISMO criterio de plausibilidad que decide la
            # asíntota (Tarea 1 de la sesión anterior) decide también si su fit es
            # "estable" -- si K no es plausible, no tiene sentido mostrar una banda de
            # incertidumbre de un ajuste que ya se considera poco confiable.
            dibujar_k, K, motivo_k = (_asintota_k_plausible(res, y_max_obs_grupo, dia_min, dia_max)
                                        if tiene_k else (True, None, None))

            # Banda de confianza del 95% (Monte Carlo sobre pcov, ya existente en la app):
            # se dibuja antes que la linea del modelo para que quede debajo. Se omite si el
            # modelo no es "estable" (K implausible) o si la banda numérica se dispara muy
            # por fuera del rango visible del eje Y -- en ambos casos, el motivo real es el
            # mismo: el ajuste está mal identificado con solo estos puntos, y una banda
            # gigante clippeada por Plotly termina pintando un rectangulo solido que oculta
            # los datos en vez de comunicar incertidumbre.
            banda_baja, banda_alta = calcular_banda_confianza(func, res["params"], res["pcov"], t_fino)
            dibujar_banda, motivo_banda = False, None
            if banda_baja is not None:
                if tiene_k and not dibujar_k:
                    motivo_banda = f"ajuste inestable ({motivo_k})"
                elif np.max(banda_alta) > 3 * y_top_cap or np.min(banda_baja) < 3 * y_bottom_cap - 2 * rango_total:
                    motivo_banda = "la incertidumbre del ajuste excede varias veces el rango visible"
                else:
                    dibujar_banda = True
            if dibujar_banda:
                # Recorte defensivo al rango visible: aunque la banda ya se consideró
                # "estable", puede sobresalir un poco por los bordes: no se agranda el
                # eje para acomodarla (mismo principio que la asíntota K).
                banda_alta_recortada = np.clip(banda_alta, y_bottom_cap, y_top_cap)
                banda_baja_recortada = np.clip(banda_baja, y_bottom_cap, y_top_cap)
                r, g, b = (int(estilo["color"][1:3], 16), int(estilo["color"][3:5], 16), int(estilo["color"][5:7], 16))
                fig.add_trace(go.Scatter(x=t_fino, y=banda_alta_recortada, mode="lines", line=dict(width=0),
                                          legendgroup=modelo, showlegend=False, hoverinfo="skip"), row=1, col=col)
                fig.add_trace(go.Scatter(x=t_fino, y=banda_baja_recortada, mode="lines", line=dict(width=0),
                                          fill="tonexty", fillcolor=f"rgba({r},{g},{b},0.15)",
                                          legendgroup=modelo, showlegend=False, hoverinfo="skip"), row=1, col=col)
            elif motivo_banda is not None:
                notas.append(f"{modelo} ({grupo}): banda de confianza no se dibuja ({motivo_banda}).")

            fig.add_trace(go.Scatter(
                x=t_fino, y=y_fino, mode="lines", name=f"{modelo} (R²={r2:.3f})",
                legendgroup=modelo, showlegend=(modelo not in leyenda_mostrada),
                line=dict(color=estilo["color"], dash=estilo["dash"], width=2.4),
            ), row=1, col=col)
            leyenda_mostrada.add(modelo)

            # El Exponencial (P0, r) no tiene asíntota: nunca entra aquí porque su primer
            # parámetro no se llama "K" (ver MODELOS). Solo Logístico y Gompertz la tienen.
            if tiene_k:
                if dibujar_k:
                    fig.add_trace(go.Scatter(
                        x=[t_fino[0], t_fino[-1]], y=[K, K], mode="lines", showlegend=False,
                        legendgroup=modelo, line=dict(color=estilo["color"], dash="dot", width=1.1),
                        hovertemplate=f"K ({modelo}) = {K:.2f} {UNIDADES[variable]}<extra></extra>",
                    ), row=1, col=col)
                else:
                    notas.append(f"{modelo} ({grupo}): asíntota K no se dibuja ({motivo_k}).")

        fig.update_xaxes(title_text="Día después del trasplante (ddt)", row=1, col=col)
        if col == 1:
            fig.update_yaxes(title_text=f"{NOMBRE_VARIABLE[variable]} ({UNIDADES[variable]})", row=1, col=col)

    # Eje Y limitado a ~1.25x el maximo observado (no a la curva/asintota ajustada): asi
    # ninguna curva ni asintota -- ni siquiera una que si paso el criterio de plausibilidad --
    # puede dominar la escala del panel. Si una K dibujada supera este techo, su linea queda
    # fuera de vista (no se agranda el eje para acomodarla).
    fig.update_yaxes(range=[y_bottom_cap, y_top_cap])
    # height=500 (no 440): con 4 entradas de leyenda (replicas + 3 modelos) kaleido a veces
    # corta la ultima entrada si el lienzo queda muy justo -- se confirmo comparando renders.
    estilo_publicacion(fig, height=500, right_margin=220)

    pie = [
        "Círculos = réplicas individuales observadas. Líneas = modelos convergidos (R² en la leyenda).",
        "Eje Y limitado a ~1.25× el máximo observado.",
        "Asíntota K (línea punteada fina): solo si el modelo convergió, R² ≥ 0.90,",
        "K ≤ 1.5× el máximo observado, y el punto de inflexión cae dentro de los días observados.",
    ]
    pie.extend(notas)
    if fuente_datos == "real":
        pie.append("Réplicas sintéticas generadas a partir de medias y CV% publicados (Aguirre-Medina et al., 2023).")
    agregar_pie_figura(fig, pie)
    return fig


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
    """AGR y RGR (Tarea 5, opcional) del modelo con MEJOR R² en cada grupo -- reutiliza
    calcular_tabla_modelo para decidir cuál es el mejor, sin duplicar ese criterio. Devuelve
    (fig, None) o (None, motivo) si ningún grupo tiene un modelo convergido."""
    grupos = [g for g in ("-M", "+M") if g in datos[variable]]
    _, mejores = calcular_tabla_modelo(RES, datos, variable, modelos)
    grupos_validos = [g for g in grupos if mejores.get(g)]
    if not grupos_validos:
        return None, "Ningún modelo convergió en ningún grupo: no hay tasas de crecimiento que calcular."

    dias_todos = sorted(set().union(*[set(datos[variable][g].keys()) for g in grupos]))
    t_fino = np.linspace(dias_todos[0], dias_todos[-1], 300)
    etiqueta_agr = {"-M": "(c) AGR −M", "+M": "(d) AGR +M"}
    etiqueta_rgr = {"-M": "(e) RGR −M", "+M": "(f) RGR +M"}
    titulos = [etiqueta_agr[g] for g in grupos_validos] + [etiqueta_rgr[g] for g in grupos_validos]
    fig = make_subplots(rows=2, cols=len(grupos_validos), subplot_titles=titulos,
                         horizontal_spacing=0.09, vertical_spacing=0.2, shared_xaxes=True)

    for col, grupo in enumerate(grupos_validos, start=1):
        modelo = mejores[grupo]
        estilo = MODELO_ESTILO[modelo]
        res = RES[variable][grupo][modelo]
        agr, rgr = calcular_agr_rgr(modelo, res["params"], t_fino)
        fig.add_trace(go.Scatter(x=t_fino, y=agr, mode="lines", name=f"{grupo}: {modelo} (mejor R²)",
                                  legendgroup=f"{grupo}-{modelo}", showlegend=True,
                                  line=dict(color=estilo["color"], dash=estilo["dash"], width=2.2)),
                      row=1, col=col)
        fig.add_trace(go.Scatter(x=t_fino, y=rgr, mode="lines", showlegend=False,
                                  legendgroup=f"{grupo}-{modelo}",
                                  line=dict(color=estilo["color"], dash=estilo["dash"], width=2.2)),
                      row=2, col=col)
        if col == 1:
            fig.update_yaxes(title_text=f"AGR ({UNIDADES[variable]}/día)", row=1, col=col)
            fig.update_yaxes(title_text="RGR (día⁻¹)", row=2, col=col)
        fig.update_xaxes(title_text="Día después del trasplante (ddt)", row=2, col=col)

    estilo_publicacion(fig, height=560, right_margin=230)
    pie = [
        "Tasas calculadas analíticamente a partir de los parámetros ya ajustados del modelo con "
        "mejor R² en cada grupo (sin reajustar).",
        "AGR = dP/dt; RGR = (1/P)·dP/dt.",
    ]
    pie.extend(f"Modelo usado en {g}: {mejores[g]} (mejor R² entre los convergidos)." for g in grupos_validos)
    if len(grupos_validos) < len(grupos):
        pie.append(f"Sin tasas para {', '.join(g for g in grupos if g not in grupos_validos)}: "
                   "ningún modelo convergió en ese grupo.")
    if fuente_datos == "real":
        pie.append("Réplicas sintéticas generadas a partir de medias y CV% publicados (Aguirre-Medina et al., 2023).")
    agregar_pie_figura(fig, pie)
    return fig, None


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


def barra_comparacion_mitades(m1, m2, residuos):
    """HTML de una mini barra que compara la media de residuos de la 1a vs 2a mitad (solo visual)."""
    escala = max(abs(m1), abs(m2), np.std(residuos) if len(residuos) else 1.0, 1e-6) * 1.3
    pos1_pct = (m1 / escala + 1) / 2 * 100
    pos2_pct = (m2 / escala + 1) / 2 * 100
    return f'''<div style="position:relative; height:18px; margin:0.3rem 0 0.1rem 0;">
        <div style="position:absolute; top:8px; left:0; right:0; height:3px; background:{T['BORDER']}; border-radius:2px;"></div>
        <div style="position:absolute; top:3px; left:50%; width:1px; height:12px; background:{T['INK_MUTED']};"></div>
        <div style="position:absolute; top:5px; left:calc({pos1_pct:.1f}% - 4px); width:8px; height:8px; border-radius:50%; background:{T['CONTROL']};"
             title="1a mitad"></div>
        <div style="position:absolute; top:5px; left:calc({pos2_pct:.1f}% - 4px); width:8px; height:8px; border-radius:50%; background:{T['ACCENT']};"
             title="2a mitad"></div>
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
                    color = T["CONTROL"] if grupo == "-M" else T["ACCENT"]
                    fig.add_trace(go.Scatter(x=y_obs, y=y_pred, mode="markers", name=f"{grupo} ({mejor_m})",
                                              marker=dict(color=color, size=7, opacity=0.75)))
                    todos_x.extend(y_obs); todos_y.extend(y_pred)
                if todos_x:
                    lo, hi = float(min(todos_x + todos_y)), float(max(todos_x + todos_y))
                    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", name="Ideal (y=x)",
                                              line=dict(color=T["INK_MUTED"], dash="dash")))
                if todos_x:
                    fig.update_layout(height=320, title=f"Real vs. predicho — {NOMBRE_VARIABLE[variable]}",
                                       xaxis_title=f"Valor real ({UNIDADES[variable]})",
                                       yaxis_title=f"Valor predicho ({UNIDADES[variable]})")
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
                st.markdown('<span class="field-label">Cuándo conviene usarlo</span>', unsafe_allow_html=True)
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

    if st.session_state.fuente_datos == "real":
        st.info(
            "**Nota metodológica.** Los datos provienen de Aguirre-Medina et al. (2023), Revista "
            "Fitotecnia Mexicana. Las réplicas individuales fueron generadas sintéticamente a partir "
            "de las medias y el CV% publicados en el artículo (no son mediciones planta por planta).",
            icon="📄",
        )

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

        fig = fig_curvas_publicacion(DATOS, RES, variable, modelos_a_mostrar, st.session_state.fuente_datos)
        st.plotly_chart(fig, width='stretch')
        st.download_button(
            f"Descargar PNG — Curvas {NOMBRE_VARIABLE[variable]}",
            data=fig.to_image(format="png", scale=3),
            file_name=f"curvas_{variable}.png", mime="image/png", key=f"png_curvas_{variable}",
        )

        with st.expander(f"Tasas de crecimiento (AGR/RGR) — {NOMBRE_VARIABLE[variable]}"):
            st.caption(
                "Opcional: AGR (dP/dt) y RGR ((1/P)·dP/dt) del modelo con mejor R² en cada grupo, "
                "calculadas analíticamente a partir de los parámetros ya ajustados (sin reajustar)."
            )
            fig_tasas, motivo_sin_tasas = fig_tasas_crecimiento(
                DATOS, RES, variable, modelos_a_mostrar, st.session_state.fuente_datos)
            if fig_tasas is None:
                st.info(motivo_sin_tasas)
            else:
                st.plotly_chart(fig_tasas, width='stretch')
                st.download_button(
                    f"Descargar PNG — Tasas {NOMBRE_VARIABLE[variable]}",
                    data=fig_tasas.to_image(format="png", scale=3),
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
        fig_var = fig_barras_variable(DATOS, variable, st.session_state.fuente_datos)
        st.plotly_chart(fig_var, width='stretch')
        st.download_button(
            f"Descargar PNG — {NOMBRE_VARIABLE[variable]}",
            data=fig_var.to_image(format="png", scale=3),
            file_name=f"barras_{variable}.png", mime="image/png", key=f"png_barras_{variable}",
        )
        st.write("")

    if len(variables_a_mostrar) >= 2:
        st.markdown('<hr class="rule">', unsafe_allow_html=True)
        st.markdown("### Resumen (a)–(d)")
        st.markdown("Las mismas 4 variables en una sola figura, con eje Y propio por panel y una leyenda única.")
        fig_resumen = fig_barras_resumen_2x2(DATOS, variables_a_mostrar, st.session_state.fuente_datos)
        st.plotly_chart(fig_resumen, width='stretch')
        st.download_button(
            "Descargar PNG — Resumen (a)–(d)",
            data=fig_resumen.to_image(format="png", scale=3),
            file_name="barras_resumen.png", mime="image/png", key="png_barras_resumen",
        )

    st.markdown('<hr class="rule">', unsafe_allow_html=True)
    st.markdown("### Comparación de R² por modelo")
    st.markdown(
        "R² de Exponencial, Logístico y Gompertz por variable y grupo. Donde un modelo no convergió "
        "o no tuvo suficientes días de muestreo, la barra se muestra vacía con la etiqueta correspondiente."
    )
    fig_r2 = fig_barras_r2_comparacion(RES, DATOS, variables_a_mostrar, modelos_a_mostrar)
    st.plotly_chart(fig_r2, width='stretch')
    st.download_button(
        "Descargar PNG — Comparación de R²",
        data=fig_r2.to_image(format="png", scale=3),
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
        "El residuo es la diferencia entre cada observación real y lo que predice el modelo en "
        "ese día (`residuo = observado − predicho`), calculado sobre cada réplica individual. Si "
        "los puntos se distribuyen al azar alrededor de cero, el modelo captura bien la forma de "
        "la curva."
    )
    st.write("")

    COLOR_GRUPO = {"-M": T["CONTROL"], "+M": T["ACCENT"]}
    for variable in variables_a_mostrar:
        st.markdown(f"### {NOMBRE_VARIABLE[variable]}")
        n = len(modelos_a_mostrar)
        fig = make_subplots(rows=1, cols=n, subplot_titles=modelos_a_mostrar, horizontal_spacing=0.06)
        for i, nombre_modelo in enumerate(modelos_a_mostrar, start=1):
            for grupo in DATOS[variable]:
                res = RES[variable][grupo][nombre_modelo]
                if res["residuos"] is None:
                    continue
                color = COLOR_GRUPO[grupo]
                fig.add_trace(go.Scatter(x=res["t_flat"], y=res["residuos"], mode="markers", name=grupo,
                                          legendgroup=grupo, showlegend=(i == 1),
                                          marker=dict(color=color, size=6, opacity=0.7)), row=1, col=i)
            fig.add_hline(y=0, line=dict(color=T["INK_MUTED"], dash="dash", width=1), row=1, col=i)
            fig.update_xaxes(title_text="DAT (días)", row=1, col=i)
            if i == 1:
                fig.update_yaxes(title_text=f"Residuo ({UNIDADES[variable]})", row=1, col=i)
        # Sin título interno: el encabezado "### {variable}" ya lo pone esta sección.
        estilo_publicacion(fig, height=380)
        st.plotly_chart(fig, width='stretch')

        with st.container(border=True):
            st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
            st.markdown('<span class="field-label">Lectura rápida (heurística, no una prueba formal)</span>', unsafe_allow_html=True)
            for grupo in DATOS[variable]:
                for nombre_modelo in modelos_a_mostrar:
                    res = RES[variable][grupo][nombre_modelo]
                    if res["residuos"] is None:
                        continue
                    mitad = len(res["residuos"]) // 2
                    m1 = np.mean(res["residuos"][:mitad])
                    m2 = np.mean(res["residuos"][mitad:])
                    patron = "posible patrón sistemático" if abs(m1 - m2) > np.std(res["residuos"]) else "sin patrón evidente"
                    col_txt, col_bar = st.columns([3, 1])
                    with col_txt:
                        st.markdown(f"- `{grupo}` **{nombre_modelo}**: media 1ª mitad = {m1:+.3f}, media 2ª mitad = {m2:+.3f} → {patron}.")
                    with col_bar:
                        st.markdown(barra_comparacion_mitades(m1, m2, res["residuos"]), unsafe_allow_html=True)
            st.caption("Comparación simple de medias, no una prueba formal (como Durbin-Watson).")
        st.write("")


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
            "- Gráficas de barras por variable y comparación de R² por modelo\n"
            "- Tasas de crecimiento (AGR y RGR) del modelo con mejor R² en cada grupo\n"
            "- Resultados esperados: mejor modelo por variable y efecto +M vs −M con prueba t\n"
            "- Conclusiones generales"
        )
        generar_pdf = st.button("Generar reporte PDF", type="primary")

    def limpiar_texto(s):
        reemplazos = {
            "−": "-", "·": "-", "→": "->", "²": "2", "±": "+/-", "–": "-", "—": "-",
            "‘": "'", "’": "'", "“": '"', "”": '"',
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
                    fig_curvas_pdf = fig_curvas_publicacion(DATOS, RES, variable, modelos_a_mostrar,
                                                             st.session_state.fuente_datos)
                    fig_curvas_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white", width=1000, height=480)
                    insertar_imagen_png(pdf, fig_curvas_pdf.to_image(format="png", scale=3))
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
                fig_barra_pdf = fig_barras_variable(DATOS, variable, st.session_state.fuente_datos)
                fig_barra_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white", width=900, height=460)
                insertar_imagen_png(pdf, fig_barra_pdf.to_image(format="png", scale=3))

            if len(variables_a_mostrar) >= 2:
                asegurar_espacio(pdf, 110)
                subtitulo_variable(pdf, "Resumen (a)-(d)")
                fig_resumen_pdf = fig_barras_resumen_2x2(DATOS, variables_a_mostrar, st.session_state.fuente_datos)
                fig_resumen_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white", width=1000, height=720)
                insertar_imagen_png(pdf, fig_resumen_pdf.to_image(format="png", scale=3))

            asegurar_espacio(pdf, 100)
            subtitulo_variable(pdf, "Comparacion de R2 por modelo")
            fig_r2_pdf = fig_barras_r2_comparacion(RES, DATOS, variables_a_mostrar, modelos_a_mostrar)
            # No se fuerza "height": la propia figura calcula su alto segun 1 o 2 filas de
            # subplots (cuadricula 2x2 cuando hay 4 variables), y forzar un alto fijo aqui
            # volvia a aplastar la segunda fila como antes de la Tarea 3.
            fig_r2_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white", width=1000)
            insertar_imagen_png(pdf, fig_r2_pdf.to_image(format="png", scale=3))

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
                fig_tasas_pdf, motivo_sin_tasas = fig_tasas_crecimiento(
                    DATOS, RES, variable, modelos_a_mostrar, st.session_state.fuente_datos)
                if fig_tasas_pdf is None:
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.set_text_color(*PDF_MUTED)
                    pdf.multi_cell(0, 5.5, limpiar_texto(motivo_sin_tasas), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.set_text_color(*PDF_INK)
                    pdf.ln(3)
                else:
                    fig_tasas_pdf.update_layout(paper_bgcolor="white", plot_bgcolor="white", width=1000)
                    insertar_imagen_png(pdf, fig_tasas_pdf.to_image(format="png", scale=3))

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
