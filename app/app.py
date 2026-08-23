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
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from scipy.optimize import curve_fit
from scipy.stats import t as t_dist, ttest_ind
from fpdf import FPDF

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
        return (f'<span class="badge badge-ambar">Sin suficientes días · {dias_disponibles}/{dias_requeridos} '
                f'necesarios para este modelo</span>')
    if r2 is None or np.isnan(r2):
        return '<span class="badge badge-rojo">Sin ajuste</span>'
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
        "\n\nEsas combinaciones se mostrarán como **'Sin suficientes días'** en vez de un R² una vez "
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
elif seccion in ("Resultados", "Estadística", "Residuos", "Discusión y conclusiones", "Exportar reporte") and not st.session_state.ajustado:
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
    t_fino = np.linspace(0, 120, 300)
    COLOR_GRUPO = {"-M": T["CONTROL"], "+M": T["ACCENT"]}

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

        n = len(modelos_a_mostrar)
        fig = make_subplots(rows=1, cols=n, subplot_titles=modelos_a_mostrar, horizontal_spacing=0.06)

        for i, nombre_modelo in enumerate(modelos_a_mostrar, start=1):
            func = MODELOS[nombre_modelo]["func"]
            for grupo in DATOS[variable]:
                res = RES[variable][grupo][nombre_modelo]
                color = COLOR_GRUPO[grupo]
                dias_g, medias_g, sds_g, _ = media_sd_por_dia(DATOS[variable][grupo])

                if res["params"] is not None:
                    banda_baja, banda_alta = calcular_banda_confianza(func, res["params"], res["pcov"], t_fino)
                    if banda_baja is not None:
                        fig.add_trace(go.Scatter(x=t_fino, y=banda_alta, mode="lines", line=dict(width=0),
                                                  showlegend=False, hoverinfo="skip"), row=1, col=i)
                        fig.add_trace(go.Scatter(x=t_fino, y=banda_baja, mode="lines", line=dict(width=0),
                                                  fill="tonexty", fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.15)",
                                                  showlegend=False, hoverinfo="skip"), row=1, col=i)

                fig.add_trace(go.Scatter(
                    x=dias_g, y=medias_g, mode="markers", name=f"{grupo} media±DE", legendgroup=grupo, showlegend=(i == 1),
                    error_y=dict(type="data", array=sds_g, visible=True, color=color, thickness=1.2),
                    marker=dict(color=color, size=7, line=dict(width=1, color=color)),
                    hovertemplate=f"{grupo} · DAT %{{x}}<br>%{{y:.2f}} {UNIDADES[variable]}<extra></extra>",
                ), row=1, col=i)
                if res["params"] is not None:
                    y_fino = func(t_fino, *res["params"])
                    fig.add_trace(go.Scatter(
                        x=t_fino, y=y_fino, mode="lines", name=f"{grupo} ajuste", legendgroup=grupo, showlegend=False,
                        line=dict(color=color, width=2.5), hoverinfo="skip",
                    ), row=1, col=i)
            fig.update_xaxes(title_text="DAT (días)", row=1, col=i)
            if i == 1:
                fig.update_yaxes(title_text=f"{NOMBRE_VARIABLE[variable]} ({UNIDADES[variable]})", row=1, col=i)

        fig.update_layout(height=420, legend=dict(orientation="h", yanchor="bottom", y=1.08, x=0))
        fig.update_annotations(font=dict(family="IBM Plex Mono, monospace", size=12, color=T["INK_MUTED"]))
        st.plotly_chart(fig, width='stretch')
        st.caption("Puntos = media ± desviación estándar de las réplicas. Banda sombreada = intervalo de confianza del 95% de la curva completa.")

        filas = []
        for grupo in DATOS[variable]:
            for nombre_modelo in modelos_a_mostrar:
                res = RES[variable][grupo][nombre_modelo]
                if res.get("insuficiente"):
                    estado = f"Sin suficientes días ({res['dias_disponibles']}/{res['dias_requeridos']})"
                elif res["r2"] is None:
                    estado = "Sin ajuste"
                else:
                    estado = "OK"
                filas.append({"Grupo": grupo, "Modelo": nombre_modelo, "Estado": estado,
                               "R²": round(res["r2"], 4) if res["r2"] is not None else None,
                               "RMSE": round(res["rmse"], 4) if res["rmse"] is not None else None,
                               "MAE": round(res["mae"], 4) if res.get("mae") is not None else None})
        df_tabla = pd.DataFrame(filas)
        with st.container(border=True):
            st.markdown('<span class="ficha-marca"></span>', unsafe_allow_html=True)
            st.markdown('<span class="field-label">Tabla de ajuste</span>', unsafe_allow_html=True)
            st.dataframe(df_tabla.style.background_gradient(subset=["R²"], cmap="Greens", vmin=0.5, vmax=1.0),
                         width='stretch', hide_index=True)
        st.write("")


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
                    f"Diferencia **estadísticamente significativa** entre −M y +M (p = {resultado_t['p']:.4f} < 0.05)."
                    if resultado_t["significativo"] else
                    f"Diferencia **no significativa** entre −M y +M en este día (p = {resultado_t['p']:.4f} ≥ 0.05)."
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
                    estado = (f"Sin suficientes días ({res['dias_disponibles']}/{res['dias_requeridos']})"
                              if res.get("insuficiente") else "Sin ajuste")
                    filas_ci.append({"Grupo": grupo, "Modelo": nombre_modelo, "Parámetro": estado,
                                      "Valor": None, "IC 95% (inferior)": None, "IC 95% (superior)": None})
                    continue
                nombres_p = MODELOS[nombre_modelo]["nombres_param"]
                for i, nombre_p in enumerate(nombres_p):
                    filas_ci.append({
                        "Grupo": grupo, "Modelo": nombre_modelo, "Parámetro": nombre_p,
                        "Valor": round(res["params"][i], 4),
                        "IC 95% (inferior)": round(res["ci_bajo"][i], 4),
                        "IC 95% (superior)": round(res["ci_alto"][i], 4),
                    })
        st.dataframe(pd.DataFrame(filas_ci), width='stretch', hide_index=True)
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
        fig.update_layout(height=380, legend=dict(orientation="h", yanchor="bottom", y=1.1, x=0))
        fig.update_annotations(font=dict(family="IBM Plex Mono, monospace", size=12, color=T["INK_MUTED"]))
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
                    f"que la diferencia sea estadísticamente significativa (p = {resultado_t['p']:.4f})."
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
        st.markdown(
            """
- Reemplazar los datos simulados por mediciones reales (sección *Datos de prueba*).
- Validación externa con un segundo estudio publicado.
- Validación cruzada (ajustar con una parte de los datos, comprobar con el resto).
- Documentar todos los supuestos explícitamente en la metodología.
            """
        )


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
            placeholder="Ej: Corazon-Guivin et al. (2023), Research Square, DOI 10.21203/rs.3.rs-2878642/v1",
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
                        estado = (f"Sin suficientes dias ({res['dias_disponibles']}/{res['dias_requeridos']})"
                                  if res.get("insuficiente") else ("OK" if res["r2"] is not None else "Sin ajuste"))
                        fila = {"Grupo": grupo, "Modelo": nombre_modelo, "Estado": estado,
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
            "- Conclusiones generales"
        )
        generar_pdf = st.button("Generar reporte PDF", type="primary")

    def limpiar_texto(s):
        reemplazos = {"−": "-", "·": "-", "→": "->", "²": "2", "±": "+/-", "": "'", "": "'", "–": "-"}
        for a, b in reemplazos.items():
            s = s.replace(a, b)
        return s.encode("latin-1", "replace").decode("latin-1")

    if generar_pdf:
        with st.spinner("Generando PDF..."):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            pdf.set_font("Helvetica", "B", 18)
            pdf.cell(0, 10, limpiar_texto("Coffea arabica - Modelos de crecimiento"), ln=1)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 6, limpiar_texto(f"Reporte generado - {etiqueta_lote}"), ln=1)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(4)

            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Metodologia", ln=1)
            pdf.set_font("Helvetica", "", 10)
            texto_metodo = (
                "Se compararon tres modelos de crecimiento (Exponencial, Logistico, Gompertz) "
                "ajustados por minimos cuadrados no lineales (scipy.optimize.curve_fit) sobre "
                f"{N_REPLICAS} replicas por dia, para dos grupos: -M (sin inocular, control) y "
                "+M (inoculado con hongos micorrizicos arbusculares)."
            )
            pdf.multi_cell(0, 5.5, limpiar_texto(texto_metodo))
            pdf.ln(2)

            for variable in variables_a_mostrar:
                pdf.set_font("Helvetica", "B", 13)
                pdf.cell(0, 8, limpiar_texto(f"Resultados - {NOMBRE_VARIABLE[variable]}"), ln=1)
                pdf.set_font("Helvetica", "", 9)

                # Tabla de R2/RMSE/MAE
                pdf.set_font("Helvetica", "B", 9)
                anchos = [18, 24, 46, 20, 20, 20]
                encabezados = ["Grupo", "Modelo", "Estado", "R2", "RMSE", "MAE"]
                for enc, w in zip(encabezados, anchos):
                    pdf.cell(w, 6, enc, border=1)
                pdf.ln()
                pdf.set_font("Helvetica", "", 9)
                for grupo in DATOS[variable]:
                    for nombre_modelo in modelos_a_mostrar:
                        res = RES[variable][grupo][nombre_modelo]
                        if res.get("insuficiente"):
                            estado = f"Sin sufic. dias ({res['dias_disponibles']}/{res['dias_requeridos']})"
                        elif res["r2"] is None:
                            estado = "Sin ajuste"
                        else:
                            estado = "OK"
                        fila = [grupo, nombre_modelo, estado,
                                f"{res['r2']:.4f}" if res['r2'] is not None else "-",
                                f"{res['rmse']:.4f}" if res['rmse'] is not None else "-",
                                f"{res.get('mae'):.4f}" if res.get('mae') is not None else "-"]
                        for val, w in zip(fila, anchos):
                            pdf.cell(w, 6, limpiar_texto(str(val)), border=1)
                        pdf.ln()
                pdf.ln(3)

                # Grafica de resultados como imagen
                t_fino = np.linspace(0, 120, 200)
                fig = make_subplots(rows=1, cols=len(modelos_a_mostrar), subplot_titles=modelos_a_mostrar)
                for i, nombre_modelo in enumerate(modelos_a_mostrar, start=1):
                    func = MODELOS[nombre_modelo]["func"]
                    for grupo in DATOS[variable]:
                        res = RES[variable][grupo][nombre_modelo]
                        color = "#9C968C" if grupo == "-M" else "#9A3324"
                        dias_g, medias_g, sds_g, _ = media_sd_por_dia(DATOS[variable][grupo])
                        fig.add_trace(go.Scatter(x=dias_g, y=medias_g, mode="markers", name=grupo,
                                                  marker=dict(color=color, size=6),
                                                  showlegend=(i == 1)), row=1, col=i)
                        if res["params"] is not None:
                            fig.add_trace(go.Scatter(x=t_fino, y=func(t_fino, *res["params"]), mode="lines",
                                                      line=dict(color=color), showlegend=False), row=1, col=i)
                fig.update_layout(height=280, width=900, paper_bgcolor="white", plot_bgcolor="white",
                                   margin=dict(l=30, r=10, t=30, b=30))
                png_bytes = fig.to_image(format="png", scale=2)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                    tmp_img.write(png_bytes)
                    ruta_img = tmp_img.name
                pdf.image(ruta_img, w=190)
                pdf.ln(4)

            pdf.add_page()
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 8, "Conclusiones", ln=1)
            pdf.set_font("Helvetica", "", 10)
            conclusiones_txt = (
                "1. Los tres modelos se ajustan razonablemente, pero Logistico y Gompertz superan "
                "de forma consistente al Exponencial en R2.\n"
                "2. La eleccion final entre Logistico y Gompertz debe basarse en cual describe "
                "mejor el patron biologico observado, no solo en R2/RMSE.\n"
                "3. El grupo +M muestra consistentemente valores mas altos que -M, lo que -con "
                "datos reales- apoyaria la hipotesis de que la inoculacion con HMA favorece el "
                "crecimiento.\n\n"
                "Limitaciones: validacion externa pendiente; datos de prueba simulados en esta "
                "fase (o datos reales, segun corresponda)."
            )
            pdf.multi_cell(0, 5.5, limpiar_texto(conclusiones_txt))

            pdf_bytes = bytes(pdf.output())

        st.success("Reporte generado.")
        st.download_button("Descargar reporte PDF", data=pdf_bytes,
                            file_name="reporte_coffea_modelos.pdf", mime="application/pdf")
