**Estado:** Cubierto por la app — documento de trazabilidad, no un producto nuevo por generar. Corresponde a "Desarrollar una metodología validada para la caracterización estadística comparativa de variables de crecimiento de plántulas de *Coffea arabica* bajo inoculación con HMA" (indicador: tablas con media, desviación estándar, valor p ≤ 0.05 y cambio porcentual entre tratamientos inoculado y control).

---

# Trazabilidad: metodología estadística comparativa

Este producto **ya está implementado y en funcionamiento** en la app Coffea IA — no requiere un documento nuevo con tablas recalculadas a mano, lo cual además duplicaría (y arriesgaría desalinear) la fuente real de la cifra.

## Dónde vive este resultado en la app

- **Sección de la app:** `Resultados esperados → Resultado esperado 2 · Efecto de la inoculación micorrízica (+M vs −M)` (bloque `elif seccion == "Resultados esperados":` en `app/app.py`).
- **Función que lo calcula:** `calcular_efecto_micorriza(datos, variable)`, usando `prueba_t_independiente` (prueba t de Welch, `scipy.stats.ttest_ind` con `equal_var=False`).
- **Qué produce, por variable y día:** media del grupo −M, media del grupo +M, incremento porcentual de +M sobre −M, estadístico t, valor p, y si es significativo (p < 0.05).
- **También visible en:** la sección **Estadística** de la app (intervalos de confianza por parámetro) y en el reporte PDF exportable (`docs/reportes/reporte_ejemplo_datos_reales.pdf`).

## Evidencia de que funciona con datos reales (recalculado el 2026-09-19)

| Variable | Día (ddt) | Incremento +M (%) | p | Significativo |
|---|---|---|---|---|
| Área foliar (cm²) | 28 | +200.0 | <0.0001 | Sí |
| Área foliar (cm²) | 112 | +97.1 | <0.0001 | Sí |
| Biomasa total (g) | 84 | +66.1 | <0.0001 | Sí |
| Altura (cm) | 84 | +25.2 | 0.0001 | Sí |

(Tabla completa de los 4 días × 4 variables en `entregables/01_manuscrito/manuscrito_borrador.md`, sección 3.3.)

## Nota metodológica (aplica a esta tabla)

Las réplicas individuales del dataset real son sintéticas, generadas a partir de las medias y CV% publicados por Aguirre-Medina et al. (2023, *Revista Fitotecnia Mexicana* 46(3), 273-281, DOI 10.35196/rfm.2023.3.273). Por lo tanto, estos valores p ilustran la metodología estadística implementada, no son evidencia estadística independiente nueva sobre el efecto de la micorrización. La validación externa con datos de otro estudio está pendiente.

## Qué falta, si algo

Nada a nivel de funcionalidad — la metodología está validada y en producción. Lo único pendiente es la validación **externa** (con un dataset distinto), documentada como trabajo futuro en el `README.md` principal y en `entregables/01_manuscrito/`.
