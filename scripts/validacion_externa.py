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


def construir_datos_una_serie(df, grupo_fijo="unico", dia_col="ddt", valor_col="media"):
    """De un DataFrame largo (variable, <dia_col>, <valor_col>, ...) construye
    DATOS[variable][grupo_fijo][dia] = array([media]) -- UNA sola observación
    por fecha (la media publicada), sin inventar réplicas."""
    datos = {}
    for variable, sub in df.groupby("variable"):
        datos[variable] = {grupo_fijo: {}}
        for _, fila in sub.iterrows():
            datos[variable][grupo_fijo][int(fila[dia_col])] = np.array([float(fila[valor_col])])
    return datos


def logistico_a_parametrizacion_paper(K, k, Ti):
    """Convierte mi parametrización K/(1+exp(-k(t-Ti))) a la del paper de
    León-Burgos, a/(1+exp(-(t-x0)/b)): igualando exponentes, -k(t-Ti) = -(t-x0)/b
    exige b = 1/k, x0 = Ti, a = K."""
    return {"a": K, "x0": Ti, "b": 1.0 / k if k != 0 else np.nan}


def fig_publicacion_leon_burgos(variable, dias, medias, RES, modelos_orden, dia_min, dia_max,
                                  y_max_obs, app_ns, nombre_archivo, etiqueta_y):
    """Figura estilo publicación (fondo blanco, paleta de la app, ticks en los
    días medidos). El pie de figura NO se dibuja aquí (va en informe.md)."""
    fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.scatter(dias, medias, s=42, facecolors="none", edgecolors=TINTA, linewidths=1.3,
               zorder=5, label="Media publicada")
    t_fino = np.linspace(min(dias), max(dias), 300)
    for modelo in modelos_orden:
        res = RES[variable]["unico"][modelo]
        estado = app_ns["estado_de_ajuste"](res)
        if estado != "OK":
            continue
        func = {"Exponencial": app_ns["modelo_exponencial"],
                "Logístico": app_ns["modelo_logistico"],
                "Gompertz": app_ns["modelo_gompertz"]}[modelo]
        y_fino = func(t_fino, *res["params"])
        ax.plot(t_fino, y_fino, color=COLOR_MODELO[modelo], linewidth=2.0,
                label=f"{modelo} (R²={res['r2']:.3f})")
        if modelo in ("Logístico", "Gompertz"):
            dibujar_k, K, _motivo = app_ns["_asintota_k_plausible"](res, y_max_obs, dia_min, dia_max)
            if dibujar_k:
                ax.axhline(K, color=COLOR_MODELO[modelo], linestyle=":", linewidth=1.2, alpha=0.8)
    ax.set_xticks(sorted(set(dias)))
    ax.tick_params(axis="x", rotation=45)
    ax.set_xlabel("Día después del trasplante (ddt)")
    ax.set_ylabel(etiqueta_y)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    ruta = os.path.join(FIG_DIR, nombre_archivo)
    fig.savefig(ruta, facecolor="white")
    plt.close(fig)
    return ruta


VARIABLES_PRINCIPALES_LB = ["area_foliar", "numero_hojas", "altura"]
VARIABLES_SECUNDARIAS_LB = ["diametro_tallo", "longitud_raiz"]
ETIQUETA_Y_LB = {
    "area_foliar": "Área foliar total (cm²)", "numero_hojas": "Número de hojas",
    "altura": "Altura (cm)", "diametro_tallo": "Diámetro del tallo (mm)",
    "longitud_raiz": "Longitud de la raíz principal (cm)",
}
REFERENCIA_APROX_MIA_LB = {
    # Dadas por el usuario (fórmulas estándar, NO salida de la app): solo para
    # detectar diferencias grandes, no se usan en ningún cálculo.
    "area_foliar": {"K": 688, "x0": 142, "r2": 0.99},
    "numero_hojas": {"K": 12.9, "x0": 90, "r2": 0.98},
    "altura": {"K": 70, "x0": 201, "r2": 0.98},
}
GOMPERTZ_ALTURA_APROX_MIA = 498  # referencia aproximada del usuario, K "absurda" esperada


