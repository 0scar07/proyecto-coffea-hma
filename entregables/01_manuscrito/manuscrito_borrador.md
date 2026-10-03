**Estado:** Borrador para revisión del docente. No se ha enviado a ninguna revista todavía; no existe una revista destino definida. Este documento corresponde al producto "Elaborar un artículo científico sobre el modelo matemático y simulación del efecto de hongos micorrízicos arbusculares en el crecimiento de plántulas de *Coffea arabica*" (indicador: manuscrito completo enviado a revista indexada en Scopus o Web of Science).

---

# [Título provisional] Modelado y comparación de curvas de crecimiento (Exponencial, Logístico y Gompertz) en plántulas de *Coffea arabica* L. inoculadas con hongos micorrízicos arbusculares

**Autores (equipo de desarrollo del proyecto; orden de autoría por definir):** Richard Montez, Diego Barrios, Santiago Uribe, Oscar Llanos
**Afiliación:** Programa de Ingeniería, Universidad Simón Bolívar. [Facultad/departamento específico por confirmar]
**Autor de correspondencia:** [Por definir]

## Resumen

Se implementó una herramienta computacional (aplicación Coffea IA, en Streamlit) que ajusta y compara tres modelos no lineales de crecimiento — Exponencial, Logístico y Gompertz — sobre datos de altura, área foliar, biomasa total y número de hojas de *Coffea arabica* L. cv Catimor, comparando un grupo control sin inocular (−M) contra un grupo inoculado con hongos micorrízicos arbusculares (+M). Los datos utilizados provienen de Aguirre-Medina et al. (2023), quienes reportan medias y coeficientes de variación en 4 momentos de muestreo (28, 56, 84 y 112 días después del trasplante, ddt). Sobre esas medias y CV% publicados se generaron réplicas individuales sintéticas para permitir el ajuste no lineal y la prueba t de Welch entre grupos; **estos valores p ilustran la metodología estadística implementada, no son evidencia estadística independiente nueva sobre el efecto de la micorrización**, ya que no provienen de mediciones planta por planta. Con los cuatro días disponibles, el ajuste no lineal reproduce razonablemente el patrón de crecimiento acelerado (R² entre 0.876 y 0.997 en los modelos que convergen), pero Gompertz no converge en algunos grupos y varias asíntotas `K` estimadas por Logístico/Gompertz resultan biológicamente implausibles, lo que se documenta y filtra explícitamente en la herramienta. Área foliar y biomasa total muestran incrementos porcentuales de +M sobre −M estadísticamente significativos (prueba t de Welch, p < 0.05) en la mayoría de los días muestreados; altura y número de hojas, en cambio, muestran diferencias mayormente no significativas con estos datos. La validación externa con un conjunto de datos independiente queda como trabajo futuro.

## 1. Introducción

El uso de hongos micorrízicos arbusculares (HMA) como biofertilizantes en el vivero de *Coffea arabica* es de interés agronómico por su potencial efecto sobre el crecimiento temprano de la planta. Modelar matemáticamente ese crecimiento — y comparar cuantitativamente los grupos inoculado (+M) y no inoculado (−M) — requiere (a) elegir entre modelos de crecimiento con distintos supuestos biológicos (crecimiento sin límite superior vs. crecimiento sigmoide con asíntota) y (b) cuantificar con rigor estadístico si las diferencias observadas entre grupos son atribuibles al tratamiento o a variabilidad muestral.

Este trabajo presenta una herramienta computacional que automatiza ambos pasos — ajuste no lineal de tres modelos de crecimiento y prueba de hipótesis entre grupos — aplicada a los datos publicados por Aguirre-Medina et al. (2023) sobre *Coffea arabica* L. cv Catimor biofertilizado con distintos aislamientos de HMA en vivero.

## 2. Métodos

### 2.1 Modelos de crecimiento

