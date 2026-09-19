**Estado:** Cubierto por la app — documento de trazabilidad, no un producto nuevo por generar. Corresponde a "Construir un modelo teórico de crecimiento de plántulas de *Coffea arabica* mediante regresión no lineal con los modelos exponencial, logístico y Gompertz" (indicador: tabla comparativa de métricas de bondad de ajuste — R², RMSE y MAE — con criterio de selección justificado).

---

# Trazabilidad: modelo teórico de crecimiento y métricas de ajuste

Este producto **ya está implementado y en funcionamiento** en la app Coffea IA.

## Dónde vive este resultado en la app

- **Modelos:** `modelo_exponencial`, `modelo_logistico`, `modelo_gompertz` en `app/app.py`, ajustados con `scipy.optimize.curve_fit` vía `ajustar_todos_los_modelos(datos)`.
- **Sección de la app:** `Resultados esperados → Resultado esperado 1 · Modelo que mejor describe cada variable`, con el criterio de selección explícito: mayor R² entre los modelos que convergieron (marcado con ⭐), respetando la regla de días mínimos por modelo (Exponencial ≥ 2 días; Logístico y Gompertz ≥ 3).
- **Comparación visual:** `docs/figuras/barras_r2_modelos.png` (cuadrícula 2×2 de R² por variable) y `docs/figuras/curvas_*.png` (curvas ajustadas con R² en la leyenda).
- **También visible en:** la tabla de R²/RMSE/MAE dentro de la sección **Resultados**, y en el reporte PDF exportable.

## Evidencia de que funciona con datos reales (recalculado el 2026-09-19)

Mejor modelo por variable y grupo (criterio: mayor R² entre los modelos convergidos):

| Variable | Grupo −M | Grupo +M |
|---|---|---|
| Altura | Exponencial (R²=0.9082) | Logístico (R²=0.8769) |
| Área foliar | Gompertz (R²=0.9720) | Exponencial (R²=0.9933) |
| Biomasa total | Logístico (R²=0.9968) | Logístico (R²=0.9940) |
| Número de hojas | Logístico (R²=0.9411) | Logístico (R²=0.9623) |

(Tabla completa de R²/RMSE/MAE para los tres modelos en `entregables/01_manuscrito/manuscrito_borrador.md`, sección 3.1; ejemplos de asíntotas K descartadas por implausibilidad en la sección 3.2 del mismo documento.)

## Nota metodológica (aplica a esta tabla)

Calculado sobre réplicas sintéticas generadas a partir de las medias y CV% publicados por Aguirre-Medina et al. (2023, *Revista Fitotecnia Mexicana* 46(3), 273-281, DOI 10.35196/rfm.2023.3.273) — ver nota completa en `entregables/09_metodologia_estadistica/`.

## Qué falta, si algo

Nada a nivel de funcionalidad — el ajuste y la comparación de métricas están validados y en producción. Pendiente: validación **externa** con un dataset distinto al de Aguirre-Medina et al. (2023); actualmente solo existe validación interna de estabilidad de medias (`scripts/validacion_cruzada_real.py`, hold-out 80/20), que no mide generalización del modelo de crecimiento en sí.