def fase_2a_leon_burgos(app_ns):
    print("=" * 70)
    print("FASE 2A -- León-Burgos et al. (2022): validación de curvas")
    print("=" * 70)
    ruta = os.path.join(VAL_DIR, "leon_burgos_2022.xlsx")
    df = pd.read_excel(ruta, sheet_name="Datos")
    ref_pub = pd.read_excel(ruta, sheet_name="Referencia_publicada", header=None)

    datos = construir_datos_una_serie(df)
    RES = app_ns["ajustar_todos_los_modelos"](datos)

    filas_curvas = []
    filas_comparacion = []
    modelos_orden = ["Exponencial", "Logístico", "Gompertz"]

    for variable in VARIABLES_PRINCIPALES_LB + VARIABLES_SECUNDARIAS_LB:
        sub = df[df["variable"] == variable].sort_values("ddt")
        dias = sub["ddt"].to_numpy()
        medias = sub["media"].to_numpy()
        dia_min, dia_max = float(dias.min()), float(dias.max())
        y_max_obs = float(medias.max())

        for modelo in modelos_orden:
            res = RES[variable]["unico"][modelo]
            estado = app_ns["estado_de_ajuste"](res)
            fila = {
                "fuente": "leon_burgos_2022", "variable": variable, "modelo": modelo,
                "estado": estado, "r2": res["r2"], "rmse": res["rmse"], "mae": res["mae"],
            }
            if estado == "OK" and modelo in ("Logístico", "Gompertz"):
                K, k, Ti = res["params"]
                dibujar_k, K_val, motivo = app_ns["_asintota_k_plausible"](res, y_max_obs, dia_min, dia_max)
                fila.update({"K": K, "k": k, "Ti": Ti, "K_sobre_max_obs": K / y_max_obs if y_max_obs else np.nan,
                             "dibuja_K_criterio_app": dibujar_k, "motivo_si_no_dibuja": motivo or ""})
            elif estado == "OK":
                fila.update({"P0_o_K": res["params"][0], "r_o_k": res["params"][1]})
            filas_curvas.append(fila)

        print(f"\n-- {variable} (máx. observado={y_max_obs:.2f}, ventana {dia_min:.0f}-{dia_max:.0f} ddt) --")
        for f in [x for x in filas_curvas if x["variable"] == variable]:
            print(f"  {f['modelo']:12s} estado={f['estado']:24s} R²={f['r2']}")

        if variable in VARIABLES_PRINCIPALES_LB:
            fig_publicacion_leon_burgos(
                variable, dias, medias, RES, modelos_orden, dia_min, dia_max, y_max_obs, app_ns,
                f"leon_burgos_{variable}.png", ETIQUETA_Y_LB[variable])

            # Comparación con lo publicado: SOLO Logístico (mío) <-> sigmoidal (paper)
            res_log = RES[variable]["unico"]["Logístico"]
            fila_cmp = {"variable": variable}
            if app_ns["estado_de_ajuste"](res_log) == "OK":
                K, k, Ti = res_log["params"]
                conv = logistico_a_parametrizacion_paper(K, k, Ti)
                fila_cmp.update({
                    "mi_K_a": K, "mi_Ti_x0": Ti, "mi_b_1_sobre_k": conv["b"], "mi_r2": res_log["r2"],
                })
            fila_pub = ref_pub[(ref_pub[0] == variable) & (ref_pub[1] == "sigmoidal")]
            if not fila_pub.empty:
                fila_cmp.update({
                    "paper_a_K": fila_pub.iloc[0][4], "paper_x0_Ti": fila_pub.iloc[0][3],
                    "paper_b": fila_pub.iloc[0][5],
                })
            # R2 publicado esta en la Tabla 3 (bloque separado), buscar por variable+sigmoidal
            fila_r2pub = ref_pub[(ref_pub[0] == variable) & (ref_pub[1] == "sigmoidal") & (ref_pub[2].apply(lambda v: isinstance(v, (int, float))))]
            ref_aprox = REFERENCIA_APROX_MIA_LB.get(variable, {})
            fila_cmp.update({
                "mi_referencia_aprox_K": ref_aprox.get("K"), "mi_referencia_aprox_x0": ref_aprox.get("x0"),
                "mi_referencia_aprox_r2": ref_aprox.get("r2"),
            })
            filas_comparacion.append(fila_cmp)

    # R2 publicado de la Tabla 3 del paper (bloque de bondad de ajuste, filas 21+)
    tabla3 = ref_pub.iloc[22:42].copy()
    tabla3.columns = ["variable", "funcion", "r2", "r2_ajustado", "mse", "see", "aic", "bic"]
    for fila_cmp in filas_comparacion:
        v = fila_cmp["variable"]
        m = tabla3[(tabla3["variable"] == v) & (tabla3["funcion"] == "sigmoidal")]
        if not m.empty:
            fila_cmp["paper_r2"] = m.iloc[0]["r2"]

    df_curvas_lb = pd.DataFrame(filas_curvas)
    df_comparacion_lb = pd.DataFrame(filas_comparacion)

    # Pregunta central: ¿coincide "No convergió/K no estimable" con lo que veo en mis
    # propios datos (28-112 ddt)?
    print("\n-- Pregunta central (criterio de plausibilidad de K) --")
    for variable in VARIABLES_PRINCIPALES_LB:
        fila = df_curvas_lb[(df_curvas_lb["variable"] == variable) & (df_curvas_lb["modelo"] == "Logístico")].iloc[0]
        if fila["estado"] == "OK":
            print(f"  {variable}: Logístico converge, dibuja_K={fila.get('dibuja_K_criterio_app')} "
                  f"(K/máx={fila.get('K_sobre_max_obs'):.2f}, motivo si no: {fila.get('motivo_si_no_dibuja')!r})")
        else:
            print(f"  {variable}: Logístico -> {fila['estado']}")

    return df_curvas_lb, df_comparacion_lb