Se ajustaron tres modelos por mínimos cuadrados no lineales (`scipy.optimize.curve_fit`):

- **Exponencial:** P(t) = P₀·e^(rt) — 2 parámetros (P₀, r).
- **Logístico:** P(t) = K / (1 + e^(−k(t−Ti))) — 3 parámetros (K, k, Ti).
- **Gompertz:** P(t) = K·e^(−e^(−k(t−Ti))) — 3 parámetros (K, k, Ti).

donde K es la asíntota superior, k la tasa de crecimiento y Ti el punto de inflexión.

### 2.2 Regla de convergencia y días mínimos

Cada modelo requiere un número mínimo de días distintos de muestreo para ser identificable, según su número de parámetros: Exponencial ≥ 2 días; Logístico y Gompertz ≥ 3 días. Si un conjunto de datos no alcanza ese mínimo, o si `curve_fit` no converge, el ajuste se marca explícitamente como "Sin días suficientes" o "No convergió" respectivamente, y se excluye de las tablas y figuras — la herramienta nunca aproxima ni fuerza un ajuste en esos casos.

### 2.3 Criterio de plausibilidad biológica de la asíntota K

Para Logístico y Gompertz, la asíntota K y su banda de confianza solo se reportan gráficamente si se cumplen las cuatro condiciones simultáneamente: (1) el modelo convergió; (2) R² ≥ 0.90; (3) K ≤ 1.5× el máximo valor observado en ese grupo y variable; (4) el punto de inflexión Ti cae dentro del rango de días efectivamente muestreados (28-112 ddt). Cuando alguna falla, la herramienta lo indica explícitamente en vez de mostrar una extrapolación sin respaldo en los datos (ver sección de Resultados para ejemplos concretos).

### 2.4 Métricas de bondad de ajuste y comparación entre grupos

Se calcularon R², RMSE y MAE para cada combinación variable × grupo × modelo. La comparación −M vs +M se realizó con prueba t de Welch (`scipy.stats.ttest_ind`, varianzas desiguales) por variable y día de muestreo, con el porcentaje de incremento de la media +M sobre la media −M.

### 2.5 Datos

Los datos de altura, número de hojas, área foliar y biomasa total (TDM), en 4 momentos de muestreo (28, 56, 84 y 112 ddt), 5 réplicas por grupo y día, provienen de:

> Aguirre-Medina, J. F.; Aguirre-Cadena, J. F.; Escobar-España, J. C.; López-González, J. L. (2023). Crecimiento de *Coffea arabica* L. cv Catimor biofertilizado con diversos aislamientos de hongos endomicorrízicos en vivero. *Revista Fitotecnia Mexicana*, 46(3), 273-281. DOI: [10.35196/rfm.2023.3.273](https://doi.org/10.35196/rfm.2023.3.273)

**Nota metodológica importante:** el paper original reporta media y desviación estándar (o CV%) por tratamiento y día, no mediciones individuales planta por planta. Las réplicas individuales usadas en este trabajo son sintéticas, generadas para reproducir exactamente esos estadísticos publicados. En consecuencia, la prueba t de Welch reportada aquí reproduce la comparación de medias del paper con una metodología estadística explícita y reproducible, pero **no constituye evidencia estadística independiente nueva** — el tamaño de muestra efectivo y la varianza entre réplicas son un artefacto de la generación sintética, no observaciones originales.

## 3. Resultados

Todas las cifras de esta sección se recalcularon directamente sobre `datos_reales_coffea_2023.xlsx` con la app (funciones `ajustar_todos_los_modelos`, `calcular_tabla_modelo`, `calcular_efecto_micorriza`); las figuras referenciadas están en `docs/figuras/`.

### 3.1 Bondad de ajuste (R² / RMSE / MAE)

| Variable | Grupo | Exponencial | Logístico | Gompertz |
|---|---|---|---|---|
| Altura (cm) | −M | R²=0.9082, RMSE=0.818, MAE=0.648 | R²=0.9082, RMSE=0.818, MAE=0.648 | No convergió |
| Altura (cm) | +M | R²=0.8759, RMSE=1.080, MAE=0.895 | R²=0.8769, RMSE=1.076, MAE=0.891 | R²=0.8762, RMSE=1.079, MAE=0.894 |
| Área foliar (cm²) | −M | R²=0.9708, RMSE=12.04, MAE=8.14 | R²=0.9718, RMSE=11.84, MAE=7.53 | R²=0.9720, RMSE=11.80, MAE=7.31 |
| Área foliar (cm²) | +M | R²=0.9933, RMSE=11.48, MAE=7.80 | R²=0.9933, RMSE=11.48, MAE=7.80 | No convergió |
| Biomasa total (g) | −M | R²=0.9968, RMSE=0.0326, MAE=0.0250 | R²=0.9968, RMSE=0.0324, MAE=0.0253 | No convergió |
| Biomasa total (g) | +M | R²=0.9908, RMSE=0.0984, MAE=0.0741 | R²=0.9940, RMSE=0.0796, MAE=0.0574 | R²=0.9935, RMSE=0.0828, MAE=0.0622 |
| Número de hojas | −M | R²=0.9115, RMSE=1.087, MAE=0.857 | R²=0.9411, RMSE=0.887, MAE=0.699 | R²=0.9364, RMSE=0.922, MAE=0.713 |
| Número de hojas | +M | R²=0.9163, RMSE=1.100, MAE=0.893 | R²=0.9623, RMSE=0.738, MAE=0.592 | R²=0.9586, RMSE=0.774, MAE=0.633 |

Modelo con mejor R² por variable/grupo: Altura −M = Exponencial, Altura +M = Logístico; Área foliar −M = Gompertz, Área foliar +M = Exponencial; Biomasa −M = Logístico, Biomasa +M = Logístico; Hojas −M = Logístico, Hojas +M = Logístico.

Ver figuras `docs/figuras/curvas_altura.png`, `curvas_area_foliar.png`, `curvas_biomasa.png`, `curvas_hojas.png` y la comparación de R² en cuadrícula 2×2 en `docs/figuras/barras_r2_modelos.png`.

### 3.2 Plausibilidad de la asíntota K

De los ocho ajustes Logístico/Gompertz calculados (2 modelos × 4 variables, excluyendo los grupos donde no convergen), la asíntota K resultó implausible o el modelo no convergió en la mayoría de los casos con esta ventana de muestreo. Ejemplos concretos (criterio de la sección 2.3):

- Altura, Logístico (−M): K estimada = 790 679.8 (cm) frente a un máximo observado de 15.0 cm — supera 1.5× el máximo por varios órdenes de magnitud.
- Área foliar, Logístico (+M): K estimada = 7 691 581.9 (cm²) frente a un máximo observado de 371.1 cm².
- Área foliar, Gompertz (−M): K estimada = 31 405.1 (cm²) frente a un máximo observado de 209.5 cm².
- Altura, Logístico (+M) y Gompertz (+M): K no se evalúa porque R² < 0.90 (0.877 y 0.876 respectivamente).

En estos casos la herramienta no dibuja la asíntota ni su banda de confianza, y lo anota explícitamente en el pie de cada figura (ver `docs/figuras/curvas_*.png`).

### 3.3 Efecto de la inoculación micorrízica (+M vs −M)

| Variable | Día (ddt) | Media −M | Media +M | Incremento +M (%) | t (Welch) | p | Significativo (p<0.05) |
|---|---|---|---|---|---|---|---|
| Altura (cm) | 28 | 7.40 | 7.80 | +5.4 | 0.816 | 0.4379 | No |
| Altura (cm) | 56 | 8.00 | 8.10 | +1.3 | 0.282 | 0.7849 | No |
| Altura (cm) | 84 | 10.30 | 12.90 | +25.2 | 7.297 | 0.0001 | Sí |
| Altura (cm) | 112 | 14.10 | 14.70 | +4.3 | 1.058 | 0.3223 | No |
| Área foliar (cm²) | 28 | 1.50 | 4.50 | +200.0 | 20.249 | <0.0001 | Sí |
| Área foliar (cm²) | 56 | 19.30 | 27.95 | +44.8 | 5.829 | 0.0008 | Sí |
| Área foliar (cm²) | 84 | 62.10 | 91.20 | +46.9 | 5.421 | 0.0022 | Sí |
| Área foliar (cm²) | 112 | 179.90 | 354.60 | +97.1 | 11.445 | <0.0001 | Sí |
| Biomasa total (g) | 28 | 0.082 | 0.093 | +13.4 | 5.790 | 0.0004 | Sí |
| Biomasa total (g) | 56 | 0.186 | 0.172 | −7.5 | −2.276 | 0.0525 | No |
| Biomasa total (g) | 84 | 0.563 | 0.935 | +66.1 | 11.043 | <0.0001 | Sí |
| Biomasa total (g) | 112 | 1.535 | 2.635 | +71.7 | 15.327 | <0.0001 | Sí |
| Número de hojas | 28 | 2.00 | 2.00 | 0.0 | 0.000 | 1.0000 | No |
| Número de hojas | 56 | 3.60 | 4.40 | +22.2 | 2.270 | 0.0563 | No |
| Número de hojas | 84 | 8.00 | 8.80 | +10.0 | 1.193 | 0.2678 | No |
| Número de hojas | 112 | 11.00 | 11.60 | +5.5 | 0.759 | 0.4742 | No |

Recordando la nota metodológica de la sección 2.5, estos valores p reflejan la comparación de las medias sintéticas reconstruidas a partir del paper, no un experimento independiente nuevo.

## 4. Discusión

La ventana de muestreo disponible (28-112 ddt) captura sobre todo la fase de crecimiento acelerado de la plántula y no alcanza a mostrar el "codo" de desaceleración que Logístico y Gompertz necesitan para estimar una asíntota K confiable. Esto explica por qué, con solo 4 puntos por grupo (1 grado de libertad para un modelo de 3 parámetros), Gompertz no converge en varios grupos (altura −M, área foliar +M, biomasa −M) y por qué varias K estimadas por Logístico/Gompertz son órdenes de magnitud mayores que el máximo observado — no un error de la herramienta, sino una limitación esperada del diseño de muestreo original.

En las variables donde el efecto de la inoculación aparece significativo de forma consistente (área foliar, en los 4 días; biomasa total, en 3 de 4 días), el patrón es compatible con lo reportado por Aguirre-Medina et al. (2023), aunque — se insiste — sobre réplicas sintéticas.

## 5. Limitaciones y trabajo futuro

- Los p-values de este trabajo provienen de réplicas sintéticas ajustadas a estadísticos publicados, no de mediciones individuales; no deben citarse como evidencia estadística independiente.
- No existe todavía validación externa de los tres modelos contra un conjunto de datos de *Coffea arabica* distinto al de Aguirre-Medina et al. (2023). Solo existe una validación interna de estabilidad de medias (hold-out 80/20, `scripts/validacion_cruzada_real.py`), que no mide generalización.
- Un diseño de muestreo que cubra también la fase de desaceleración del crecimiento permitiría estimar K de forma más confiable en Logístico y Gompertz.

## Referencias

Aguirre-Medina, J. F.; Aguirre-Cadena, J. F.; Escobar-España, J. C.; López-González, J. L. (2023). Crecimiento de *Coffea arabica* L. cv Catimor biofertilizado con diversos aislamientos de hongos endomicorrízicos en vivero. *Revista Fitotecnia Mexicana*, 46(3), 273-281. DOI: 10.35196/rfm.2023.3.273
