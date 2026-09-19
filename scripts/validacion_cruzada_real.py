# -*- coding: utf-8 -*-
"""
Validacion cruzada (hold-out 80/20) sobre los datos REALES del paper:
Aguirre-Medina, J. F.; Aguirre-Cadena, J. F.; Escobar-Espana, J. C.;
Lopez-Gonzalez, J. L. (2023). Crecimiento de Coffea arabica L. cv Catimor
biofertilizado con diversos aislamientos de hongos endomicorrizicos en vivero.
Revista Fitotecnia Mexicana, 46(3), 273-281. DOI: 10.35196/rfm.2023.3.273
Cuadro 2: altura, area foliar, biomasa total y numero de hojas en 4 momentos
de muestreo (28, 56, 84 y 112 dias despues del trasplante), 5 replicas/grupo/dia.

Metodo: para cada variable/grupo/dia se separan las 5 replicas en 80%
entrenamiento / 20% prueba, de forma aleatoria, repitiendo 200 veces. Se
compara la media del set de entrenamiento contra la media del set de prueba
(escondido) -- si el error es bajo y estable, la media reportada es confiable
y no depende de que replicas especificas cayeron en la muestra.

Nota: con solo 5 replicas por combinacion, el split 80/20 es 4 vs 1 -- un
holdout muy pequeno. Se lee directamente el Excel bundleado en este mismo
directorio en vez de hardcodear valores, para no desincronizarse otra vez
del dataset real si este se actualiza.
"""
import os
import numpy as np
import pandas as pd

RUTA_EXCEL = os.path.join(os.path.dirname(__file__), "datos_reales_coffea_2023.xlsx")


def validacion_cruzada_holdout(valores, prop_entrenamiento=0.8, n_repeticiones=200, seed=123):
    rng = np.random.default_rng(seed)
    n = len(valores)
    n_train = max(1, int(round(n * prop_entrenamiento)))
    if n_train >= n:
        n_train = n - 1
    errores_pct = []
    for _ in range(n_repeticiones):
        idx = rng.permutation(n)
        media_train = valores[idx[:n_train]].mean()
        media_test = valores[idx[n_train:]].mean()
        if media_train == 0:
            continue
        errores_pct.append(abs(media_test - media_train) / media_train * 100)
    return np.mean(errores_pct), np.max(errores_pct)


if __name__ == "__main__":
    df = pd.read_excel(RUTA_EXCEL, sheet_name=0)
    df.columns = [c.strip().lower() for c in df.columns]

    print("VALIDACION CRUZADA (hold-out 80/20, 200 repeticiones) - datos REALES\n")
    for (variable, grupo, dat), grupo_df in df.groupby(["variable", "grupo", "dat"]):
        valores = grupo_df["valor"].to_numpy(dtype=float)
        err_prom, err_max = validacion_cruzada_holdout(valores)
        print(f"{variable:12s} {grupo:3s}  dat={dat:3d}  n={len(valores)}: "
              f"error % promedio = {err_prom:5.2f}%  |  error % maximo = {err_max:5.2f}%")
