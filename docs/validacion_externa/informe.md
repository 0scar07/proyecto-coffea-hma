# Validación externa parcial de la metodología — 2026-09-27

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
| area_foliar | K=688.1, Ti=142.5, R²=0.989 | a=666.4, x0=141.9, R²=0.99 | K≈688.0, x0≈142, R²≈0.99 |
| numero_hojas | K=12.9, Ti=89.8, R²=0.977 | a=12.4, x0=88.2, R²=0.97 | K≈12.9, x0≈90, R²≈0.98 |
| altura | K=70.0, Ti=200.6, R²=0.980 | a=70.8, x0=203.9, R²=0.99 | K≈70.0, x0≈201, R²≈0.98 |

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
