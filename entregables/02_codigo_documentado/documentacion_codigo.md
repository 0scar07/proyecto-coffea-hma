**Estado:** En preparación — documentación externa del código ya existente. **No se modificó `app/app.py`** para producir este documento (tocar ese archivo dispara un redeploy en Streamlit Cloud); ver la sección final "Propuesta no aplicada" para una sugerencia de docstrings que el equipo puede decidir aplicar después.

Este documento corresponde al producto "Implementar un algoritmo de ajuste y validación predictiva de modelos de crecimiento biológico" (indicador: código fuente documentado con curvas ajustadas, valores predichos y métricas de desempeño calculadas).

---

# Documentación técnica de `app/app.py`

Todo el código de la aplicación vive en un único archivo, `app/app.py` (2749 líneas, verificado con `wc -l` el 2026-09-19), que Streamlit Cloud ejecuta directamente como archivo principal. No hay paquetes ni módulos adicionales dentro de `app/`.

## 1. Arquitectura general

El archivo se organiza, de arriba hacia abajo, en estas capas:

1. **Estilo y composición visual** (líneas ~212-428): funciones que dan formato a las figuras de Plotly (`estilo_publicacion`, `alinear_titulos_panel_izquierda`) y que separan el pie/caption de cada figura del gráfico mismo (`construir_pie`, `pie_a_lineas_texto`, `mostrar_pie_streamlit`, `componer_png_con_pie`).
2. **Modelos matemáticos** (líneas ~429-435): las tres funciones puras `modelo_exponencial`, `modelo_logistico`, `modelo_gompertz` — la definición matemática de cada curva, sin ningún efecto secundario.
3. **Datos y utilidades numéricas** (líneas ~478-556): generación de datos simulados, manejo de réplicas por día/grupo, y las métricas de bondad de ajuste (`calcular_r2`, `calcular_rmse`, `calcular_mae`).
4. **Ajuste de modelos y pruebas estadísticas** (líneas ~557-714): el núcleo del ajuste no lineal (`ajustar_todos_los_modelos`), la prueba t de Welch (`prueba_t_independiente`), y las reglas de estado ("No convergió"/"Sin días suficientes") que **no se modificaron** en ningún trabajo de presentación anterior.
5. **Construcción de figuras** (líneas ~716-1151): una función por tipo de gráfica (barras por variable, resumen 2×2, comparación de R², curvas de crecimiento publicables, tasas AGR/RGR, bandas de confianza Monte Carlo).
6. **Reporte PDF** (dentro de la sección `"Exportar reporte"`, ~línea 2331 en adelante): la clase `ReportePDF(FPDF)` y las funciones de composición del documento.
7. **Entrada/salida de datos** (líneas ~1324-1434): lectura/escritura de Excel en formato largo, plantilla descargable, validación de archivos subidos.
8. **Navegación e interfaz** (resto del archivo): un bloque `if seccion == "...": ... elif seccion == "...":` por cada sección del menú lateral, que arma la interfaz de Streamlit reutilizando las funciones anteriores.

## 2. Flujo de datos

```
Excel subido / datos simulados
        │
        ▼
 datos[variable][grupo][dia] -> lista de réplicas (np.array)
        │
        ▼
 ajustar_todos_los_modelos(datos)          <- corre curve_fit para los 3 modelos
        │                                      x cada variable x cada grupo
        ▼
 RES[variable][grupo][modelo] = {
     "params", "pcov", "r2", "rmse", "mae",
     "insuficiente", "convergio", ...
 }
        │
        ├──► fig_curvas_publicacion / fig_tasas_crecimiento / fig_barras_*   (Plotly)
        ├──► calcular_tabla_modelo / calcular_efecto_micorriza              (tablas)
        └──► ReportePDF                                                     (PDF)
```

`RES` es el diccionario central: todo lo que se muestra en pantalla o se exporta a PDF se deriva de él, nunca se recalculan los modelos por separado para cada gráfica.

## 3. Funciones principales

### 3.1 Modelos de crecimiento (sin cambios, núcleo científico)

