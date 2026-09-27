# Liga 1 Perú — XGBoost xG Predictor

Modelo de Machine Learning para predicción de rendimiento ofensivo en la Liga 1 del Perú.
Tesis — UNMSM, Facultad de Ingeniería de Sistemas e Informática.

## Estructura
```
├── back/                        ← Backend (AWS Lambda, contenedor publicado en ECR)
│   ├── main.py                   ← API FastAPI (+ handler Lambda vía Mangum)
│   ├── migrate_to_postgres.py    ← Script manual: sube bd_liga1.csv a RDS
│   ├── Dockerfile                ← Imagen base public.ecr.aws/lambda/python:3.12
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
│                                    calcula en app.js a partir de este archivo.
│
├── .github/workflows/
│   ├── deploy-aws.yml            ← CI/CD backend: ECR + Lambda
│   └── deploy-frontend.yml       ← CI/CD frontend: S3 + CloudFront
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

---

# Arquitectura en AWS

## Diagrama de flujo

```
Usuario (navegador)
   │
   ├─(1) Sitio estático ──► CloudFront (sitio) ──► S3 s3-bucket-futbol-ligas-web
   │                         d2a1x1ayseqtnd.cloudfront.net
   │
   └─(2) app.js hace fetch(API_URL)
            │
            ▼
        CloudFront (API)  d172q11bxscxd2.cloudfront.net
            │
            ▼
        API Gateway (HTTP API)  futbol-ligas-api  [oplygu25f5]
            │
            ▼
        Lambda  futbol-ligas-predictor   (imagen desde ECR: ligas-predictores)
            │   FastAPI + Mangum, modelos XGBoost (.pkl) empaquetados en la imagen
            │
            └─► Datos históricos (cascada al arrancar):
                  1. RDS PostgreSQL  db-liga1-peru      (tabla partidos_liga1)
                  2. S3              liga1-predictor-data / bd_liga1.csv
                  3. CSV local       back/data/bd_liga1.csv (dentro de la imagen)
