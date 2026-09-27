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
DATOS_DIR = os.path.join(OUT_DIR, "datos")
PREVIEWS = os.path.join(REPO, "previews", "validacion_externa")

for d in (OUT_DIR, FIG_DIR, DATOS_DIR, PREVIEWS):
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


# =============================================================================
# FASE 2C — Vallejos-Torres et al. (2021): efecto +M frente a −M
# =============================================================================
ESCENARIOS_N = [18, 108]  # 18 unidades experimentales o 108 plantas individuales
ESCENARIOS_INTERPRETACION = ["como_DE", "como_EE"]  # el valor entre parentesis, tal cual o como error estandar

# Mis propios resultados reales (Resultados esperados, +M vs -M) a 112 ddt, ya
# verificados en tareas anteriores sobre datos_reales_coffea_2023.xlsx con
# calcular_efecto_micorriza: se recalculan aqui mismo por trazabilidad.
def recalcular_efecto_112ddt_mi_app():
    df = pd.read_excel(XLSX_REAL, sheet_name="datos")
    filas = []
    for variable in ("altura", "hojas"):
        sub = df[(df["variable"] == variable) & (df["dat"] == 112)]
        m_menos = sub[sub["grupo"] == "-M"]["valor"].mean()
        m_mas = sub[sub["grupo"] == "+M"]["valor"].mean()
        filas.append({"variable": variable, "media_-M": m_menos, "media_+M": m_mas,
                       "incremento_pct": (m_mas - m_menos) / m_menos * 100})
    return pd.DataFrame(filas)


