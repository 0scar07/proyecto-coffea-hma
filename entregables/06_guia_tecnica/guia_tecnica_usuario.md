**Estado:** Borrador para revisión del docente. Corresponde al producto "Desarrollar una guía práctica de uso e interpretación del modelo computacional y sus curvas de simulación para apoyar la toma de decisiones en viveros cafeteros" (indicador: documento técnico disponible en formato digital para consulta y distribución).

---

# Guía técnica de uso — Coffea IA

Esta guía explica, sección por sección, cómo usar la app Coffea IA y cómo interpretar sus resultados. Los nombres de sección se verificaron directamente contra el código (`app/app.py`, bloques `if seccion == "..."`) el 2026-09-19.

## 1. Antes de empezar: formato de los datos

La app acepta datos en formato largo, con estas columnas exactas (verificado contra `datos_reales/datos_reales_coffea_2023.xlsx`, hoja `datos`):

| Columna | Significado | Ejemplo |
|---|---|---|
| `variable` | Qué se midió | `altura`, `area_foliar`, `biomasa`, `hojas`, `diametro` |
| `grupo` | Tratamiento | `-M` (control) o `+M` (inoculado) |
| `dat` | Día después del trasplante | `28`, `56`, `84`, `112` |
| `replica` | Número de réplica | `1`, `2`, `3`, `4`, `5` |
| `valor` | Valor medido | ej. `9.0538` |

Puedes descargar una plantilla en blanco con este formato desde la sección **Datos de prueba** de la app, o usar directamente el Excel real incluido en `datos_reales/`.

## 2. Recorrido por las secciones

### Resumen

Pantalla inicial: muestra el estado general (si ya se ajustaron modelos o no, y con qué fuente de datos).

![Resumen](../../docs/screenshots/resumen.png)

### Ajustar modelos

Aquí se dispara el ajuste no lineal (`curve_fit`) de los tres modelos sobre cada variable y grupo. Presiona el botón **Ajustar modelos** después de cargar tus datos.

![Ajustar modelos](../../docs/screenshots/ajustar_modelos.png)

### Metodología

Explica, en lenguaje editorial, la fórmula y el significado de cada modelo (Exponencial, Logístico, Gompertz).

![Metodología](../../docs/screenshots/metodologia.png)

### Resultados

Muestra las curvas ajustadas por variable: panel (a) para el grupo −M y panel (b) para +M, con las réplicas observadas (círculos), las curvas de los modelos que convergieron, la banda de confianza del 95% y, cuando es plausible, la asíntota K (ver sección 3 de esta guía). Incluye, en un expander, las **tasas de crecimiento (AGR/RGR)**.

![Resultados](../../docs/screenshots/curvas.png)
![Tasas de crecimiento](../../docs/screenshots/tasas.png)

### Gráficas de barras

Barras de medias ± desviación estándar por día y grupo, con marcas de significancia estadística (ns/\*/\*\*/\*\*\*), y una comparación de R² por modelo en cuadrícula 2×2.

![Gráficas de barras](../../docs/screenshots/barras.png)

### Resultados esperados

Dos tablas generadas automáticamente: (1) el modelo con mejor R² por variable y grupo, y (2) el efecto de la inoculación micorrízica (+M vs −M) con la prueba t de Welch.

![Resultados esperados](../../docs/screenshots/resultados_esperados.png)

### Estadística

Intervalos de confianza por parámetro y detalle de la prueba t de Welch entre −M y +M.

![Estadística](../../docs/screenshots/estadistica.png)

### Residuos

Diagnóstico de ajuste: gráficas de residuos por modelo y grupo, útiles para ver si un modelo con buen R² igual tiene un patrón sistemático de error.

![Residuos](../../docs/screenshots/residuos.png)

### Discusión y conclusiones

Lectura editorial de los resultados generales del ajuste. *(No se incluye captura propia; el contenido es texto generado dinámicamente según la fuente de datos activa.)*

### Datos de prueba

Permite generar datos simulados, descargar la plantilla de Excel, o subir un archivo propio (o el real de `datos_reales/`) para reemplazar los datos simulados.

### Exportar reporte

Genera un PDF con metodología, tablas y las mismas gráficas mostradas en la app. Un ejemplo ya generado está en `docs/reportes/reporte_ejemplo_datos_reales.pdf` (18 páginas, ~2.43 MB, con datos reales).

## 3. Cómo interpretar los resultados