```

## Inventario de componentes

| Componente | Nombre / Identificador | Región | Rol en el sistema |
|---|---|---|---|
| **S3 (frontend)** | `s3-bucket-futbol-ligas-web` | `us-east-1` | Aloja `index.html`, `app.js`, `styles.css` y el CSV del fixture |
| **CloudFront (sitio)** | dominio `d2a1x1ayseqtnd.cloudfront.net` · ID de distribución: secret `CLOUDFRONT_DISTRIBUTION_ID` | global | CDN que sirve el frontend desde S3 |
| **CloudFront (API)** | dominio `d172q11bxscxd2.cloudfront.net` (es el `API_URL` en `frontend/app.js:12`) | global | Capa delante de API Gateway; punto de entrada de la API para el navegador |
| **API Gateway** | `futbol-ligas-api` · ID `oplygu25f5` · tipo **HTTP API** · **Regional** · creada 2026-08-09 | `us-east-2` | Recibe la petición HTTP y la entrega a Lambda |
| **Lambda** | `futbol-ligas-predictor` (empaquetada como imagen de contenedor) | `us-east-2` | Ejecuta la API FastAPI vía `Mangum` (`handler = Mangum(app)`) |
| **ECR** | repositorio `ligas-predictores` · tag `latest` | `us-east-2` | Registro de la imagen Docker de Lambda |
| **RDS PostgreSQL** | instancia `db-liga1-peru` · endpoint `db-liga1-peru.cp4scs6caw84.us-east-2.rds.amazonaws.com:5432` · BD `postgres` · usuario `postgres` | `us-east-2` (AZ `us-east-2b`) | Fuente principal del histórico (tabla `partidos_liga1`) |
| **S3 (datos)** | bucket `liga1-predictor-data` (default en `main.py`, ⚠ por confirmar) · key `bd_liga1.csv` | — | Fallback si RDS no responde |
| **IAM** | rol de ejecución de la Lambda (⚠ por documentar nombre/políticas) · usuario/keys de CI/CD en GitHub Secrets | global | Permisos de Lambda hacia S3 y credenciales del pipeline |
| **GitHub Actions** | `deploy-aws.yml`, `deploy-frontend.yml` | — | CI/CD automático en cada push a `main`/`master` |

## Red (VPC)

| Elemento | Valor |
|---|---|
| VPC | `vpc-088f3180e62c2a261` — `172.31.0.0/16` (VPC por defecto) |
| Subnet `us-east-2a` | `subnet-0d8ac6fbc9d8e02ca` — `172.31.0.0/20` (pública) |
| Subnet `us-east-2b` | `subnet-0ed6759b12a1a11b3` — `172.31.16.0/20` (pública, aquí vive RDS) |
| Internet Gateway | `igw-0b6f8aa98c15c2f5c` |
| Route table (Main) | `rtb-0b2affc13650acd82` — `172.31.0.0/16 → local`, `0.0.0.0/0 → igw` |
| Network ACL | `acl-0c77522c2e8c1d209` |
| DB Subnet Group | `default-vpc-088f3180e62c2a261` (subnets `us-east-2a` y `us-east-2b`) |
| ENI de RDS | `eni-01c0567707291347a` — IP privada `172.31.20.110` (IP pública vía Elastic IP) |
| Security Group | `sg-0d2381bc1a24c7a2b` (`default`) |

**Reglas inbound del Security Group:**

| Tipo | Protocolo/Puerto | Origen | Comentario |
|---|---|---|---|
| All traffic | All | el propio SG | Regla por defecto del SG `default` |
| PostgreSQL | TCP 5432 | `0.0.0.0/0` | ⚠ RDS expuesto a internet (ver "Pendientes") |

**Notas de red:**
- RDS es **Single-AZ** y tiene `Publicly accessible = Yes`.
- **Lambda NO está dentro del VPC** (no tiene ENI propio): llega a RDS por su IP pública, y por eso el puerto 5432 está abierto a `0.0.0.0/0`.
- Las subnets son **públicas** (route table con salida directa al Internet Gateway).
- El subnet group de RDS exige ≥ 2 AZs; por eso se mantienen las subnets de `us-east-2a` y `us-east-2b`.

## Variables de entorno de la Lambda

| Variable | Descripción | Default en `main.py` |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión a RDS: `postgresql://user:pass@host:5432/dbname`. Si no existe, se salta a S3 | — |
| `S3_BUCKET` | Bucket con el CSV histórico de respaldo | `liga1-predictor-data` |
| `S3_KEY` | Key del CSV dentro del bucket | `bd_liga1.csv` |

Credenciales de AWS: la Lambda usa su **rol de ejecución IAM** (no hay access keys en el código).

## Secrets de GitHub Actions

| Secret | Uso |
|---|---|
| `AWS_ACCESS_KEY_ID` | Autenticación del pipeline contra AWS |
| `AWS_SECRET_ACCESS_KEY` | Autenticación del pipeline contra AWS |
| `CLOUDFRONT_DISTRIBUTION_ID` | Distribución a invalidar tras subir el frontend |

## CI/CD

| Workflow | Disparador | Qué hace |
|---|---|---|
| `deploy-aws.yml` | push a `main`/`master` (o manual) | `docker build` de `back/` → push a ECR `ligas-predictores:latest` → `aws lambda update-function-code` sobre `futbol-ligas-predictor` (`us-east-2`) |
| `deploy-frontend.yml` | push que toque `frontend/**` (o manual) | `aws s3 sync frontend/ s3://s3-bucket-futbol-ligas-web --delete` (`us-east-1`) → `aws cloudfront create-invalidation --paths "/*"` |

> `deploy-aws.yml` se ejecuta en **cada** push a `main` (no filtra por `back/**`), mientras que `deploy-frontend.yml` solo se ejecuta si cambia `frontend/`.

