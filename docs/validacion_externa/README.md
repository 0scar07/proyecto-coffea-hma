# Validación externa parcial — Coffea IA

Esta carpeta contiene una **validación externa PARCIAL** de la metodología de Coffea IA
(los 3 modelos de crecimiento, el criterio de convergencia y el criterio de plausibilidad
de la asíntota K) contra tres estudios ya publicados. **No** es una validación de mis
propios resultados con un experimento nuevo — eso sigue pendiente.

## Qué leer primero

1. **`informe.md`** (o `informe.pdf`) — el documento completo: qué se hizo con cada
   fuente, comparación con lo publicado, y las listas "Qué SÍ se puede afirmar" / "Qué NO
   se puede afirmar".
2. **`resumen_exposicion.md`** (o `resumen_exposicion.pdf`) — media página con lo esencial,
   pensada para llevar a una exposición.

## Qué hay en cada carpeta

- **`datos/`** — las 4 tablas de resultados en CSV (`resultados_curvas.csv`,
  `comparacion_publicado.csv`, `efecto.csv`, `sensibilidad_vallejos_torres.csv`), y en
  `datos/excel/` las mismas 4 tablas en `.xlsx` con formato para lectura humana (misma
  información, solo presentación).
- **`figuras/`** — las 5 figuras PNG citadas en el informe.
- **`fuente_pdf/`** — el script y los estilos que generan `informe.pdf` y
  `resumen_exposicion.pdf` a partir de los `.md`.

## Cómo se generó

El análisis lo hizo `scripts/validacion_externa.py`: extraía con `ast` el código vigente
de `app/app.py` (sin importarlo), lo corría contra los tres datasets externos (León-Burgos
2022, Siqueira 1998 y Vallejos-Torres 2021) y escribía los CSV, las figuras y los dos `.md`
de esta carpeta. El script y esos tres Excel ya no están en el repositorio (se retiraron
después de generar el informe); siguen disponibles en el historial de git si hiciera falta
volver a correrlo. `fuente_pdf/` solo se encarga de convertir esos `.md` ya
generados a PDF con el estilo visual de la app — no cambia ningún número.
