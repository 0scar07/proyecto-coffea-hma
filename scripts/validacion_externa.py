# -*- coding: utf-8 -*-
"""Validación externa PARCIAL de la metodología de Coffea IA con datos publicados
de otros estudios: León-Burgos et al. (2022), Siqueira et al. (1998) y
Vallejos-Torres et al. (2021).

Lo que se valida es la METODOLOGÍA (modelos, criterio de convergencia, criterio
de plausibilidad de K), no las cifras de mi propio dataset. Los tres estudios
difieren en cultivar, sustrato, edad y unidades entre sí y con mis datos: se
analizan por separado y solo se combinan las conclusiones al final.

Este script NO importa app/app.py (arrancaría Streamlit): usa el módulo `ast`
para extraer el código fuente vigente de las funciones puras de ajuste, lo
ejecuta en un espacio de nombres aislado (solo numpy/scipy), y así usa siempre
la MISMA lógica que la app real sin duplicarla a mano. La única excepción es
la prueba de fidelidad (más abajo), que sí importa app.py una vez, de forma
aislada, solo para comparar resultados -- no para el resto del pipeline.

Los datos de estas fuentes son MEDIAS publicadas, no réplicas: no se generan
réplicas sintéticas y no se corren las pruebas t de la app (que requieren
arrays de réplicas). Para Vallejos-Torres (Fase 2C) se usa
scipy.stats.ttest_ind_from_stats directamente sobre los estadísticos de resumen.

Uso: python scripts/validacion_externa.py
"""
import ast
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.stats import t as t_dist, ttest_ind_from_stats

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, ".."))
APP_PY = os.path.join(REPO, "app", "app.py")
VAL_DIR = os.path.join(REPO, "datos_reales", "validacion_externa")
XLSX_REAL = os.path.join(REPO, "datos_reales", "datos_reales_coffea_2023.xlsx")
OUT_DIR = os.path.join(REPO, "docs", "validacion_externa")
FIG_DIR = os.path.join(OUT_DIR, "figuras")
PREVIEWS = os.path.join(REPO, "previews", "validacion_externa")

for d in (OUT_DIR, FIG_DIR, PREVIEWS):
    os.makedirs(d, exist_ok=True)

# Paleta real de la app ("Cuaderno de campo", app/.streamlit/config.toml)
CREMA = "#F1ECE3"
TINTA = "#201C18"
TERRACOTA = "#A8432B"
BORDE = "#E4DFD6"
GRIS = "#8A8277"
COLOR_MODELO = {"Exponencial": "#2E7D9A", "Logístico": "#C9962B", "Gompertz": "#3F8F6B"}


# =============================================================================
# FASE 1 — Extraer con `ast` el código vigente de app.py (sin importar app.py)
# =============================================================================
FUNCS_NECESARIAS = [
    "modelo_exponencial", "modelo_logistico", "modelo_gompertz",
    "calcular_r2", "calcular_rmse", "calcular_mae",
    "flatten_replicas", "media_sd_por_dia", "dias_disponibles",
    "ajustar_todos_los_modelos", "_asintota_k_plausible",
    "texto_estado_sin_dias", "estado_de_ajuste",
]
ASSIGNS_NECESARIOS = ["MODELOS", "P0_INICIAL", "ESTADO_OK", "ESTADO_NO_CONVERGIO", "ESTADO_SIN_DIAS"]

ORDEN_ENSAMBLADO = [
    "modelo_exponencial", "modelo_logistico", "modelo_gompertz", "MODELOS",
    "calcular_r2", "calcular_rmse", "calcular_mae", "P0_INICIAL",
    "flatten_replicas", "media_sd_por_dia", "dias_disponibles",
    "ajustar_todos_los_modelos",
    "ESTADO_OK", "ESTADO_NO_CONVERGIO", "ESTADO_SIN_DIAS",
    "texto_estado_sin_dias", "estado_de_ajuste", "_asintota_k_plausible",
]