### R², RMSE, MAE

- **R²** (0 a 1): qué tan bien el modelo explica la variación observada. Más cerca de 1 es mejor, pero un R² alto en un modelo con muy pocos puntos (como aquí: 4 días) no garantiza que la forma del modelo sea la correcta — hay que mirarlo junto con RMSE/MAE y con el gráfico de residuos.
- **RMSE** (raíz del error cuadrático medio) y **MAE** (error absoluto medio): están en las mismas unidades que la variable (cm, cm², g, etc.); penalizan más los errores grandes RMSE que MAE. Sirven para comparar modelos entre sí en la misma variable — no tiene sentido comparar el RMSE de "altura" (cm) contra el de "biomasa" (g).

### "No convergió" y "Sin días suficientes"

- **"Sin días suficientes"**: el modelo necesita más días distintos de muestreo de los que hay disponibles para ese grupo/variable (Exponencial necesita ≥ 2 días; Logístico y Gompertz, ≥ 3, por su número de parámetros). La app no intenta el ajuste en absoluto.
- **"No convergió"**: el modelo sí tenía suficientes días, pero el algoritmo de mínimos cuadrados no encontró una solución estable. Es más común en Gompertz con solo 4 puntos por grupo.

En ambos casos, la app **no** muestra un R² ni dibuja una curva — es preferible mostrar la ausencia de resultado a inventar un ajuste poco confiable.

### La asíntota K (Logístico y Gompertz)

La app solo dibuja la línea de la asíntota K (y su banda de confianza) si se cumplen las cuatro condiciones a la vez:

1. El modelo convergió.
2. R² ≥ 0.90.
3. K ≤ 1.5× el máximo valor observado en ese grupo y variable.
4. El punto de inflexión del modelo cae dentro del rango de días efectivamente muestreados (28-112 ddt).

Cuando alguna condición falla, la app lo dice explícitamente en el pie de la figura (por ejemplo, "Logístico (−M): K no se dibuja porque supera 1.5× el máximo observado") en vez de mostrar una extrapolación sin respaldo. Esto es frecuente con estos datos porque la ventana de 28 a 112 días después del trasplante cubre sobre todo la fase acelerada del crecimiento, no la fase de desaceleración que un modelo sigmoide necesita para fijar su asíntota con confianza.

### Significancia estadística (ns / \* / \*\* / \*\*\*)

Basada en la prueba t de Welch entre −M y +M para cada día: ns = p ≥ 0.05 (no significativo), \* = p < 0.05, \*\* = p < 0.01, \*\*\* = p < 0.001.

**Importante:** con el dataset real, estas réplicas son sintéticas (generadas a partir de las medias y CV% de Aguirre-Medina et al., 2023 — el paper no publica mediciones planta por planta). Los valores p ilustran la metodología estadística de la app, no son evidencia estadística independiente nueva.

## 4. Preguntas frecuentes

**¿Por qué un modelo con R² alto no dibuja su asíntota K?**
Porque R² alto no implica que K esté bien identificada — puede fallar el criterio de rango (K ≤ 1.5× el máximo observado) o el del punto de inflexión, aunque el ajuste general sea bueno en los puntos observados. Ver sección 3 de esta guía.

**¿Puedo confiar en los p-values del dataset real como si fueran un resultado experimental nuevo?**
No de forma independiente: las réplicas individuales del dataset real son sintéticas. Los p-values reproducen la comparación de medias del paper original con una metodología transparente, pero no son una validación externa nueva.

**¿La app "entrena" un modelo de machine learning?**
No. Es una regresión no lineal por mínimos cuadrados (`scipy.optimize.curve_fit`) sobre tres fórmulas matemáticas fijas — no hay ningún componente de aprendizaje automático.

**¿Qué pasa si subo mi propio Excel con otra variable?**
Debe respetar las columnas `variable, grupo, dat, replica, valor` (sección 1 de esta guía). Si tu variable tiene menos días distintos de los que un modelo necesita, ese modelo mostrará "Sin días suficientes" para tu variable, igual que ocurre hoy con los datos incluidos.

**¿Dónde veo la validación de que las medias reportadas son estables?**
En `scripts/validacion_cruzada_real.py`, que hace un hold-out 80/20 repetido 200 veces sobre las réplicas sintéticas — mide estabilidad de la media, no generalización a datos nuevos (ver `entregables/09_metodologia_estadistica/`).
