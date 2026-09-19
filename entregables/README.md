# Entregables de gestión y difusión — Coffea IA

Este directorio contiene **borradores, plantillas y material preparado** para los productos de gestión y difusión del proyecto (los que no se calculan directamente con la app). Ningún archivo aquí es un documento final: cada uno lleva su propio encabezado de estado. No se inventaron autores, instituciones, fechas de eventos, número de asistentes, resultados de evaluación, revista destino, ni envíos/aceptaciones — todo dato desconocido está marcado como `[por definir]` o `[placeholder]` dentro de cada archivo.

La lista de productos y sus indicadores/beneficiarios provienen de la tabla de Resultados/Productos del proyecto (imagen aportada por el usuario, 2026-09-19); no se agregó ni se quitó ningún producto de esa lista, salvo separar el artículo divulgativo del manuscrito científico por ser dos productos distintos en la tabla original.

## Tabla de estado

| # | Producto (tal como aparece en la tabla de Resultados/Productos) | Carpeta | Estado | Qué falta |
|---|---|---|---|---|
| 1 | Elaborar un artículo científico... (manuscrito para revista Scopus/WoS) | [`01_manuscrito/`](01_manuscrito/) | Borrador para revisión del docente | Revisión del docente; definir orden de autoría; no se ha elegido revista destino |
| 2 | Desarrollar una metodología validada para la caracterización estadística comparativa | [`09_metodologia_estadistica/`](09_metodologia_estadistica/) | Cubierto por la app (documento de trazabilidad) | Nada a nivel funcional; pendiente la validación externa del proyecto en general |
| 3 | Construir un modelo teórico de crecimiento (tabla comparativa R²/RMSE/MAE) | [`10_metricas_ajuste_modelos/`](10_metricas_ajuste_modelos/) | Cubierto por la app (documento de trazabilidad) | Nada a nivel funcional; pendiente la validación externa del proyecto en general |
| 4 | Implementar un algoritmo de ajuste y validación predictiva (código fuente documentado) | [`02_codigo_documentado/`](02_codigo_documentado/) | En preparación | Decidir si se aplican los docstrings propuestos al final del documento (no aplicados) |
| 5 | Formar a cuatro estudiantes de pregrado en investigación científica | [`04_informes_estudiantes/`](04_informes_estudiantes/) | Plantilla | Datos reales de cada estudiante; fecha de sustentación si aplica |
| 6 | Realizar un taller de capacitación sobre modelos matemáticos y Python | [`03_taller_capacitacion/`](03_taller_capacitacion/) | Plantilla | Fecha, lugar, público objetivo y facilitador |
| 7 | Fortalecer la cooperación científica mediante una publicación colaborativa | [`05_publicacion_colaborativa/`](05_publicacion_colaborativa/) | Esquema / en preparación | Roles y orden de autoría; fechas reales del cronograma; revista destino |
| 8 | Elaborar un artículo divulgativo sobre los resultados | [`08_articulo_divulgativo/`](08_articulo_divulgativo/) | Borrador para revisión del docente | Revisión del docente; revista de divulgación destino |
| 9 | Desarrollar una guía práctica de uso e interpretación del modelo | [`06_guia_tecnica/`](06_guia_tecnica/) | Borrador para revisión del docente | Revisión del docente |
| 10 | Socializar los resultados mediante una ponencia en un evento académico | [`07_ponencia/`](07_ponencia/) | Esquema (solo guion en Markdown) | Evento y fecha; generar el archivo de diapositivas si se solicita |

## Notas transversales a todos los documentos

- Todas las cifras de resultados (R², RMSE, MAE, medias, incrementos %, valores t y p) se recalcularon directamente sobre `datos_reales/datos_reales_coffea_2023.xlsx` con las funciones reales de `app/app.py` el 2026-09-19 — no se copiaron de memoria ni se estimaron.
- Las réplicas individuales del dataset real son sintéticas (generadas a partir de las medias y CV% publicados por Aguirre-Medina et al., 2023, *Revista Fitotecnia Mexicana* 46(3), 273-281, DOI 10.35196/rfm.2023.3.273); por eso los valores p ilustran la metodología estadística, no son evidencia estadística independiente nueva. Esta nota se repite en cada documento que presenta cifras.
- La validación externa (con datos de otro estudio) está pendiente en todo el proyecto — no se afirma en ningún documento que ya exista.
- Se usa siempre "ajuste de modelos" o "regresión no lineal"; ninguno de estos documentos usa "entrenar/entrenamiento".
- No se modificó nada dentro de `app/`, `datos_reales/` ni `scripts/` para producir estos entregables.