| Función | Entradas | Salida | Qué implementa |
|---|---|---|---|
| `modelo_exponencial(t, P0, r)` | tiempo, P0, r | valor predicho | P(t) = P₀·e^(rt) |
| `modelo_logistico(t, K, k, Ti)` | tiempo, K, k, Ti | valor predicho | P(t) = K/(1+e^(−k(t−Ti))) |
| `modelo_gompertz(t, K, k, Ti)` | tiempo, K, k, Ti | valor predicho | P(t) = K·e^(−e^(−k(t−Ti))) |
| `ajustar_todos_los_modelos(datos)` | dict de datos por variable/grupo/día | dict `RES` con parámetros, R², RMSE, MAE y estado por modelo | Corre `scipy.optimize.curve_fit` para los tres modelos sobre cada variable y grupo; aplica la regla de días mínimos (Exponencial ≥2, Logístico/Gompertz ≥3) antes de intentar el ajuste |
| `prueba_t_independiente(datos, variable, dia)` | datos, variable, día | estadístico t, p-value | Prueba t de Welch (`scipy.stats.ttest_ind`, `equal_var=False`) entre −M y +M |
| `estado_de_ajuste(res)` | resultado de un ajuste | `"OK"` / `"No convergió"` / `"Sin días suficientes"` | Vocabulario unificado de estado, usado en toda la app y el PDF |
| `_asintota_k_plausible(res, y_max_obs_grupo, dia_min, dia_max)` | resultado, máximo observado, rango de días | `(dibujar: bool, K, motivo)` | Criterio de 4 condiciones para decidir si la asíntota K es biológicamente plausible (ver `entregables/06_guia_tecnica/` para el detalle) |

### 3.2 Métricas de bondad de ajuste

| Función | Qué calcula |
|---|---|
| `calcular_r2(y_obs, y_pred)` | Coeficiente de determinación R² |
| `calcular_rmse(y_obs, y_pred)` | Raíz del error cuadrático medio |
| `calcular_mae(y_obs, y_pred)` | Error absoluto medio |

### 3.3 Tablas de resultados (usadas en "Resultados esperados" y el PDF)

| Función | Entradas | Salida |
|---|---|---|
| `calcular_tabla_modelo(RES, datos, variable, modelos)` | resultados del ajuste, datos, variable, lista de modelos | filas con R²/RMSE/MAE por grupo y modelo, más el modelo con mejor R² por grupo |
| `calcular_efecto_micorriza(datos, variable)` | datos, variable | filas por día con media −M, media +M, incremento %, t, p, significancia |
| `texto_interpretativo_efecto(variable, fila)` | variable, una fila de la tabla anterior | texto en español que interpreta el resultado de esa fila |

### 3.4 Construcción de figuras (Plotly)

| Función | Qué produce |
|---|---|
| `fig_curvas_publicacion(datos, RES, variable, modelos, fuente_datos)` | Curvas ajustadas, panel (a) −M / panel (b) +M, réplicas observadas, banda de confianza y asíntota K (cuando es plausible). Devuelve `(fig, pie)`. |
| `fig_tasas_crecimiento(datos, RES, variable, modelos, fuente_datos)` | Paneles AGR (tasa absoluta) y RGR (tasa relativa) calculados analíticamente a partir de los parámetros ya ajustados, sin reajustar. Devuelve `(fig, pie)` o `(None, motivo)`. |
| `fig_barras_variable(datos, variable, fuente_datos)` | Barras de medias ± DE por día con marcas de significancia (ns/\*/\*\*/\*\*\*). |
| `fig_barras_resumen_2x2(datos, variables, fuente_datos)` | Las barras de las 4 variables en una cuadrícula 2×2. |
| `fig_barras_r2_comparacion(RES, datos, variables, modelos)` | Comparación de R² por modelo y variable, también en cuadrícula 2×2. |
| `calcular_banda_confianza(func, popt, pcov, t_eval, n_muestras, semilla_mc)` | Banda de confianza del 95% por remuestreo Monte Carlo de la matriz de covarianza de `curve_fit`. |
| `calcular_agr_rgr(modelo, params, t)` | AGR = dP/dt y RGR = (1/P)·dP/dt, derivadas analíticas de cada modelo. |

