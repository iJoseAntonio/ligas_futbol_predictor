---
name: feedback-aws-console-vs-cli
description: "User wants to perform AWS console/infra changes himself via the web console, not have Claude run them via AWS CLI"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 847f50b8-de44-4105-ae7e-3b02fcca96e9
  modified: 2026-10-05T02:41:50.528Z
---

Cuando haya tareas por hacer en AWS (crear/editar recursos: Lambda, CloudFront, Route 53/Cloudflare DNS, ACM, RDS, IAM, etc.), dar instrucciones paso a paso para que el usuario las ejecute él mismo en la consola web de AWS — no ejecutarlas directamente vía AWS CLI/Bash en su nombre.

**Why:** El usuario está migrando su proyecto de tesis (liga1-xg-predictor-aws) a una cuenta nueva de AWS y quiere aprender la plataforma haciendo las cosas él mismo, no que Claude las automatice. Lo pidió explícitamente después de que Claude conectó un dominio custom (xgfutbol.online) a CloudFront + ACM corriendo los comandos de AWS CLI directamente en vez de guiarlo por consola.

**How to apply:** Para cualquier cambio de infraestructura AWS (no para debugging/lectura, que sigue siendo útil hacer vía CLI para diagnosticar), dar los pasos de consola (qué menú, qué botón, qué campo llenar) en vez de correr `aws ...` por él. Sigue siendo válido usar la CLI para verificar/diagnosticar estado (ej. `aws acm describe-certificate`, `aws lambda get-function`) ya que eso es lectura, no una acción de infraestructura que el usuario quiera aprender a hacer manualmente — la distinción es "acciones que modifican recursos" (consola, que las haga él) vs "verificación/diagnóstico de solo lectura" (CLI está bien que lo haga Claude).

Para cambios de código del proyecto (back/main.py, frontend/app.js, CSVs, etc.) esto NO aplica — esos los sigue editando Claude normalmente, la restricción es específica a acciones de infraestructura/consola AWS.
