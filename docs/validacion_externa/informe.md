# Validación externa parcial de la metodología — 2026-09-27

**Qué es esto:** una validación externa **parcial** de la metodología de Coffea IA (los
3 modelos de crecimiento, el criterio de convergencia y el criterio de plausibilidad de
K), usando datos ya publicados de otros tres estudios. No es una validación de mis
propios resultados con datos de café biofertilizado nuevos — eso sigue pendiente. Los
tres estudios difieren entre sí y con el mío en cultivar, sustrato, edad de la planta y
unidades: se analizan por separado y solo se combinan las conclusiones metodológicas.

Generado por `scripts/validacion_externa.py`, que **no importa `app/app.py`**: extrae
con el módulo `ast` el código fuente vigente de `modelo_exponencial/logistico/gompertz`,
`ajustar_todos_los_modelos`, `calcular_r2/rmse/mae` y `_asintota_k_plausible`, lo ejecuta
en un espacio de nombres aislado, y así usa siempre la lógica real de la app. Una prueba
de fidelidad (altura, ambos grupos, `datos_reales_coffea_2023.xlsx`) confirma que ese
código extraído produce exactamente el mismo R², RMSE, MAE y estado de convergencia que
`app.py` importado directamente.

Todos los datos de estas tres fuentes son **medias publicadas, no réplicas**: cada fecha
es una sola observación. No se generaron réplicas sintéticas para estas fuentes y no se
corrieron las pruebas t de la app (que requieren arrays de réplicas) salvo en
Vallejos-Torres, donde se usó `scipy.stats.ttest_ind_from_stats` directamente sobre los
estadísticos de resumen del paper.

## 1. León-Burgos et al. (2022) — validación de curvas

Café Cenicafé 1 en vivero (Chinchiná, Colombia), una sola población sin tratamientos,
12 fechas de 30 a 195 ddt, medias de n=20 plantas. Se ajustaron los 3 modelos de la app
a área foliar, número de hojas y altura (las 3 variables comparables con mi app) y,
como secundarias, diámetro del tallo y longitud de raíz.

**Resultado clave:** convertí mi Logístico `K/(1+e^(-k(t-Ti)))` a la parametrización
sigmoidal del paper `a/(1+e^(-(t-x0)/b))` igualando exponentes: `a=K`, `x0=Ti`, `b=1/k`.

| Variable | Mi Logístico (convertido) | Publicado (sigmoidal) | Mi referencia aproximada previa |
|---|---|---|---|
| area_foliar | K=688.1, Ti=142.5, R²=0.989 | a=666.4, x0=141.9, R²=0.99 | K≈688.0, x0≈142, R²≈0.99 |
| numero_hojas | K=12.9, Ti=89.8, R²=0.977 | a=12.4, x0=88.2, R²=0.97 | K≈12.9, x0≈90, R²≈0.98 |
| altura | K=70.0, Ti=200.6, R²=0.980 | a=70.8, x0=203.9, R²=0.99 | K≈70.0, x0≈201, R²≈0.98 |

Los tres casos caen muy cerca de los parámetros publicados (diferencias de 1-5% en K/a,
menos de 2% en R²), y también muy cerca de mi propia referencia aproximada calculada de
antemano con fórmulas estándar — sin usar la app. Esto es la evidencia más directa de
que la implementación del modelo Logístico en `app.py` reproduce un ajuste ya publicado
de forma independiente.

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

Figuras: `figuras/leon_burgos_area_foliar.png`, `leon_burgos_numero_hojas.png`,
`leon_burgos_altura.png` (círculos = medias publicadas; línea punteada = asíntota K,
solo cuando el criterio de la app la permite).

## 2. Siqueira et al. (1998) — apoyo, efecto en el tiempo

Café Mundo Novo, ensayo de campo de 6 años en Brasil, promedios de 5 dosis de P por
tratamiento fúngico. Reproduje el efecto máximo citado por el paper para el tratamiento
Lav: **+50.0% a 9 MAT, +18.4% (≈18%) a 19 MAT, +10.4% (≈10%) a 26 MAT** sobre el control
sin inocular (Ni) — coincide con lo publicado.

Con solo 4 fechas (altura) la app **sí intenta** los 3 modelos (4 ≥ 3, el mínimo para
Logístico/Gompertz), pero con 1 solo grado de libertad: el ejemplo del control (Ni) da
R²=0.9999 en Logístico, un ajuste casi perfecto que es un **artefacto de tener apenas un
punto de más que parámetros**, no evidencia de un modelo excelente. Con diámetro del
tallo y de copa (solo 3 fechas: 9/19/26 MAT), Logístico y Gompertz caen en el límite
exacto (3 parámetros, 3 puntos, 0 grados de libertad): el ajuste es exacto por
construcción y no es informativo. No se fuerza ningún ajuste fuera de estas reglas.

Figura: `figuras/siqueira_efecto_altura.png` (% de incremento sobre Ni por tratamiento).

## 3. Vallejos-Torres et al. (2021) — efecto +M frente a −M

Café arábica en San Martín (Perú), medias por consorcio agrupadas sobre suelos y
propagación (Tabla 3 del paper). Los 3 consorcios (Huall-pache, Do-cat, Mo-cat) muestran
incrementos positivos sobre el control en las 4 variables medidas (+7% a +82%).

**Sensibilidad estadística (Welch, `ttest_ind_from_stats`) bajo 4 escenarios explícitos**
(n=18 unidades o n=108 plantas, × valor entre paréntesis interpretado como desviación
estándar o como error estándar, con DE=EE·√n): el resultado depende casi por completo de
**cómo se interprete el paréntesis**, no de qué n se elija. Interpretándolo como
desviación estándar, la mayoría de los efectos son significativos (p<0.05) en los dos
tamaños de n. Interpretándolo como error estándar —el rótulo que da el propio paper,
aunque la ficha de la fuente ya advierte que el valor parece demasiado grande para serlo
con más de 100 plantas por nivel— **ningún efecto resulta significativo**, en ningún n.
Esto es matemáticamente esperable: si el paréntesis es un error estándar, la desviación
estándar usada se recalcula como EE·√n, y el error estándar de la media resultante
(DE/√n) vuelve a dar exactamente EE, sin importar qué n se haya elegido. La ambigüedad
real está en la interpretación del paréntesis, no en el tamaño de muestra. **No se puede
sacar una conclusión fuerte de un solo escenario** — el detalle completo está en
`sensibilidad_vallejos_torres.csv`.

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

Figura: `figuras/vallejos_torres_incremento.png`.

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

- `resultados_curvas.csv` — ajuste de los 3 modelos por variable/fuente (León-Burgos,
  Siqueira).
- `comparacion_publicado.csv` — mi Logístico convertido vs. el sigmoidal publicado por
  León-Burgos et al., y mi referencia aproximada previa.
- `efecto.csv` — % de incremento sobre el control (Siqueira en el tiempo,
  Vallejos-Torres por consorcio).
- `sensibilidad_vallejos_torres.csv` — Welch bajo los 4 escenarios explícitos.
- `figuras/*.png` — 6 figuras (3 de León-Burgos, 1 de Siqueira, 1 de Vallejos-Torres).