### 3.5 Estilo y separación figura/pie (capa de presentación)

| Función | Rol |
|---|---|
| `estilo_publicacion(fig, ...)` | Aplica fuente, márgenes, ticks y leyenda horizontal a cualquier figura de Plotly. |
| `alinear_titulos_panel_izquierda(fig, n_paneles)` | Alinea las etiquetas "(a) −M" / "(b) +M" a la izquierda de cada panel. |
| `construir_pie(descripcion, notas, extra)` | Empaqueta el texto del pie de figura como datos (no como anotación de Plotly). |
| `mostrar_pie_streamlit(pie)` | Renderiza el pie como `st.caption`/`st.markdown` debajo de la figura en la app. |
| `componer_png_con_pie(png_bytes, pie, scale)` | Compone la imagen PNG descargable con el pie de texto debajo, usando Pillow. |

### 3.6 Entrada/salida de datos

| Función | Rol |
|---|---|
| `datos_a_formato_largo(datos)` | Convierte el diccionario interno a un DataFrame en formato largo (`variable, grupo, dat, replica, valor`). |
| `generar_plantilla_excel()` | Genera el Excel descargable de plantilla para que el usuario suba sus propios datos. |
| `cargar_datos_desde_archivo(archivo)` | Lee y valida un Excel/CSV subido por el usuario, verificando las columnas obligatorias. |
| `advertir_dias_insuficientes(datos)` | Revisa qué modelos no tendrán suficientes días para converger, antes de intentar el ajuste. |

### 3.7 Reporte PDF

La clase `ReportePDF(FPDF)` (definida dentro de la sección "Exportar reporte") personaliza encabezado y pie de página. El documento se arma sección por sección (metodología, tablas, figuras — las mismas que en la app, reinsertadas con `insertar_imagen_png`/`insertar_pie_pdf` — y conclusiones), y termina en `pdf_bytes = bytes(pdf.output())`, que se ofrece como descarga con `st.download_button`.

## 4. Cómo correr y probar la app

Ver `entregables/06_guia_tecnica/guia_tecnica_usuario.md` para instrucciones de uso, y el `README.md` principal del repositorio para instalación (`pip install -r app/requirements.txt`, `streamlit run app/app.py`).

Para pruebas automatizadas sin abrir un navegador, la app se puede ejercitar con `streamlit.testing.v1.AppTest`, por ejemplo:

```python
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app/app.py", default_timeout=60)
at.run()
at.session_state["seccion"] = "Ajustar modelos"
at.run()
# ... click de botones, verificación de at.exception, etc.
```

No existe todavía una carpeta `tests/` versionada en el repositorio con estos scripts — es una posible mejora futura, no incluida en este entregable.

## 5. Propuesta no aplicada: docstrings

Al revisar el archivo (`grep -c '"""' app/app.py` = 72, es decir unos 36 bloques de docstring ya existentes sobre 47 funciones/clases), la mayoría de las funciones de ajuste y estado ya tienen docstring explicando su criterio (por ejemplo `_asintota_k_plausible`, `ajustar_todos_los_modelos`). Las que **no** tienen docstring y se beneficiarían de uno son principalmente las funciones de construcción de figuras (`fig_barras_variable`, `fig_barras_resumen_2x2`, `fig_tasas_crecimiento`) y las de I/O de datos (`cargar_datos_desde_archivo`, `generar_plantilla_excel`).

**Esta propuesta no se aplicó**: modificar `app/app.py` dispara un redeploy en Streamlit Cloud, y la decisión de tocar el archivo de producción le corresponde al equipo. Si se decide aplicarla, bastaría con agregar un docstring de una o dos líneas (entradas/salida/qué gráfica produce) a cada una de esas funciones, sin cambiar ninguna lógica.
