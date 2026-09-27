# Validación externa parcial — resumen para la exposición

**Validación externa parcial de la metodología** (no de mis propios resultados) con tres
estudios publicados de café con micorrizas: León-Burgos et al. (2022), Siqueira et al.
(1998) y Vallejos-Torres et al. (2021).

- Mi modelo Logístico, aplicado a datos independientes de León-Burgos et al. (2022),
  reproduce sus parámetros publicados (K, punto de inflexión) con diferencias de solo
  1-5%, usando el mismo código de `app.py`, sin modificarlo.
- Mi criterio de plausibilidad de K se comporta igual en ambos datasets: cuando la
  ventana de muestreo no alcanza a mostrar la desaceleración, la K estimada se dispara y
  el criterio correctamente evita dibujarla — pasa en mis datos y en los de León-Burgos.
- La dirección del efecto de la inoculación (+M mayor que el control) es consistente en
  los tres estudios externos y en mi propia app, aunque la magnitud y significancia no
  son comparables entre estudios (cultivar, sustrato, edad y unidades distintos; mis
  réplicas son sintéticas).
- La sensibilidad estadística de Vallejos-Torres depende por completo de cómo se
  interprete un valor ambiguo del paper (desviación estándar vs. error estándar): no hay
  una conclusión única, y así se reporta.

| Fuente | Qué se validó | Resultado |
|---|---|---|
| León-Burgos et al. (2022) | Curvas (Logístico) | K y Ti a 1-5% de lo publicado |
| León-Burgos et al. (2022) | Criterio de plausibilidad de K | Mismo patrón que mis datos |
| Siqueira et al. (1998) | Efecto en el tiempo | Reproduce 50%/18%/10% citados |
| Vallejos-Torres et al. (2021) | Dirección del efecto +M | Misma dirección que mi app |

Estado: **validación externa parcial** — valida la metodología (modelos, criterios de
convergencia y de plausibilidad de K), no sustituye la validación externa con un
experimento propio nuevo, que sigue pendiente.