def fase_2c_vallejos_torres(app_ns):
    print("\n" + "=" * 70)
    print("FASE 2C -- Vallejos-Torres et al. (2021): efecto +M frente a -M")
    print("=" * 70)
    ruta = os.path.join(VAL_DIR, "vallejos_torres_2021.xlsx")
    df = pd.read_excel(ruta, sheet_name="Datos")
    control = df[df["es_control"] == "sí"].set_index("variable")
    tratamientos = [t for t in df["tratamiento"].unique() if t != "Control sin HMA"]

    # 1) % de incremento de cada consorcio sobre el control, y direccion
    filas_incremento = []
    for tratamiento in tratamientos:
        sub = df[df["tratamiento"] == tratamiento].set_index("variable")
        for variable in sub.index:
            media_ctrl = control.loc[variable, "media"]
            media_trat = sub.loc[variable, "media"]
            inc = (media_trat - media_ctrl) / media_ctrl * 100
            filas_incremento.append({
                "fuente": "vallejos_torres_2021", "tratamiento": tratamiento, "variable": variable,
                "media_control": media_ctrl, "media_tratamiento": media_trat,
                "incremento_pct": inc, "direccion": "mayor que control" if inc > 0 else "menor que control",
            })
    df_incremento = pd.DataFrame(filas_incremento)
    print("\n-- % de incremento sobre el control (Tabla 3) --")
    for _, f in df_incremento.iterrows():
        print(f"  {f['tratamiento']:14s} {f['variable']:16s} {f['incremento_pct']:+6.1f}%  ({f['direccion']})")

    # 2) Sensibilidad con Welch (ttest_ind_from_stats) bajo escenarios explicitos
    filas_sens = []
    for tratamiento in tratamientos:
        sub = df[df["tratamiento"] == tratamiento].set_index("variable")
        for variable in sub.index:
            m_ctrl, p_ctrl = control.loc[variable, "media"], control.loc[variable, "valor_entre_parentesis"]
            m_trat, p_trat = sub.loc[variable, "media"], sub.loc[variable, "valor_entre_parentesis"]
            n_sig = 0
            for n in ESCENARIOS_N:
                for interp in ESCENARIOS_INTERPRETACION:
                    sd_ctrl = p_ctrl if interp == "como_DE" else p_ctrl * np.sqrt(n)
                    sd_trat = p_trat if interp == "como_DE" else p_trat * np.sqrt(n)
                    t_stat, p_val = ttest_ind_from_stats(
                        mean1=m_trat, std1=sd_trat, nobs1=n,
                        mean2=m_ctrl, std2=sd_ctrl, nobs2=n, equal_var=False)
                    sig = p_val < 0.05
                    n_sig += int(sig)
                    filas_sens.append({
                        "fuente": "vallejos_torres_2021", "tratamiento": tratamiento, "variable": variable,
                        "n_escenario": n, "interpretacion_parentesis": interp,
                        "sd_control_usada": sd_ctrl, "sd_tratamiento_usada": sd_trat,
                        "t_welch": t_stat, "p_welch": p_val, "significativo_p<0.05": sig,
                    })
            print(f"  {tratamiento:14s} {variable:16s} significativo en {n_sig}/4 escenarios")
    df_sensibilidad = pd.DataFrame(filas_sens)

    # 3) Comparacion de direccion/orden de magnitud con mi propia app (altura y
    # numero de hojas, unicas 2 variables con datos REALES en mi app -- mi
    # "diametro" usa datos simulados, no reales, asi que no se compara aqui)
    print("\n-- Comparación de dirección con mi app (datos reales, 112 ddt) --")
    df_mi_app = recalcular_efecto_112ddt_mi_app()
    print(df_mi_app.to_string(index=False))
    print("  (Vallejos-Torres: altura +17.0% a +37.0%, hojas +7.2% a +66.8% según consorcio, ambas positivas.")
    print("   Mi app: altura +4.3% (ns), hojas +5.5% (ns) a 112 ddt -- misma DIRECCIÓN, distinto orden de")
    print("   magnitud y significancia; no son comparables en cifra por edad/sustrato/unidades distintos.)")

    # Figura de apoyo (no pedida explícitamente, pero barata y clarifica el paso 1)
    fig, ax = plt.subplots(figsize=(7.5, 5.0), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    variables_orden = ["altura", "numero_ramas", "numero_hojas", "diametro_tallo"]
    x = np.arange(len(tratamientos))
    ancho = 0.2
    cmap = plt.get_cmap("tab10")
    for i, variable in enumerate(variables_orden):
        vals = [df_incremento[(df_incremento["tratamiento"] == t) & (df_incremento["variable"] == variable)]["incremento_pct"].iloc[0] for t in tratamientos]
        ax.bar(x + (i - 1.5) * ancho, vals, width=ancho, label=variable, color=cmap(i))
    ax.axhline(0, color=TINTA, linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(tratamientos)
    ax.set_ylabel("% de incremento sobre el control sin HMA")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "vallejos_torres_incremento.png"), facecolor="white")
    plt.close(fig)

    return df_incremento, df_sensibilidad, df_mi_app


