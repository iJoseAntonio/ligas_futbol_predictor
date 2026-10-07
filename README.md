# xG Futbol — Predictor Multi-Modelo (ex "Liga 1 Perú")

Modelo de Machine Learning para predicción de rendimiento ofensivo en ligas de fútbol, actualmente aplicado a la Liga 1 del Perú, con arquitectura pensada para escalar a otras ligas.
Tesis — UNMSM, Facultad de Ingeniería de Sistemas e Informática.

**Sitio:** https://xgfutbol.online

## Estructura
```
├── back/                             ← Backend (AWS Lambda, contenedor publicado en ECR)
│   ├── main.py                        ← API FastAPI (+ handler Lambda vía Mangum)
│   ├── migrate_to_postgres.py         ← Script manual: sube bd_liga1.csv a RDS
│   ├── precompute_performance.py      ← Precalcula /model-performance offline (ver nota abajo)
│   ├── scrape_lineups.py              ← Scraper de alineaciones (Sofascore, vía Playwright)
│   ├── Dockerfile                     ← Imagen base public.ecr.aws/lambda/python:3.12
│   ├── requirements.txt
│   ├── .python-version
│   ├── data/                          ← Datos consumidos por el backend
│   │   ├── bd_liga1.csv                ← Dataset histórico (se actualiza por jornada)
│   │   └── partidos_liga1_2026.csv     ← Fixture de la temporada actual (⚠ duplicado
│   │                                      en frontend/, ver nota abajo)
│   └── modelos/
│       ├── shap_values.json            ← Valores SHAP (endpoint /shap-values)
│       ├── model_performance.json      ← Rendimiento por ronda precalculado (endpoint /model-performance)
│       ├── lineups_2026.json           ← Alineaciones precalculadas (endpoint /lineups)
│       ├── corregidos/                 ← Modelos vigentes (usados por main.py)
│       │   ├── Goles/                  ← .pkl + hiperparámetros + métricas (Goles ≥ 2)
│       │   ├── Goles_Esperadas/         ← .pkl + hiperparámetros + métricas (xG ≥ 1.5)
│       │   ├── Tiros_Puerta/            ← .pkl + hiperparámetros + métricas (Tiros ≥ 5)
│       │   └── metricas_modelos.json   ← Comparación combinada de los 3 targets
│       └── legacy/                     ← Modelos anteriores (Optuna optimizado contra
│                                          test, conservados como referencia histórica)
│
├── frontend/                         ← Sitio estático (S3 + CloudFront, dominio propio)
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── partidos_liga1_2026.csv        ← Fixture, leído client-side (duplicado de back/data/).
│   │                                     La tabla de posiciones (Acumulado/Apertura/Clausura,
│   │                                     Todos/Local/Visitante) se calcula en app.js.
│   ├── favicon-16.png, favicon-32.png ← Favicon (balón, sin escudo/texto — más legible a tamaño chico)
│   ├── apple-touch-icon.png           ← Ícono para "agregar a inicio" en iOS
│   └── logo-512.png, logo_pelota.png  ← Logo en alta resolución (uso general: header, tesis)
│
├── .github/workflows/
│   ├── deploy-aws.yml                 ← CI/CD backend: ECR + Lambda
│   └── deploy-frontend.yml            ← CI/CD frontend: S3 + CloudFront
│
└── notebooks/                        ← Notebooks de análisis y entrenamiento
    ├── Ingenieria_Caracteristicas_Modelos_Predictivos.ipynb
    ├── Modelo_Predictivo_Goles.ipynb
    ├── Modelo_Predictivo_Goles_Esperados.ipynb
    ├── Modelo_Predictivo_Tiros_Puerta.ipynb
    └── Seleccion_Umbrales_Target..ipynb
```