def extraer_codigo_de_app():
    """Recorre el AST de app/app.py y devuelve {nombre: codigo_fuente} solo para
    las funciones/constantes puras que necesitamos, quitando decoradores como
    @st.cache_data (streamlit no está disponible en este espacio de nombres
    aislado) sin tocar el CUERPO de la función."""
    with open(APP_PY, encoding="utf-8") as f:
        fuente = f.read()
    arbol = ast.parse(fuente)
    piezas = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.FunctionDef) and nodo.name in FUNCS_NECESARIAS:
            nodo.decorator_list = []
            piezas[nodo.name] = ast.unparse(nodo)
        elif isinstance(nodo, ast.Assign):
            for t in nodo.targets:
                if isinstance(t, ast.Name) and t.id in ASSIGNS_NECESARIOS:
                    piezas[t.id] = ast.unparse(nodo)
    faltantes = (set(FUNCS_NECESARIAS) | set(ASSIGNS_NECESARIOS)) - set(piezas)
    if faltantes:
        raise RuntimeError(
            f"No se encontraron en app/app.py (¿cambiaron de nombre?): {sorted(faltantes)}"
        )
    return piezas


def construir_namespace_app():
    """Ensambla el código extraído en orden de dependencias y lo ejecuta en un
    namespace aislado. Devuelve (namespace, codigo_fuente_completo)."""
    piezas = extraer_codigo_de_app()
    codigo_fuente = "\n\n".join(piezas[n] for n in ORDEN_ENSAMBLADO)
    ns = {"np": np, "curve_fit": curve_fit, "t_dist": t_dist, "__name__": "app_extraido"}
    exec(compile(codigo_fuente, "<extraido_de_app.py>", "exec"), ns)
    return ns, codigo_fuente


def prueba_de_fidelidad(app_ns):
    """Compara, para 'altura' (ambos grupos) sobre datos_reales_coffea_2023.xlsx,
    el resultado de (a) las funciones extraídas con ast en este script y (b) las
    funciones reales de app.py importado directamente -- solo para esta prueba
    puntual, no se usa en el resto del pipeline. Deben coincidir R², RMSE, MAE
    y el estado de convergencia para los 3 modelos y los 2 grupos."""
    df = pd.read_excel(XLSX_REAL, sheet_name="datos")
    sub = df[df["variable"] == "altura"]
    datos = {"altura": {"-M": {}, "+M": {}}}
    for (grupo, dia), g in sub.groupby(["grupo", "dat"]):
        datos["altura"][grupo][int(dia)] = g["valor"].to_numpy()

    res_extraido = app_ns["ajustar_todos_los_modelos"](datos)

    sys.path.insert(0, os.path.join(REPO, "app"))
    import app as app_real  # SOLO para esta prueba de fidelidad puntual

    res_real = app_real.ajustar_todos_los_modelos(datos)

    print("--- Prueba de fidelidad: altura (-M y +M), código extraído vs app.py real ---")
    ok_total = True
    for grupo in ("-M", "+M"):
        for modelo in ("Exponencial", "Logístico", "Gompertz"):
            a = res_extraido["altura"][grupo][modelo]
            b = res_real["altura"][grupo][modelo]
            estado_a = app_ns["estado_de_ajuste"](a)
            estado_b = app_real.estado_de_ajuste(b)
            r2_iguales = (
                (a["r2"] is None and b["r2"] is None)
                or (a["r2"] is not None and b["r2"] is not None and np.isclose(a["r2"], b["r2"], equal_nan=True))
            )
            rmse_iguales = (
                (a["rmse"] is None and b["rmse"] is None)
                or (a["rmse"] is not None and b["rmse"] is not None and np.isclose(a["rmse"], b["rmse"], equal_nan=True))
            )
            mae_iguales = (
                (a["mae"] is None and b["mae"] is None)
                or (a["mae"] is not None and b["mae"] is not None and np.isclose(a["mae"], b["mae"], equal_nan=True))
            )
            ok = (estado_a == estado_b) and r2_iguales and rmse_iguales and mae_iguales
            ok_total &= ok
            print(f"  {grupo:3s} {modelo:12s} estado: {estado_a!r:28s} vs {estado_b!r:28s}  "
                  f"R² {a['r2']} vs {b['r2']}  -> {'OK' if ok else 'DIFERENTE'}")
    if not ok_total:
        raise RuntimeError("La prueba de fidelidad encontró diferencias entre el código extraído y app.py real.")
    print("Prueba de fidelidad: TODO COINCIDE (mismo R², RMSE, MAE y estado en los 6 casos).\n")


if __name__ == "__main__":
    print("Construyendo namespace aislado desde app/app.py (ast, sin importar streamlit)...")
    APP_NS, codigo_fuente_extraido = construir_namespace_app()
    print(f"  {len(FUNCS_NECESARIAS)} funciones y {len(ASSIGNS_NECESARIOS)} constantes extraídas.")
    prueba_de_fidelidad(APP_NS)