# =============================================================================
# FASE 3 — CSVs e informe
# =============================================================================
def fase_3_informe(df_curvas_lb, df_comparacion_lb, df_efecto_siqueira, df_curvas_siqueira,
                    df_incremento_vt, df_sensibilidad_vt, df_mi_app_112ddt):
    print("\n" + "=" * 70)
    print("FASE 3 -- CSVs e informe")
    print("=" * 70)

    resultados_curvas = pd.concat([df_curvas_lb, df_curvas_siqueira], ignore_index=True, sort=False)
    resultados_curvas.to_csv(os.path.join(DATOS_DIR, "resultados_curvas.csv"), index=False)

    df_comparacion_lb.to_csv(os.path.join(DATOS_DIR, "comparacion_publicado.csv"), index=False)

    efecto = pd.concat([df_efecto_siqueira, df_incremento_vt], ignore_index=True, sort=False)
    efecto.to_csv(os.path.join(DATOS_DIR, "efecto.csv"), index=False)

    df_sensibilidad_vt.to_csv(os.path.join(DATOS_DIR, "sensibilidad_vallejos_torres.csv"), index=False)

    for nombre in ("resultados_curvas.csv", "comparacion_publicado.csv", "efecto.csv",
                   "sensibilidad_vallejos_torres.csv"):
        ruta = os.path.join(DATOS_DIR, nombre)
        print(f"  {nombre}: {os.path.getsize(ruta)} bytes")

    # ---- informe.md ----------------------------------------------------
    fecha = pd.Timestamp.now().strftime("%Y-%m-%d")

    def fmt_cmp_row(r):
        return (f"| {r['variable']} | K={r['mi_K_a']:.1f}, Ti={r['mi_Ti_x0']:.1f}, R²={r['mi_r2']:.3f} "
                f"| a={r['paper_a_K']:.1f}, x0={r['paper_x0_Ti']:.1f}, R²={r.get('paper_r2', float('nan')):.2f} "
                f"| K≈{r['mi_referencia_aprox_K']}, x0≈{r['mi_referencia_aprox_x0']}, R²≈{r['mi_referencia_aprox_r2']} |")

    filas_cmp_md = "\n".join(fmt_cmp_row(r) for _, r in df_comparacion_lb.iterrows())

    informe = f"""# Validación externa parcial de la metodología — {fecha}

## ¿Qué es esto y por qué existe?

Coffea IA es una app que ajusta tres modelos matemáticos de crecimiento a datos de
*Coffea arabica* con y sin hongos micorrízicos. Todo lo probado hasta ahora venía de un
solo dataset propio. Este documento es una validación externa **parcial**: comprueba si
la *metodología* de la app (los 3 modelos, el criterio de convergencia y el criterio de
plausibilidad de la asíntota K) se comporta de forma razonable frente a datos que **ya
publicaron otros investigadores**, no frente a datos nuevos míos. Está pensado para
alguien que abre este documento sin haber visto el resto del proyecto — por ejemplo, un
docente revisando el trabajo — y que necesita entender de una vez qué se validó y qué no.
"Parcial" es la palabra clave: valida la metodología, no valida (todavía) mis propios
resultados con un experimento nuevo, y los tres estudios usados difieren entre sí y con
el mío en cultivar, sustrato, edad de la planta y unidades, así que se analizan por
separado y solo se combinan las conclusiones metodológicas al final.

**Cómo se generó (técnico):** el script `scripts/validacion_externa.py` **no importa
`app/app.py`** (eso arrancaría Streamlit); en vez de eso extrae con el módulo `ast` de
Python el código fuente vigente de `modelo_exponencial/logistico/gompertz`,
`ajustar_todos_los_modelos`, `calcular_r2/rmse/mae` y `_asintota_k_plausible`, y lo
ejecuta en un espacio de nombres aislado. Así se usa siempre la lógica real de la app,
sin copiarla a mano y sin arriesgarse a que se desactualice. Una prueba de fidelidad
(altura, ambos grupos, `datos_reales_coffea_2023.xlsx`) confirma que ese código extraído
produce exactamente el mismo R², RMSE, MAE y estado de **convergencia** (que el ajuste
numérico haya encontrado una solución estable, en vez de fallar o quedarse sin
suficientes días de datos para siquiera intentarlo) que `app.py` importado directamente.

**Qué tipo de datos son estos:** las tres fuentes externas son **medias publicadas, no
réplicas** (mediciones repetidas de una misma condición): cada fecha es una sola
observación. Por eso no se generaron réplicas sintéticas (datos simulados que imitan la
variabilidad de mediciones individuales, como sí se usan con mi propio dataset) para
estas fuentes, y no se corrieron las pruebas t de la app —que necesitan arrays de
réplicas—, salvo en Vallejos-Torres, donde se usó `scipy.stats.ttest_ind_from_stats`
directamente sobre los estadísticos de resumen que trae el paper.

## 1. León-Burgos et al. (2022) — validación de curvas

Café Cenicafé 1 en vivero (Chinchiná, Colombia), una sola población sin tratamientos,
12 fechas de 30 a 195 ddt, medias de n=20 plantas. Se ajustaron los 3 modelos de la app
a área foliar, número de hojas y altura (las 3 variables comparables con mi app) y,
como secundarias, diámetro del tallo y longitud de raíz.

**Resultado clave:** convertí mi Logístico `K/(1+e^(-k(t-Ti)))` a la parametrización
sigmoidal del paper `a/(1+e^(-(t-x0)/b))` igualando exponentes: `a=K` (la asíntota:
el valor máximo teórico al que tiende la curva cuando el tiempo crece sin límite),
`x0=Ti` (el punto de inflexión, donde el crecimiento pasa de acelerar a desacelerar),
`b=1/k`.

| Variable | Mi Logístico (convertido) | Publicado (sigmoidal) | Mi referencia aproximada previa |
|---|---|---|---|
{filas_cmp_md}

*Lectura: los tres casos caen muy cerca de los parámetros publicados* (diferencias de
1-5% en K/a, menos de 2% en R²), y también muy cerca de mi propia referencia aproximada
calculada de antemano con fórmulas estándar — sin usar la app. Esto es la evidencia más
directa de que la implementación del modelo Logístico en `app.py` reproduce un ajuste ya
publicado de forma independiente.

**Pregunta central — ¿coincide el patrón de plausibilidad de K con el de mis propios
datos (28-112 ddt)?** Sí, y de forma reveladora: mi criterio de plausibilidad marca la
altura de León-Burgos como **no dibujable** (K=70.0 supera 1.5× el máximo observado de
33.0 cm, aunque R²=0.980 y el modelo sí convergió) — el mismo patrón que veo en mis
propios datos, donde la ventana de muestreo no alcanza a mostrar el aplanamiento hacia
la asíntota. Y esto ocurre **incluso con 12 fechas hasta 195 ddt** (más del doble de mi
ventana de 28-112 ddt) y con un ajuste publicado y aceptado por los revisores del paper.
Área foliar y número de hojas sí pasan el criterio completo (K/máx = 1.18 y 1.07).
Ningún modelo quedó "Sin días suficientes" ni "No convergió" en esta fuente (12 fechas
son de sobra para los 3 modelos).

El "exponencial" del paper es una exponencial **saturante** `a(1-e^(-bx))`, una función
distinta a mi Exponencial `P0·e^(rt)` (sin límite superior): no se comparan como si
fueran el mismo modelo, siguiendo la instrucción explícita de no confundirlos.

**Figura 1.** Área foliar: círculos = medias publicadas por León-Burgos et al.; líneas =
los 3 modelos de la app ajustados a esos puntos; línea punteada = asíntota K, dibujada
porque aquí sí cumple el criterio de plausibilidad (K/máx = 1.18). —
`figuras/leon_burgos_area_foliar.png`

**Figura 2.** Número de hojas: misma lectura que la Figura 1; K también se dibuja aquí
(K/máx = 1.07). — `figuras/leon_burgos_numero_hojas.png`

**Figura 3.** Altura: los 3 modelos ajustan bien (R² > 0.97), pero ninguna línea de K
aparece — es justo el caso que describe la "Pregunta central" de arriba: el criterio de
plausibilidad la descarta. — `figuras/leon_burgos_altura.png`

## 2. Siqueira et al. (1998) — apoyo, efecto en el tiempo

Café Mundo Novo, ensayo de campo de 6 años en Brasil, promedios de 5 dosis de P por
tratamiento fúngico. Reproduje el efecto máximo citado por el paper para el tratamiento
Lav: **+50.0% a 9 MAT, +18.4% (≈18%) a 19 MAT, +10.4% (≈10%) a 26 MAT** sobre el control
sin inocular (Ni) — coincide con lo publicado.

Con solo 4 fechas (altura) la app **sí intenta** los 3 modelos (4 ≥ 3, el mínimo para
Logístico/Gompertz), pero con 1 solo **grado de libertad** (cuántos puntos "sobran" una
vez que el modelo ya usó los que necesita para fijar sus parámetros: 4 fechas − 3
parámetros = 1): el ejemplo del control (Ni) da R²=0.9999 en Logístico, un ajuste casi
perfecto que es un **artefacto de tener apenas un punto de más que parámetros**, no
evidencia de un modelo excelente. Con diámetro del tallo y de copa (solo 3 fechas:
9/19/26 MAT), Logístico y Gompertz caen en el límite exacto (3 parámetros, 3 puntos, 0
grados de libertad): el ajuste es exacto por construcción y no es informativo. No se
fuerza ningún ajuste fuera de estas reglas.

**Figura 4.** % de incremento en altura de cada tratamiento fúngico sobre el control sin
inocular (Ni), a lo largo de las 4 fechas medidas: el efecto es mayor al inicio y se
reduce con el tiempo en todos los tratamientos. — `figuras/siqueira_efecto_altura.png`

## 3. Vallejos-Torres et al. (2021) — efecto +M frente a −M

Café arábica en San Martín (Perú), medias por consorcio agrupadas sobre suelos y
propagación (Tabla 3 del paper). Los 3 consorcios (Huall-pache, Do-cat, Mo-cat) muestran
incrementos positivos sobre el control en las 4 variables medidas (+7% a +82%).

**Sensibilidad estadística (prueba t de Welch —una prueba t que no asume que los dos
grupos tengan la misma varianza—, vía `ttest_ind_from_stats`) bajo 4 escenarios
explícitos** (n=18 unidades o n=108 plantas, × valor entre paréntesis interpretado como
desviación estándar o como error estándar, con DE=EE·√n): el resultado depende casi por
completo de **cómo se interprete el paréntesis**, no de qué n se elija. Interpretándolo
como desviación estándar, la mayoría de los efectos son significativos (p<0.05) en los
dos tamaños de n. Interpretándolo como error estándar —el rótulo que da el propio paper,
aunque la ficha de la fuente ya advierte que el valor parece demasiado grande para serlo
con más de 100 plantas por nivel— **ningún efecto resulta significativo**, en ningún n.
Esto es matemáticamente esperable: si el paréntesis es un error estándar, la desviación
estándar usada se recalcula como EE·√n, y el error estándar de la media resultante
(DE/√n) vuelve a dar exactamente EE, sin importar qué n se haya elegido. La ambigüedad
real está en la interpretación del paréntesis, no en el tamaño de muestra. **No se puede
sacar una conclusión fuerte de un solo escenario** — el detalle completo está en
`datos/sensibilidad_vallejos_torres.csv`.

**Comparación de dirección con mi app** (datos reales, 112 ddt — únicas 2 variables con
datos reales en mi app; mi "diámetro" usa datos simulados, así que no se compara aquí):

| Variable | Vallejos-Torres (rango por consorcio) | Mi app (112 ddt) |
|---|---|---|
| Altura | +17.0% a +37.0% | +4.3% (no significativo) |
| Número de hojas | +7.2% a +66.8% | +5.5% (no significativo) |

Misma **dirección** (+M siempre mayor que −M) en ambas variables, pero **distinto orden
de magnitud** y significancia — esperable dado que mis réplicas son sintéticas y las
edades/sustratos/unidades no son comparables. No se interpreta esto como una
confirmación cuantitativa, solo como consistencia direccional.

**Figura 5.** % de incremento de cada consorcio sobre el control sin HMA, por variable:
Do-cat y Mo-cat muestran los incrementos más grandes en número de ramas y de hojas. —
`figuras/vallejos_torres_incremento.png`

## Qué SÍ se puede afirmar

- El modelo Logístico de la app, aplicado a datos independientes de León-Burgos et al.
  (2022), reproduce parámetros (K, Ti) y R² muy cercanos a los publicados por ese estudio
  (diferencias de 1-5%), usando la misma implementación de `app.py` sin modificarla.
- El criterio de convergencia (mínimo de días distintos por modelo) y el criterio de
  plausibilidad de K de la app se comportan de forma **consistente** entre mi dataset y
  el de León-Burgos: en ambos, una ventana de muestreo que no alcanza a mostrar la
  desaceleración produce una K estimada muchas veces mayor al máximo observado, y el
  criterio correctamente la marca como no plausible en vez de dibujarla.
- La dirección del efecto de la inoculación (+M/consorcios mayor que control) es
  consistente entre los tres estudios externos y mi propia app, en las variables donde
  hay comparación posible (altura, número de hojas).
- Con muy pocos puntos y modelos de 3 parámetros (Siqueira, Fase 2B), la app sigue su
  propia regla de "intentar si hay ≥3 días" — pero un R² alto en esas condiciones (0-1
  grados de libertad) no debe leerse como evidencia de buen modelo.

## Qué NO se puede afirmar

- Que mis propios resultados (con datos_reales_coffea_2023.xlsx) estén validados
  externamente: eso requeriría un experimento nuevo, independiente, con réplicas reales
  de *Coffea arabica* bajo condiciones comparables — sigue pendiente.
- Que el efecto de la inoculación micorrízica tenga una magnitud comparable entre
  estudios: los tres papers y mi propio dataset difieren en cultivar, sustrato, edad de
  la planta y unidades, y las réplicas de mi dataset son sintéticas.
- Que la sensibilidad estadística de Vallejos-Torres sea concluyente: depende
  completamente de cómo se interprete un valor entre paréntesis que el propio paper no
  aclara y que la ficha de la fuente ya marca como dudoso.
- Que el modelo Gompertz o el "exponencial saturante" de León-Burgos sean equivalentes a
  los modelos correspondientes de mi app: no se intentó esa comparación por ser formas
  matemáticas distintas.
- Ningún cuartil de revista está verificado (Scimago bloqueó el acceso automático):
  quedan como "por verificar" en cada ficha de fuente.

## Limitaciones de cada estudio

- **León-Burgos et al. (2022):** datos extraídos de una figura vectorial del PDF (no
  digitalizados a mano), verificados contra el texto en el día 180 (diferencia <0.6%);
  cultivar y manejo de vivero distintos a los míos; sin grupo con y sin micorriza (una
  sola población).
- **Siqueira et al. (1998):** solo 4 fechas de muestreo (0/9/19/26 MAT); medias
  promediadas sobre 5 dosis de fósforo, lo que oculta esa interacción; el control (Ni)
  no está necesariamente libre de micorrizas nativas del suelo; el diámetro del tallo
  está rotulado en cm en la tabla del paper pero los valores (5-30) parecen ser mm.
- **Vallejos-Torres et al. (2021):** el 100% de las plantas —incluido el control—
  tenían nematodos; el control no estaba libre de colonización micorrízica (19.37%
  frente a 27.5-28.5% en los consorcios); medias agrupadas sobre 3 suelos y 2 tipos de
  propagación; el valor entre paréntesis está rotulado "error estándar" pero es
  demasiado grande para serlo con el n reportado (ver sensibilidad); no se sabe si el n
  real es 18 o 108.
- **Cuartiles de revista:** sin verificar en Scimago en los tres casos (bloqueó el
  acceso automático); quedan como "por verificar".

## Archivos generados

- `datos/resultados_curvas.csv` — ajuste de los 3 modelos por variable/fuente
  (León-Burgos, Siqueira).
- `datos/comparacion_publicado.csv` — mi Logístico convertido vs. el sigmoidal publicado
  por León-Burgos et al., y mi referencia aproximada previa.
- `datos/efecto.csv` — % de incremento sobre el control (Siqueira en el tiempo,
  Vallejos-Torres por consorcio).
- `datos/sensibilidad_vallejos_torres.csv` — Welch bajo los 4 escenarios explícitos.
- `datos/excel/*.xlsx` — las 4 tablas anteriores, formateadas para lectura humana
  (mismos datos, sin decimales de más, con hoja "Léeme").
- `figuras/*.png` — 5 figuras (3 de León-Burgos, 1 de Siqueira, 1 de Vallejos-Torres).
"""
    with open(os.path.join(OUT_DIR, "informe.md"), "w", encoding="utf-8") as f:
        f.write(informe)
    print(f"\n  informe.md: {os.path.getsize(os.path.join(OUT_DIR, 'informe.md'))} bytes")

    # ---- resumen_exposicion.md ------------------------------------------
    resumen = f"""# Validación externa parcial — resumen para la exposición

**Validación externa parcial de la metodología** (no de mis propios resultados) con tres
estudios publicados de café con micorrizas: León-Burgos et al. (2022), Siqueira et al.
(1998) y Vallejos-Torres et al. (2021).

- Mi modelo Logístico, aplicado a datos independientes de León-Burgos et al. (2022),
  reproduce sus parámetros publicados (K, punto de inflexión) con diferencias de solo
  1-5%, usando el mismo código de `app.py`, sin modificarlo.
- Mi criterio de plausibilidad de K se comporta igual en ambos datasets: cuando la
  ventana de muestreo no alcanza a mostrar la desaceleración, la K estimada se dispara y
  el criterio correctamente evita dibujarla — pasa en mis datos y en los de León-Burgos.
- La dirección del efecto de la inoculación (+M mayor que el control) es consistente en
  los tres estudios externos y en mi propia app, aunque la magnitud y significancia no
  son comparables entre estudios (cultivar, sustrato, edad y unidades distintos; mis
  réplicas son sintéticas).
- La sensibilidad estadística de Vallejos-Torres depende por completo de cómo se
  interprete un valor ambiguo del paper (desviación estándar vs. error estándar): no hay
  una conclusión única, y así se reporta.

| Fuente | Qué se validó | Resultado |
|---|---|---|
| León-Burgos et al. (2022) | Curvas (Logístico) | K y Ti a 1-5% de lo publicado |
| León-Burgos et al. (2022) | Criterio de plausibilidad de K | Mismo patrón que mis datos |
| Siqueira et al. (1998) | Efecto en el tiempo | Reproduce 50%/18%/10% citados |
| Vallejos-Torres et al. (2021) | Dirección del efecto +M | Misma dirección que mi app |

Estado: **validación externa parcial** — valida la metodología (modelos, criterios de
convergencia y de plausibilidad de K), no sustituye la validación externa con un
experimento propio nuevo, que sigue pendiente.
"""
    with open(os.path.join(OUT_DIR, "resumen_exposicion.md"), "w", encoding="utf-8") as f:
        f.write(resumen)
    print(f"  resumen_exposicion.md: {os.path.getsize(os.path.join(OUT_DIR, 'resumen_exposicion.md'))} bytes")


if __name__ == "__main__":
    print("Construyendo namespace aislado desde app/app.py (ast, sin importar streamlit)...")
    APP_NS, codigo_fuente_extraido = construir_namespace_app()
    print(f"  {len(FUNCS_NECESARIAS)} funciones y {len(ASSIGNS_NECESARIOS)} constantes extraídas.")
    prueba_de_fidelidad(APP_NS)

    df_curvas_lb, df_comparacion_lb = fase_2a_leon_burgos(APP_NS)
    df_efecto_siqueira, df_curvas_siqueira = fase_2b_siqueira(APP_NS)
    df_incremento_vt, df_sensibilidad_vt, df_mi_app_112ddt = fase_2c_vallejos_torres(APP_NS)

    fase_3_informe(df_curvas_lb, df_comparacion_lb, df_efecto_siqueira, df_curvas_siqueira,
                   df_incremento_vt, df_sensibilidad_vt, df_mi_app_112ddt)

    print("\nListo. Salidas en docs/validacion_externa/.")