> **Nota metodológica:** los modelos en `back/modelos/legacy/` fueron optimizados con
> Optuna evaluando directamente contra el conjunto de test, lo cual infla sus métricas
> reportadas (data leakage). Los modelos en `back/modelos/corregidos/` usan validación
> cruzada temporal (`TimeSeriesSplit`) dentro del conjunto de entrenamiento, evitando
> ese problema — son los que usa la API en producción.

> **Por qué `model_performance.json` existe:** el cálculo de rendimiento por ronda
> (`/model-performance`) tarda ~30 segundos — más que el límite duro de 29-30s que
> impone API Gateway por invocación (no configurable). Por eso se precalcula **offline**
> con `precompute_performance.py` y el endpoint solo lee el JSON resultante, igual que
> ya se hacía con `shap_values.json`. Ver sección 6 de `README_AWS.md` para el detalle.

> **Alineaciones (`/lineups`):** Sofascore bloquea scraping directo con `requests`
> (403 vía Cloudflare), así que `scrape_lineups.py` usa un navegador real
> automatizado (**Playwright**) — navega una vez a sofascore.com y desde ahí hace
> `fetch()` a `/api/v1/event/{id}/lineups` por cada partido de 2026. El `match_id`
> se extrae de la columna `url_partido` (el número después de `#id:`). Sofascore no
> da coordenadas x/y por jugador; la posición en la cancha se calcula en el
> frontend a partir del string de formación (ej. `4-2-3-1`) y el orden de los
> titulares, que sí sigue ese mismo orden. `playwright` **no** está en
> `requirements.txt` — solo se usa en este script local, no corre dentro de Lambda
> (instálalo aparte: `pip install playwright && playwright install chromium`).

---

## Arquitectura en AWS

La infraestructura completa (componentes, red, dominio propio, CI/CD, bugs corregidos, pendientes) está documentada en **[`README_AWS.md`](./README_AWS.md)**.

Resumen rápido:
```
Usuario → CloudFront (dominio xgfutbol.online) → S3 (frontend)
Usuario → app.js → API Gateway → Lambda (dentro de una VPC) → RDS PostgreSQL (privada)
```

## Ciclo de actualización por jornada

1. Actualizar `back/data/bd_liga1.csv` y `back/data/partidos_liga1_2026.csv`.
2. Copiar `partidos_liga1_2026.csv` también a `frontend/` (el navegador lo lee directo).
3. Si hay reentrenamiento: correr `notebooks/Ingenieria_Caracteristicas_Modelos_Predictivos.ipynb` (cambiando `MODELO_ACTIVO` entre `'goles'`, `'tiros'`, `'xg'`).
4. Regenerar el rendimiento precalculado:
   ```bash
   cd back
   python precompute_performance.py
   ```
5. Regenerar las alineaciones de los partidos jugados (requiere `playwright` instalado aparte):
   ```bash
   cd back
   python scrape_lineups.py
   ```
6. `git add . && git commit -m "jornada X actualizada" && git push` → despliega Lambda y frontend automáticamente.
7. **Resincronizar RDS** (manual, vía túnel SSM porque la base es privada — ver `README_AWS.md` sección 5):
   ```bash
   # Terminal 1 (dejar corriendo)
   aws ssm start-session --target <INSTANCE_ID_BASTION> \
     --document-name AWS-StartPortForwardingSessionToRemoteHost \
     --parameters host="<endpoint-rds>",portNumber="5432",localPortNumber="5432"

   # Terminal 2
   cd back
   python migrate_to_postgres.py
   ```
8. Verificar: `GET /health` → `partidos_historicos` debe coincidir con las filas del CSV (sin encabezado).

> **⚠ `partidos_liga1_2026.csv` está duplicado** en `back/data/` (lo usa `main.py`
> en el servidor) y en `frontend/` (lo descarga el navegador directamente, sin pasar
> por la API). Cada vez que actualices este archivo, cópialo a **ambas** rutas —
> si solo actualizas una, el fixture quedará desincronizado entre la API y el sitio.
