# Coffea IA · Modelado de crecimiento

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-013243?style=flat&logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-8CAAE6?style=flat&logo=scipy&logoColor=black)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat&logo=plotly&logoColor=white)
![Excel](https://img.shields.io/badge/Excel-217346?style=flat&logo=microsoftexcel&logoColor=white)
![License MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)

**Desarrollado por:** Richard Montez, Diego Barrios, Santiago Uribe y Oscar Llanos

Aplicación en Streamlit que ajusta y compara tres modelos matemáticos de
crecimiento (**Exponencial**, **Logístico**, **Gompertz**) sobre datos de
biomasa, área foliar, altura, diámetro del tallo y número de hojas de
*Coffea arabica*, comparando un grupo control sin inocular (**−M**) frente a
un grupo inoculado con Hongos Micorrízicos Arbusculares (**+M**).

Incluye ajuste por mínimos cuadrados no lineales, bandas de confianza al
95%, pruebas t de Welch, análisis de residuos, carga de datos propios en
formato largo (CSV/Excel) y exportación de un reporte en PDF.

## Capturas

**Resumen**

![Resumen](docs/screenshots/resumen.png)

**Ajustar modelos** — configuración del ajuste y resultado inmediato con
badges de bondad de ajuste (R²) por grupo y modelo

![Ajustar modelos](docs/screenshots/ajustar_modelos.png)

**Metodología** — explicación de cada modelo con tratamiento editorial

![Metodología](docs/screenshots/metodologia.png)

**Estadística** — intervalos de confianza y prueba t de Welch entre −M y +M

![Estadística](docs/screenshots/estadistica.png)

**Residuos** — diagnóstico de ajuste por modelo y grupo

![Residuos](docs/screenshots/residuos.png)

**Resultados con datos reales** — con los 4 días de muestreo del Cuadro 2
del paper, la app ajusta curvas completas para −M y +M en cada variable
(cuando un dataset tiene menos días de los que un modelo necesita, la app
avisa de inmediato y muestra una comparación directa en vez de forzar un
ajuste sin sentido)

![Resultados con datos reales](docs/screenshots/resultados_datos_reales.png)

## Qué resuelve

- **Comparación de modelos**: ajusta los tres modelos a los mismos datos y
  compara con R², RMSE y MAE antes de elegir el definitivo.
- **Rigor estadístico**: no solo un R² — también intervalos de confianza
  por parámetro y una prueba t de Welch con las réplicas reales entre −M y
  +M.
- **Validación de datos honesta**: si un dataset (real o de prueba) no
  tiene suficientes días distintos de muestreo para identificar un modelo
  (Exponencial necesita ≥2 días; Logístico y Gompertz ≥3), la app lo
  advierte de inmediato al cargar el archivo y muestra un badge
  "Sin suficientes días" en vez de inventar un ajuste — nunca un R² falso.
- **Datos simulados + datos reales conviven**: mientras se completa la
  validación con datos reales para todas las variables, la app sigue
  funcionando con datos de prueba simulados (con réplicas) para las
  variables que aún faltan, sin romper el flujo.
- **Reporte reproducible**: exporta un PDF con metodología, tablas de
  parámetros y gráficas, listo para anexar a un documento.

## Fuente de los datos reales

Los datos reales incluidos (`datos_reales/datos_reales_coffea_2023.xlsx`)
corresponden al Cuadro 2 de:

> Aguirre-Medina, J. F.; Aguirre-Cadena, J. F.; Escobar-España, J. C.;
> López-González, J. L. (2023). Crecimiento de *Coffea arabica* L. cv Catimor
> biofertilizado con diversos aislamientos de hongos endomicorrízicos en vivero.
> *Revista Fitotecnia Mexicana*, 46(3), 273-281.
> DOI: [10.35196/rfm.2023.3.273](https://doi.org/10.35196/rfm.2023.3.273)

Altura, número de hojas, área foliar y biomasa total en 4 momentos de
muestreo (28, 56, 84 y 112 días después del trasplante), 5 réplicas por
grupo y día. Como el paper reporta media y desviación estándar por
tratamiento (no mediciones planta por planta), las réplicas individuales
cargadas son sintéticas — generadas para reproducir exactamente esos
estadísticos reportados, no mediciones reales por planta. La variable
diámetro del tallo no está en el paper y sigue usando datos simulados.

## Stack

- [Streamlit](https://streamlit.io/) — interfaz y estado de la app
- [SciPy](https://scipy.org/) (`curve_fit`) — ajuste por mínimos cuadrados no lineales
- [Plotly](https://plotly.com/python/) — gráficas interactivas
- [pandas](https://pandas.pydata.org/) / [NumPy](https://numpy.org/) — manejo de datos
- [fpdf2](https://pyfpdf.github.io/fpdf2/) — generación del reporte PDF
- [openpyxl](https://openpyxl.readthedocs.io/) — lectura/escritura de Excel

## Cómo correrla localmente

```bash
git clone https://github.com/0scar07/proyecto-coffea-hma.git
cd proyecto-coffea-hma
pip install -r app/requirements.txt
streamlit run app/app.py
```

La app abre en `http://localhost:8501`. Por defecto arranca con datos
simulados; para probar con datos reales, ve a **Datos de prueba** y sube un
archivo en el formato de la plantilla descargable (o el Excel real incluido
en `datos_reales/`).

## Estructura del proyecto

```
proyecto-coffea-hma/
├── app/
│   ├── app.py                  # app de Streamlit (única fuente de la lógica y el UI)
│   ├── requirements.txt
│   └── .streamlit/
│       └── config.toml         # tema nativo de Streamlit (paleta "Cuaderno de campo")
├── datos_reales/
│   ├── datos_reales_coffea_2023.xlsx
│   └── validacion_cruzada_real.py   # script de validación cruzada sobre los datos reales
└── docs/
    └── screenshots/             # capturas usadas en este README
```

## Desplegar en Streamlit Cloud

1. En [share.streamlit.io](https://share.streamlit.io), **New app**.
2. Repositorio: `0scar07/proyecto-coffea-hma`, rama `master`.
3. **Main file path**: `app/app.py`.
4. Deploy — Streamlit Cloud toma automáticamente `app/requirements.txt` y
   `app/.streamlit/config.toml` porque están junto al archivo principal.

Si se actualiza el código y la app desplegada no refleja los cambios,
usa **"Reboot app"** desde el menú de la app en Streamlit Cloud para forzar
un proceso nuevo (limpia cualquier caché de `@st.cache_data` que haya
quedado de una versión anterior).

## Estado y limitaciones conocidas

- Datos reales completos para 4 variables (altura, número de hojas, área
  foliar y biomasa total) en 4 días de muestreo (28, 56, 84 y 112 ddt),
  según el Cuadro 2 del paper citado arriba. La variable diámetro del
  tallo sigue usando datos simulados, ya que el paper fuente no la reporta.
- Los parámetros de forma de Logístico y Gompertz (`K`, tasa) dependen de
  que los datos cubran también la fase de desaceleración del crecimiento,
  no solo la fase inicial acelerada. Con los 4 días disponibles (28-112
  ddt) la planta aún no muestra ese "codo" de desaceleración, y con solo 4
  puntos por grupo (1 grado de libertad para un modelo de 3 parámetros) el
  ajuste queda muy ajustado: en la práctica, **Gompertz falla en converger
  en uno de los dos grupos** (−M o +M, según la variable) para altura,
  área foliar y biomasa total, mientras que Exponencial y Logístico sí
  ajustan de forma estable en esas tres variables. En número de hojas los
  tres modelos convergen sin problema en ambos grupos. Esta es una
  limitación esperada de pocos puntos de muestreo, no un error de la
  aplicación.

## Licencia

Distribuido bajo licencia [MIT](LICENSE).
