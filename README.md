# Liga 1 Perú — XGBoost xG Predictor

Modelo de Machine Learning para predicción de rendimiento ofensivo en la Liga 1 del Perú.
Tesis — UNMSM, Facultad de Ingeniería de Sistemas e Informática.

## Estructura
```
├── back/                        ← Backend (AWS Lambda, contenedor publicado en ECR)
│   ├── main.py                   ← API FastAPI
│   ├── requirements.txt
│   ├── .python-version
│   ├── data/                     ← Datos consumidos por el backend
│   │   ├── bd_liga1.csv           ← Dataset histórico (se actualiza por jornada)
│   │   └── partidos_liga1_2026.csv← Fixture de la temporada actual (⚠ duplicado
│   │                                 en frontend/, ver nota abajo)
│   └── modelos/
│       ├── shap_values.json       ← Valores SHAP (endpoint /shap-values)
│       ├── corregidos/            ← Modelos vigentes (usados por main.py)
│       │   ├── Goles/             ← .pkl + hiperparámetros + métricas (Goles ≥ 2)
│       │   ├── Goles_Esperadas/    ← .pkl + hiperparámetros + métricas (xG ≥ 1.5)
│       │   ├── Tiros_Puerta/       ← .pkl + hiperparámetros + métricas (Tiros ≥ 5)
│       │   └── metricas_modelos.json ← Comparación combinada de los 3 targets
│       └── legacy/                ← Modelos anteriores (Optuna optimizado contra
│                                     test, conservados como referencia histórica)
│
├── frontend/                    ← Sitio estático (S3 + CloudFront)
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── partidos_liga1_2026.csv   ← Fixture, leído client-side (duplicado de back/data/).
│                                    La tabla de posiciones (Todos/Local/Visitante) se
│                                    calcula en app.js a partir de este archivo, ya no
│                                    depende de un CSV estático de posiciones.
│
└── notebooks/                   ← Notebooks de análisis y entrenamiento
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

> **Despliegue:** todo el proyecto corre en AWS, desplegado automáticamente por GitHub
> Actions en cada push a `main`.
> - **Backend:** `back/Dockerfile` (base `public.ecr.aws/lambda/python:3.12`) se
>   construye y publica en **Amazon ECR** (repo `ligas-predictores`, `us-east-2`), y se
>   despliega como función **AWS Lambda** (`futbol-ligas-predictor`) expuesta vía
>   **API Gateway**. Automatizado por `.github/workflows/deploy-aws.yml`.
> - **Frontend:** `frontend/` se sincroniza al bucket **S3** `s3-bucket-futbol-ligas-web`
>   (`us-east-1`) con invalidación de caché de **CloudFront**
>   (`d172q11bxscxd2.cloudfront.net`, el mismo dominio usado como `API_URL` en
>   `app.js`). Automatizado por `.github/workflows/deploy-frontend.yml`.
> - **Datos:** al arrancar, `main.py` carga el histórico en cascada — primero
>   **RDS PostgreSQL** (`DATABASE_URL`), si falla intenta **S3**
>   (`S3_BUCKET`/`S3_KEY`, vía `boto3`), y si tampoco hay acceso cae al **CSV local**
>   empaquetado en la imagen. `back/migrate_to_postgres.py` es el script para poblar
>   RDS desde el CSV histórico.

## Ciclo de actualización por jornada
Reentrenar los 3 modelos corriendo `notebooks/Ingenieria_Caracteristicas_Modelos_Predictivos.ipynb`
(cambiando `MODELO_ACTIVO` entre `'goles'`, `'tiros'`, `'xg'`), luego:
```bash
git add .
git commit -m "jornada X actualizada"
git push
```

> **⚠ `partidos_liga1_2026.csv` está duplicado** en `back/data/` (lo usa `main.py`
> en el servidor) y en `frontend/` (lo descarga el navegador directamente, sin pasar
> por la API). Cada vez que actualices este archivo, cópialo a **ambas** rutas —
> si solo actualizas una, el fixture quedará desincronizado entre la API y el sitio.

## AWS — configuración
- **Variables de entorno del backend (Lambda):**
  - `DATABASE_URL` — cadena de conexión a RDS PostgreSQL (`postgresql://user:pass@host:5432/dbname`)
  - `S3_BUCKET` — bucket con el CSV histórico de respaldo (default: `liga1-predictor-data`)
  - `S3_KEY` — key del objeto CSV dentro del bucket (default: `bd_liga1.csv`)
- **Credenciales:** la función Lambda usa su **rol de ejecución IAM** para acceder a S3 (no hay access keys en el código). El pipeline de CI/CD usa los secrets del repo `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `CLOUDFRONT_DISTRIBUTION_ID`.
- **Despliegue:** no es manual — basta con hacer push a `main`/`master` y los workflows de GitHub Actions construyen y publican backend y frontend automáticamente.