## Endpoints de la API

Base URL: `https://d172q11bxscxd2.cloudfront.net`

| Endpoint | Rate limit | Descripción |
|---|---|---|
| `GET /health` | 60/min | Estado de modelos y datos (`partidos_historicos`, etc.) |
| `GET /predict-match?home=&away=&fecha=DD/MM/YYYY` | 30/min | Predicción de los 3 modelos para ambos equipos |
| `GET /match-result?home=&away=&fecha=DD/MM/YYYY` | 60/min | Resultado real del partido (xG, tiros a puerta, goles) |
| `GET /team-rankings` | 60/min | Ranking de equipos de la temporada 2026 |
| `GET /model-metrics`, `GET /shap-values`, `GET /model-performance`, `GET /modelo-info` | 60/min | Métricas, explicabilidad y rendimiento histórico de los modelos |

CORS abierto (`allow_origins=["*"]`). Límite por IP aplicado dentro de FastAPI con `slowapi`.

## Actualización de datos por jornada

La API **no lee el CSV del repo directamente**: primero consulta RDS. Por eso, actualizar el CSV y hacer `git push` **no basta**.

1. Actualizar `back/data/bd_liga1.csv` y `back/data/partidos_liga1_2026.csv`.
2. Copiar `partidos_liga1_2026.csv` también a `frontend/` (el navegador lo lee directo).
3. Si hay reentrenamiento: correr `notebooks/Ingenieria_Caracteristicas_Modelos_Predictivos.ipynb` (cambiando `MODELO_ACTIVO` entre `'goles'`, `'tiros'`, `'xg'`).
4. `git add . && git commit -m "jornada X actualizada" && git push` → despliega Lambda y frontend.
5. **Resincronizar RDS** (paso manual):
   ```bash
   cd back
   python migrate_to_postgres.py
   ```
   Pide el endpoint de RDS y la contraseña maestra por consola. Hace `to_sql(..., if_exists="replace")`: **borra y recrea** la tabla `partidos_liga1` con el contenido completo del CSV (`goles_local` y `goles_visitante` se crean como `INTEGER`; el resto lo infiere pandas). Requiere `psycopg2-binary` instalado en el entorno.
6. Verificar: `GET /health` → `partidos_historicos` debe coincidir con el número de filas del CSV (sin contar el encabezado).

> **⚠ `partidos_liga1_2026.csv` está duplicado** en `back/data/` (lo usa `main.py`
> en el servidor) y en `frontend/` (lo descarga el navegador directamente, sin pasar
> por la API). Cada vez que actualices este archivo, cópialo a **ambas** rutas —
> si solo actualizas una, el fixture quedará desincronizado entre la API y el sitio.

## Pendientes / por mejorar

- [ ] Documentar el rol IAM de la Lambda (nombre y políticas) y el usuario IAM del CI/CD (aplicar mínimo privilegio).
- [ ] Confirmar el bucket S3 de fallback (`S3_BUCKET`) y si `bd_liga1.csv` se mantiene actualizado ahí.
- [ ] Documentar rutas, integración y stage (`$default`) de `futbol-ligas-api` en API Gateway, y los orígenes/comportamientos de las dos distribuciones de CloudFront.
- [ ] **Seguridad:** restringir el puerto 5432 del Security Group (hoy `0.0.0.0/0`) y rotar la contraseña maestra de RDS; evaluar mover Lambda al VPC + VPC Endpoint de S3 para dejar RDS privado (evita el costo de un NAT Gateway).
- [ ] Automatizar la sincronización a RDS/S3 (hoy `migrate_to_postgres.py` es manual).
- [ ] Infraestructura como código (Terraform/CDK): hoy todo se creó por consola.
- [ ] Agregar `lightgbm` a `requirements.txt` si se van a servir esos modelos.
- [ ] Filtrar `deploy-aws.yml` para que solo corra cuando cambie `back/**`.
