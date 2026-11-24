---
name: validacion-rango-rondas
description: Rango de rondas para la validacion de la tesis (Cap. V) — en revision; corte de entrenamiento del modelo desplegado = 27/04/2026 (Apertura 12)
metadata:
  node_type: memory
  type: project
  originSessionId: def1fc74-f474-4e0f-b176-1459ea7ff236
  modified: 2026-09-29T05:27:01.102Z
---

El modelo desplegado (backend `back/main.py`, `CUTOFF = 2026-04-27`, 57 features, sin features del rival) se entreno con datos hasta el **27/04/2026 (cierre de Apertura 12)**, igual que dice el apartado 4.1.1 de la tesis. Todo partido posterior es "fuera de muestra".

Rango de validacion (Capitulo V): el 2026-09-29 el usuario propuso Apertura 15 a Clausura 5, pero se discutio que esa ventana no tiene justificacion metodologica (la hoja Cuotas tiene cuotas de BetMines del 02/05 al 23/09, Apertura 13 a Clausura 9). Recomendacion dada: validar con TODAS las rondas posteriores al corte. Decision final pendiente del usuario.

Datos de referencia (hoja Goles, target goles>=2): todas post-corte A13-C9 n=250, accuracy 61.6%, F1 0.38, base trivial "siempre Menos" 60.0%.

**Why:** el objetivo especifico 4 y los indicadores (1.6.2) piden metricas del modelo (Accuracy, Recall, F1), no ganancias de apuestas; el jurado puede verificar las rondas excluidas en el Excel o en el modulo de rendimiento de la web.

**How to apply:** no redactar justificaciones del rango que no sean ciertas; al calcular metricas filtrar por la columna `Jornada` al rango que el usuario confirme y reportar los tres modelos (xG, tiros, goles). Ver [[usuario-tesis]].
