**Estado:** Esquema / guion en Markdown solamente. No se generó el archivo de diapositivas (.pptx) — se hace solo si se pide explícitamente. Sin evento, fecha ni evaluador confirmados. Corresponde al producto "Socializar los resultados del proyecto mediante una ponencia en un evento académico institucional o nacional" (indicador: resumen aceptado, certificado de participación o constancia de presentación en el evento).

---

# Guion de ponencia: modelado de crecimiento de *Coffea arabica* con y sin micorrizas

**Evento:** [por definir] · **Fecha:** [por definir] · **Duración estimada:** 12-15 minutos + preguntas

## Diapositiva 1 — Portada

**Título:** Modelado y comparación de curvas de crecimiento en *Coffea arabica* inoculada con hongos micorrízicos arbusculares
**Viñetas:** Autores (Richard Montez, Diego Barrios, Santiago Uribe, Oscar Llanos) · Programa de Ingeniería, Universidad Simón Bolívar
**Notas del orador:** Presentarse brevemente y situar el trabajo como un proyecto de modelación aplicada, no como un experimento de campo nuevo.

## Diapositiva 2 — El problema

**Viñetas:**
- Los hongos micorrízicos arbusculares (HMA) son un biofertilizante de interés para el vivero de café.
- Pregunta: ¿cómo describir matemáticamente el crecimiento y comparar con rigor +M vs −M?
**Notas del orador:** Enmarcar el problema como "modelar + comparar", los dos pasos que resuelve la herramienta.

## Diapositiva 3 — Los datos

**Viñetas:**
- Fuente: Aguirre-Medina et al. (2023), *Revista Fitotecnia Mexicana* 46(3), 273-281.
- Altura, área foliar, biomasa total, número de hojas — 4 momentos de muestreo (28, 56, 84, 112 ddt), 5 réplicas por grupo/día.
- Réplicas sintéticas, generadas a partir de medias y CV% publicados (el paper no reporta planta por planta).
**Notas del orador:** Ser explícito con la limitación de las réplicas sintéticas — es un punto de honestidad metodológica clave.

## Diapositiva 4 — Los tres modelos

**Viñetas:**
- Exponencial: crecimiento sin límite superior.
- Logístico y Gompertz: crecimiento sigmoide, con asíntota K.
- Ajuste por mínimos cuadrados no lineales (`scipy.optimize.curve_fit`), no aprendizaje automático.
**Notas del orador:** Aclarar que "ajuste de modelo" no es lo mismo que "entrenar una red neuronal" — es una regresión clásica.

## Diapositiva 5 — Métodos

**Viñetas:**
- Métricas de bondad de ajuste: R², RMSE, MAE.
- Comparación de grupos: prueba t de Welch.
- Regla de honestidad: si no hay suficientes días o el modelo no converge, no se fuerza un ajuste.
**Notas del orador:** Este es el punto diferenciador de la herramienta frente a solo "correr un curve_fit" — la app se niega a mostrar un resultado no confiable.

## Diapositiva 6 — Resultados: bondad de ajuste

**Viñetas:**
- R² entre 0.876 y 0.997 en los modelos que convergen.
- Gompertz no converge en varios grupos (altura −M, área foliar +M, biomasa −M) — limitación esperada con solo 4 puntos por grupo.
**Notas del orador:** Mostrar `docs/figuras/barras_r2_modelos.png` o `curvas_area_foliar.png` en pantalla.

## Diapositiva 7 — Resultados: plausibilidad de K

**Viñetas:**
- Ejemplo: K estimada = 790 679.8 cm en altura (Logístico, −M) frente a un máximo observado de 15.0 cm.
- La app filtra estas asíntotas no plausibles en vez de mostrarlas.
**Notas del orador:** Este ejemplo numérico concreto ayuda a que la audiencia entienda por qué el criterio de plausibilidad es necesario, no un capricho de diseño.

## Diapositiva 8 — Resultados: efecto de la inoculación

**Viñetas:**
- Área foliar: incremento de +M significativo en los 4 días muestreados (hasta +200% a los 28 ddt, +97.1% a los 112 ddt).
- Biomasa total: significativo en 3 de 4 días.
- Altura y número de hojas: mayormente no significativos con estos datos.
**Notas del orador:** Recordar de nuevo la limitación de réplicas sintéticas antes de que la audiencia interprete estos p-values como un hallazgo experimental nuevo.

## Diapositiva 9 — Limitaciones

**Viñetas:**
- Ventana 28-112 ddt: captura la fase acelerada, no la de desaceleración.
- Solo validación interna de estabilidad de medias (`scripts/validacion_cruzada_real.py`), no validación externa.
- Los p-values ilustran la metodología, no son evidencia estadística independiente.
**Notas del orador:** No minimizar estas limitaciones — son parte del argumento de por qué el siguiente paso es la validación externa.

## Diapositiva 10 — Siguiente paso

**Viñetas:**
- Validación externa con un dataset independiente de *Coffea arabica*.
- Posible ampliación del muestreo para cubrir la fase de desaceleración.
**Notas del orador:** Cerrar con una invitación a colaborar o retroalimentar, según el tipo de evento.

## Diapositiva 11 — Cierre / preguntas

**Viñetas:**
- Repositorio del proyecto y app desplegada (ver README principal).
- Agradecimientos.
**Notas del orador:** Dejar tiempo para preguntas; tener a la mano la app abierta por si alguien pide ver una variable específica en vivo.