# =============================================================================
# FASE 2B — Siqueira et al. (1998): apoyo, efecto en el tiempo (4 fechas)
# =============================================================================
def fase_2b_siqueira(app_ns):
    print("\n" + "=" * 70)
    print("FASE 2B -- Siqueira et al. (1998): apoyo, efecto en el tiempo")
    print("=" * 70)
    ruta = os.path.join(VAL_DIR, "siqueira_1998.xlsx")
    df = pd.read_excel(ruta, sheet_name="Datos")

    # 1) % de incremento de cada tratamiento sobre Ni (control), por variable y fecha
    filas_efecto = []
    for variable, sub in df.groupby("variable"):
        piv = sub.pivot(index="tratamiento", columns="mat", values="media")
        if "Ni" not in piv.index:
            continue
        control = piv.loc["Ni"]
        for tratamiento in piv.index:
            if tratamiento == "Ni":
                continue
            for mat in piv.columns:
                v_ctrl, v_trat = control.get(mat), piv.loc[tratamiento].get(mat)
                if pd.isna(v_ctrl) or pd.isna(v_trat) or v_ctrl == 0:
                    continue
                filas_efecto.append({
                    "fuente": "siqueira_1998", "variable": variable, "tratamiento": tratamiento,
                    "mat": mat, "media_control_Ni": v_ctrl, "media_tratamiento": v_trat,
                    "incremento_pct": (v_trat - v_ctrl) / v_ctrl * 100,
                })
    df_efecto_siqueira = pd.DataFrame(filas_efecto)

    print("\n-- Verificación del efecto máximo citado en el paper (tratamiento Lav, altura) --")
    lav = df_efecto_siqueira[(df_efecto_siqueira["variable"] == "altura") & (df_efecto_siqueira["tratamiento"] == "Lav")]
    for _, f in lav.iterrows():
        print(f"  {f['mat']:.0f} MAT: +{f['incremento_pct']:.1f}% sobre Ni "
              f"(citado en el paper: {'50%' if f['mat']==9 else '18%' if f['mat']==19 else '10%' if f['mat']==26 else '?'})")

    # 2) ¿Qué devuelve la app con solo 4 fechas (altura) y con 3 (diámetros)?
    print("\n-- Ajuste con las funciones de la app, por tratamiento --")
    filas_curvas = []
    for variable in ["altura", "diametro_tallo", "diametro_copa"]:
        sub = df[df["variable"] == variable]
        n_fechas = sub["mat"].nunique()
        datos = {variable: {}}
        for tratamiento, g in sub.groupby("tratamiento"):
            datos[variable][tratamiento] = {int(row["mat"]): np.array([float(row["media"])]) for _, row in g.iterrows()}
        RES = app_ns["ajustar_todos_los_modelos"](datos)
        for tratamiento in datos[variable]:
            for modelo in ("Exponencial", "Logístico", "Gompertz"):
                res = RES[variable][tratamiento][modelo]
                estado = app_ns["estado_de_ajuste"](res)
                n_params = len(app_ns["MODELOS"][modelo]["nombres_param"])
                filas_curvas.append({
                    "fuente": "siqueira_1998", "variable": variable, "tratamiento": tratamiento,
                    "modelo": modelo, "n_fechas": n_fechas, "n_params": n_params,
                    "grados_libertad": n_fechas - n_params, "estado": estado, "r2": res["r2"],
                    "rmse": res["rmse"], "mae": res["mae"],
                })
        print(f"  {variable} ({n_fechas} fechas distintas): "
              f"{'todos los modelos con >=1 grado de libertad' if n_fechas > 3 else 'Logístico/Gompertz con 0 grados de libertad (3 puntos, 3 parámetros: ajuste exacto, no informativo)'}")
    df_curvas_siqueira = pd.DataFrame(filas_curvas)

    ejemplo_altura_ni = df_curvas_siqueira[(df_curvas_siqueira["variable"] == "altura") & (df_curvas_siqueira["tratamiento"] == "Ni")]
    print("\n  Ejemplo (altura, tratamiento Ni/control, 4 fechas -> 1 grado de libertad en Logístico/Gompertz):")
    for _, f in ejemplo_altura_ni.iterrows():
        print(f"    {f['modelo']:12s} estado={f['estado']:20s} R²={f['r2']}")

    # 3) Figura: % de incremento sobre el control en el tiempo, una linea por tratamiento
    fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    altura_efecto = df_efecto_siqueira[df_efecto_siqueira["variable"] == "altura"]
    cmap = plt.get_cmap("tab10")
    for i, tratamiento in enumerate(sorted(altura_efecto["tratamiento"].unique())):
        sub = altura_efecto[altura_efecto["tratamiento"] == tratamiento].sort_values("mat")
        ax.plot(sub["mat"], sub["incremento_pct"], marker="o", color=cmap(i), label=tratamiento, linewidth=1.8)
    ax.axhline(0, color=GRIS, linewidth=1, linestyle="--")
    ax.set_xticks(sorted(altura_efecto["mat"].unique()))
    ax.set_xlabel("Meses después del trasplante (MAT)")
    ax.set_ylabel("% de incremento en altura sobre el control (Ni)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "siqueira_efecto_altura.png"), facecolor="white")
    plt.close(fig)

    return df_efecto_siqueira, df_curvas_siqueira


if __name__ == "__main__":
    print("Construyendo namespace aislado desde app/app.py (ast, sin importar streamlit)...")
    APP_NS, codigo_fuente_extraido = construir_namespace_app()
    print(f"  {len(FUNCS_NECESARIAS)} funciones y {len(ASSIGNS_NECESARIOS)} constantes extraídas.")
    prueba_de_fidelidad(APP_NS)

    df_curvas_lb, df_comparacion_lb = fase_2a_leon_burgos(APP_NS)
    df_efecto_siqueira, df_curvas_siqueira = fase_2b_siqueira(APP_NS)
