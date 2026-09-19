**Estado:** Plantilla — material preparado, sin fecha ni sede definidas todavía. Corresponde al producto "Realizar un taller de capacitación sobre implementación de modelos matemáticos de crecimiento vegetal y simulación computacional en Python" (indicador: registro de asistencia, material didáctico y certificados de participación).

---

# Taller: modelado de crecimiento vegetal con Python y la app Coffea IA

## Datos generales

- **Fecha:** [por definir]
- **Lugar / modalidad:** [por definir]
- **Público objetivo:** [por definir — ver nota abajo]
- **Duración sugerida:** 3 horas (bloques de 45 min, con un descanso de 15 min a la mitad)
- **Facilitador(es):** [por definir]
- **Número de asistentes esperado:** [por definir]

> Nota sobre el público objetivo: el producto original menciona formación dirigida a estudiantes del Programa de Ingeniería de la Universidad Simón Bolívar; se deja como \[por definir\] porque no se especificó si el taller es exclusivamente para ese programa o se abre a otro público (técnicos de vivero, otros programas), lo cual cambia el nivel técnico del contenido.

## Objetivos

1. Explicar, sin prerrequisitos de programación avanzada, qué son los modelos Exponencial, Logístico y Gompertz y por qué se usan para describir crecimiento biológico.
2. Mostrar cómo la app Coffea IA ajusta esos modelos a datos reales y simulados, y cómo interpretar R², RMSE, MAE y el estado "No convergió".
3. Que cada asistente logre, de forma guiada, cargar datos, ajustar modelos y exportar un reporte PDF usando la app.

## Agenda por bloques

| Bloque | Duración | Contenido |
|---|---|---|
| 1. Contexto y motivación | 30 min | El problema del crecimiento de *Coffea arabica* con y sin micorrizas; por qué comparar modelos en vez de asumir uno solo |
| 2. Fundamentos de los tres modelos | 45 min | Fórmulas, parámetros, cuándo cada uno tiene sentido biológico (sección "Metodología" de la app) |
| — Descanso — | 15 min | |
| 3. Recorrido guiado de la app | 45 min | Navegación por las 11 secciones (ver guion paso a paso) |
| 4. Ejercicios prácticos | 40 min | Los 2 ejercicios de la sección siguiente, en parejas o individual |
| 5. Cierre y preguntas | 15 min | Dudas, encuesta de satisfacción |

## Guion paso a paso para usar la app

1. Abrir la app (local: `streamlit run app/app.py`, o la URL desplegada en Streamlit Cloud — ver README principal).
2. En **Datos de prueba**, mostrar las dos opciones: datos simulados (por defecto) o subir el Excel real (`datos_reales/datos_reales_coffea_2023.xlsx`).
3. Ir a **Ajustar modelos** y presionar el botón — explicar que esto corre una regresión no lineal (`curve_fit`), no un entrenamiento de red neuronal.
4. Ir a **Resultados** y mostrar las curvas por variable: círculos = réplicas observadas, líneas = modelos convergidos, y explicar por qué a veces no se dibuja la asíntota K (criterio de plausibilidad).
5. Abrir el expander de **Tasas de crecimiento (AGR/RGR)** dentro de Resultados.
6. Ir a **Gráficas de barras** y mostrar las marcas de significancia (ns/\*/\*\*/\*\*\*) de la prueba t de Welch.
7. Ir a **Resultados esperados** y mostrar la tabla de mejor modelo y la tabla de efecto +M vs −M.
8. Ir a **Estadística** y **Residuos** para el diagnóstico del ajuste.
9. Ir a **Exportar reporte** y generar el PDF completo.

## Ejercicios prácticos (con datos reales)

**Ejercicio 1 — Comparar modelos en una variable.**
Con el Excel real cargado, en **Ajustar modelos**, activar los tres modelos y ajustar. En **Resultados esperados → Resultado esperado 1**, identificar cuál modelo tiene mejor R² para "Área foliar" en el grupo +M y cuál en el grupo −M. Discutir: ¿son el mismo modelo en los dos grupos?

**Ejercicio 2 — Leer el efecto de la inoculación.**
En **Resultados esperados → Resultado esperado 2**, para la variable "Biomasa total (TDM)", identificar en qué días el incremento de +M sobre −M es estadísticamente significativo (p < 0.05) y en cuáles no. Discutir por qué un incremento porcentual grande no siempre es significativo (tamaño de muestra, varianza).

**Ejercicio 3 (opcional, si el tiempo alcanza) — Interpretar un "No convergió".**
En **Resultados**, para la variable "Altura", ubicar el modelo Gompertz en el grupo −M (no converge con estos datos) y leer la nota de la figura que explica por qué. Discutir qué significa "no convergió" frente a forzar un ajuste de todas formas.

## Esquema de diapositivas (guion, sin archivo de presentación)

1. Portada — título del taller, [fecha], [facilitador]
2. El problema: crecimiento de *Coffea arabica* con y sin HMA
3. Los datos: Aguirre-Medina et al. (2023) — qué miden y su limitación (réplicas sintéticas)
4. Tres modelos, tres formas de crecer (Exponencial vs. Logístico vs. Gompertz — diagrama conceptual)
5. Cómo se ajusta un modelo (idea de mínimos cuadrados, sin fórmulas pesadas)
6. R², RMSE, MAE — qué significan en términos simples
7. Cuándo la app dice "No convergió" (y por qué eso es honesto, no un error)
8. Demo en vivo: recorrido de la app (bloque 3 de la agenda)
9. Ejercicio 1 (enunciado)
10. Ejercicio 2 (enunciado)
11. Cierre: qué se puede hacer con estos modelos en el vivero
12. Preguntas y encuesta

## Lista de verificación de materiales

- [ ] Sala o enlace de videollamada confirmado
- [ ] Proyector / pantalla compartida probada
- [ ] Acceso a internet para todos los asistentes (o la app corriendo localmente en cada equipo)
- [ ] Excel real (`datos_reales/datos_reales_coffea_2023.xlsx`) accesible para todos
- [ ] Guion de diapositivas impreso o disponible para el facilitador
- [ ] Hojas/formulario de registro de asistencia
- [ ] Encuesta de satisfacción (ver `encuesta_satisfaccion.md`) lista para repartir
- [ ] Plantilla de certificado de participación

## Encuesta de satisfacción

Ver archivo separado: [`encuesta_satisfaccion.md`](encuesta_satisfaccion.md) (en blanco, lista para aplicar).
