**Estado:** Borrador para revisión del docente. No enviado ni publicado en ninguna revista de divulgación. Corresponde al producto "Elaborar un artículo divulgativo sobre los resultados del modelo matemático y la simulación computacional del efecto de los hongos micorrízicos arbusculares en plántulas de Coffea arabica" (indicador: manuscrito enviado o publicado en revista especializada en agronomía o revista de divulgación científica).

Este texto es distinto del manuscrito científico formal (`entregables/01_manuscrito/`): está escrito para un público de ingenieros agrónomos, técnicos de vivero y productores cafeteros, sin el aparato metodológico completo de un artículo indexado.

---

# ¿Puede una fórmula matemática ayudarnos a entender el efecto de la micorriza en el café?

## La idea en una frase

Le enseñamos a un programa a "dibujar" tres formas distintas de crecimiento de la planta de café, y luego usamos esas curvas para comparar plántulas con y sin hongos micorrízicos arbusculares (HMA) de forma más rigurosa que solo mirar una tabla de promedios.

## ¿Por qué modelar el crecimiento con curvas?

Cuando se mide la altura o el área foliar de una plántula varias veces en el tiempo, los números por sí solos no dicen mucho sobre la *forma* en que la planta está creciendo. Existen fórmulas matemáticas clásicas — llamadas modelos de crecimiento — que describen distintos patrones: crecimiento que no se detiene (modelo Exponencial) o crecimiento que se acelera y luego se estabiliza (modelos Logístico y Gompertz). Ajustar estas fórmulas a los datos reales permite comparar de forma más objetiva qué tanto un tratamiento (en este caso, la inoculación con HMA) cambia el patrón de crecimiento.

## Lo que se hizo

Se construyó una herramienta computacional (una aplicación web, Coffea IA) que toma datos de crecimiento de *Coffea arabica* — altura, área foliar, biomasa total y número de hojas, medidos a los 28, 56, 84 y 112 días después del trasplante — y ajusta automáticamente los tres modelos a cada variable, para el grupo control (sin inocular) y el grupo inoculado con HMA. Los datos base provienen del trabajo publicado por Aguirre-Medina et al. (2023) en la *Revista Fitotecnia Mexicana*.

**Una aclaración importante:** el artículo original de Aguirre-Medina et al. reporta promedios y variabilidad (no mediciones planta por planta), así que la herramienta genera réplicas individuales sintéticas que reproducen esos promedios, para poder hacer las comparaciones estadísticas. Esto significa que los resultados de significancia estadística que se presentan a continuación ilustran cómo funciona la metodología, y no deben leerse como una nueva evidencia experimental independiente del artículo original.

## Lo que se encontró

Con los cuatro momentos de muestreo disponibles, el ajuste de los modelos fue razonablemente bueno (valores de R² entre 0.876 y 0.997 en los modelos que lograron converger), aunque el modelo Gompertz no logró ajustarse en algunos casos — algo esperable cuando solo se cuenta con 4 puntos de datos por grupo para un modelo de 3 parámetros.

Al comparar los grupos con y sin micorriza:

- El **área foliar** mostró el efecto más consistente: la planta inoculada tuvo un área foliar mayor en los cuatro momentos de muestreo, con diferencias estadísticamente significativas en todos ellos.
- La **biomasa total** también mostró un efecto significativo en 3 de los 4 momentos de muestreo, con incrementos de hasta 72% a los 112 días.
- La **altura** y el **número de hojas** mostraron diferencias en su mayoría no significativas con estos datos.

## ¿Qué significa esto para el vivero?

Estos resultados son consistentes con la idea de que la inoculación con HMA favorece particularmente el desarrollo foliar y la acumulación de biomasa en las primeras etapas de la plántula, más que la elongación del tallo. Sin embargo, y esto es clave: estos hallazgos vienen de un reanálisis metodológico de datos ya publicados, con réplicas sintéticas — no de un experimento nuevo en campo. La validación con un conjunto de datos experimentales independiente todavía está pendiente.

## Para quien quiera ver los números

Los detalles completos (tablas de R²/RMSE/MAE, tabla completa de comparación por día, criterio usado para decidir cuándo un modelo es confiable) están en el manuscrito técnico (`entregables/01_manuscrito/manuscrito_borrador.md`) y en la guía técnica de la app (`entregables/06_guia_tecnica/guia_tecnica_usuario.md`).

## Referencia

Aguirre-Medina, J. F.; Aguirre-Cadena, J. F.; Escobar-España, J. C.; López-González, J. L. (2023). Crecimiento de *Coffea arabica* L. cv Catimor biofertilizado con diversos aislamientos de hongos endomicorrízicos en vivero. *Revista Fitotecnia Mexicana*, 46(3), 273-281. DOI: 10.35196/rfm.2023.3.273
