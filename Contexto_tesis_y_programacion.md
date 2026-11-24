# Contexto para continuar la sustentación
Tesis de Jose Antonio Villanueva Ines, Ingeniería de Sistemas, UNMSM. Se desarrolla un modelo de aprendizaje automático para predecir, antes del partido y por separado para cada equipo de la Liga 1 del Perú, si alcanzará 1,5 goles esperados, cinco tiros a puerta y dos goles anotados. Basarse en la última tesis, el artículo y la presentación que adjunte el autor.
## Datos y entrenamiento
1 078 partidos del periodo de desarrollo 2023–abril de 2026, 2 156 registros equipo-partido y 2 123 utilizables tras calcular promedios y ratios. La tesis menciona valores faltantes por desplazamiento temporal y divisiones por cero, sin atribuir cuántos de los 33 corresponden a cada causa. 28 variables × dos ventanas (3 y 5 partidos previos) más localía = 57 predictores. División cronológica de 1 701 registros de entrenamiento y 422 de prueba. Optuna y cinco particiones temporales. SMOTE solo en el bloque de entrenamiento de cada partición. Se compararon XGBoost, LightGBM, Random Forest y regresión logística. XGBoost tuvo 64,69 % de exactitud en xG en prueba interna. La regresión logística lideró en AUC-ROC y F1 en los tres indicadores. Se implementaron tres clasificadores XGBoost para una implementación e interpretación común.
## Hallazgos y alcance
En 144 partidos posteriores (16 fechas, 288 registros por indicador), exactitud 62,5 % para xG, 57,3 % para tiros a puerta y 61,1 % para goles. Ventajas sobre la clase mayoritaria de 5,2, 4,5 y 0,3 puntos porcentuales. AUC-ROC 0,628, 0,607 y 0,540. Sensibilidad xG 39,0 %. IC del 95 % para exactitud y AUC-ROC; Wilson y 2 000 réplicas bootstrap respectivamente. Sin confirmar la unidad de remuestreo. Dos registros relacionados por partido. Brier 0,247, 0,259 y 0,259. Según SHAP la localía lideró los tres clasificadores. Segundas variables: atajadas en tres partidos para xG, despejes en cinco para tiros a puerta y goles en cinco para goles anotados.
## Artefacto y presentación
La evaluación predictiva se hizo con partidos posteriores. La plataforma xG Fútbol fue valorada por cuatro expertos (4,50/5) y siete aficionados (4,37/5). No se utilizó V de Aiken. La versión de sustentación revisada del escritorio tenía 31 diapositivas en granate y crema. El autor considera redundante la de cumplimiento de objetivos específicos antes de conclusiones. Se recomendó cerrar con una conclusión por cada uno de los cuatro objetivos y una frase sobre el artefacto. Diferenciar sugerencias de cambios efectivamente aplicados. La recomendación más reciente discutida fue evaluar la fuerza del rival con posición en la tabla, puntos o Elo, como trabajo futuro.
## Preferencias
Español claro para defender ante jurado. Prosa corrida sin dos puntos en los párrafos de tesis. Evitar exagerar el aporte o atribuir causalidad a SHAP. Artículo y tesis deben coincidir en resultados. Dar más protagonismo al modelo que a la página o al juicio de expertos. Respetar la tipografía y estilo del archivo vigente. Cuando el autor pide una explicación, usar ejemplos concretos del estudio.

## Cómo funciona la aplicación desde una consulta hasta el resultado
La web está en frontend/index.html, frontend/app.js y frontend/styles.css. Al abrir un encuentro, app.js construye la consulta y obtiene el pronóstico de /predict-match. La consulta de /match-result recupera los resultados observados. El navegador usa cachedApiJson para reutilizar respuestas. La arquitectura descrita en la tesis usa S3 y CloudFront para el sitio, API Gateway y Lambda para la API FastAPI, y PostgreSQL en RDS para el histórico. Mangum adapta FastAPI a Lambda. Los despliegues de frontend y backend tienen workflows separados en .github/workflows.

1. Al cargar recursos, back/main.py abre con joblib tres archivos XGBoost de back/modelos/corregidos. El servidor intenta leer el histórico de la tabla partidos_liga1 de PostgreSQL cuando existe configuración para ello. Como alternativas intenta un CSV desde S3 y después el CSV local. La carpeta legacy contiene versiones anteriores.
2. /predict-match recibe home, away y opcionalmente fecha en DD/MM/YYYY. Con una fecha válida, compute_team_stats conserva únicamente filas cuya fecha es estrictamente anterior al encuentro. Si la fecha se omite o no se puede interpretar, el código usa todo el histórico cargado. Esta diferencia importa al reproducir un partido pasado.
3. _build_team_df identifica en cada partido si el equipo jugó como local o visitante y selecciona las columnas de ese lado. Ordena las actuaciones por fecha y calcula precisión de pases, precisión de tiros, conversión de xG y proporción de tiros desde dentro del área. En este código de inferencia los cocientes con denominador cero se rellenan con cero. El texto de la tesis documenta el tratamiento de faltantes durante la preparación del conjunto de desarrollo.
4. Para cada variable toma la media de hasta los últimos tres y cinco encuentros disponibles. Si solo hay dos partidos previos, ambas ventanas utilizan esos dos. Si falta todo el historial de uno de los equipos, la ruta devuelve 404. Esto describe la API; para justificar la eliminación de las 33 filas durante el desarrollo se debe usar el procedimiento de preparación de la tesis.
5. Se añade Local=1 para el anfitrión y Local=0 para el visitante. run_model ordena las entradas según FEATURES_FINAL. El modelo devuelve la probabilidad de la clase positiva con predict_proba y la clase con predict. La probabilidad se devuelve como porcentaje con un decimal. En un partido se generan seis pronósticos, tres por equipo. En cada pronóstico se usa el historial del propio equipo; los nombres sirven para recuperar los registros. Una medida explícita de fuerza del rival como Elo es una propuesta futura.
6. SMOTE y Optuna corresponden al entrenamiento previo. Cuando se consulta la plataforma, esta ejecuta los clasificadores ya ajustados. La validación temporal descrita en la tesis y una petición de inferencia en la web son operaciones distintas.

## Otros puntos de entrada para preguntas sobre el código
- back/main.py incluye /match-stats, /team-rankings, /lineups, /modelo-info y las rutas del pronóstico y resultados.
- /model-metrics lee el JSON de métricas guardadas. /shap-values devuelve back/modelos/shap_values.json. La presencia de ese endpoint no prueba que la interfaz genere explicaciones SHAP individuales en vivo.
- El rendimiento por jornada se calcula fuera de la petición mediante back/precompute_performance.py. /model-performance lee back/modelos/model_performance.json para evitar repetir el cálculo costoso dentro de API Gateway.
- Para rastrear incorporación y transformación de datos, consultar back/sofascore_descargar_json.py, back/sofascore_json_a_csv.py y back/actualizar_bd_liga1.py. Para nombres de equipos, back/team_names.py. Los notebooks disponibles incluyen Sofascore_Liga1_Peru.ipynb, Sofascore_API_Data.ipynb y Actualizar_Predicciones.ipynb.
- Para revisar rutas, etiquetas y llamadas del navegador, comenzar en frontend/app.js. Para dependencias y empaquetado, back/requirements.txt y back/Dockerfile.

## Código de referencia
Los siguientes fragmentos proceden del backend del proyecto al preparar este archivo. Permiten responder sobre las entradas, ventanas, orden de variables y salida de la predicción. Para modificar o ejecutar el proyecto se necesita la versión vigente del repositorio.

```python
MODEL_XG_PATH    = "modelos/corregidos/Goles_Esperadas/modelo_xgboost_liga1_xg.pkl"
MODEL_TIROS_PATH = "modelos/corregidos/Tiros_Puerta/modelo_xgboost_liga1_tiros.pkl"
MODEL_GOLES_PATH = "modelos/corregidos/Goles/modelo_xgboost_liga1_goles.pkl"
DATA_PATH        = "data/bd_liga1.csv"

# Configuración de S3 (se lee del entorno para mayor flexibilidad)
S3_BUCKET = os.environ.get("S3_BUCKET", "liga1-predictor-data")
S3_KEY    = os.environ.get("S3_KEY",    "bd_liga1.csv")

# Configuración de RDS PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL") # postgresql://user:pass@host:5432/dbname

modelo_xg      = None
modelo_tiros   = None
modelo_goles   = None
df_historico   = None
_perf_by_round = []

# Columnas raw a extraer del CSV
COLS_STATS_CSV = [
    'goles', 'Posesión de pelota', 'Goles esperados (xG)', 'Tiros totales',
    'Tiros a puerta', 'Disparos al palo', 'Tiros fuera', 'Tiros bloqueados',
    'Tiros adentro del area', 'Tiros desde fuera del area', 'Fueras de juego',
    'Pases', 'Pases precisos', 'Saques de banda', 'Pases al ultimo tercio',
    'Entradas', 'Intercepciones', 'Recuperaciones', 'Despejes', 'Corners', 'Faltas',
    'Tiros libres', 'Tarjetas amarillas', 'Tarjetas rojas', 'Atajadas', 'Saques de meta',
]

# Variables para rolling (sin Pases/Pases precisos → reemplazados por ratios)
COLS_PARA_ROLLING = [
    'goles', 'Posesión de pelota', 'Goles esperados (xG)', 'Tiros totales',
    'Tiros a puerta', 'Disparos al palo', 'Tiros fuera', 'Tiros bloqueados',
    'Tiros adentro del area', 'Tiros desde fuera del area', 'Fueras de juego',
    'Saques de banda', 'Pases al ultimo tercio',
    'Entradas', 'Intercepciones', 'Recuperaciones', 'Despejes', 'Corners', 'Faltas',
    'Tiros libres', 'Tarjetas amarillas', 'Tarjetas rojas', 'Atajadas', 'Saques de meta',
    'precision_pases', 'precision_tiros', 'conversion_xg', 'ratio_area',
]

# Feature set unificado para los 3 modelos: 28*2 + Local = 57 features
FEATURES_FINAL = (
    [f'{col}_prom_3' for col in COLS_PARA_ROLLING] +
    [f'{col}_prom_5' for col in COLS_PARA_ROLLING] +
    ['Local']
)



def _build_team_df(team_name: str, df_fuente: pd.DataFrame) -> pd.DataFrame | None:
    """Construye el historial de un equipo con ratios calculados."""
    rows = []
    for _, m in df_fuente.iterrows():
        if m.get('equipo_local') == team_name:
            suffix = '_local'
        elif m.get('equipo_visitante') == team_name:
            suffix = '_visitante'
        else:
            continue
        row = {'fecha': m['fecha']}
        for col in COLS_STATS_CSV:
            val = m.get(f'{col}{suffix}', 0)
            num = pd.to_numeric(val, errors='coerce')
            row[col] = num if pd.notna(num) else 0.0
        rows.append(row)

    if not rows:
        return None

    df_t = pd.DataFrame(rows).sort_values('fecha').reset_index(drop=True)

    # Ratios derivados
    df_t['precision_pases'] = (
        df_t['Pases precisos'] / df_t['Pases'].replace(0, np.nan)
    ).fillna(0)
    df_t['precision_tiros'] = (
        df_t['Tiros a puerta'] / df_t['Tiros totales'].replace(0, np.nan)
    ).fillna(0)
    df_t['conversion_xg'] = (
        df_t['goles'] / df_t['Goles esperados (xG)'].replace(0, np.nan)
    ).fillna(0)
    df_t['ratio_area'] = (
        df_t['Tiros adentro del area'] / df_t['Tiros totales'].replace(0, np.nan)
    ).fillna(0)

    return df_t


def compute_team_stats(team_name: str, is_local: int, as_of_date: pd.Timestamp | None = None) -> dict | None:
    if df_historico is None or df_historico.empty:
        return None

    df_fuente = df_historico
    if as_of_date is not None:
        df_fuente = df_historico[df_historico['fecha'] < as_of_date]

    df_t = _build_team_df(team_name, df_fuente)
    if df_t is None:
        return None

    features = {'Local': is_local}
    for col in COLS_PARA_ROLLING:
        features[f'{col}_prom_3'] = float(df_t[col].tail(3).mean())
        features[f'{col}_prom_5'] = float(df_t[col].tail(5).mean())

    return features


def _compute_stats_df(team_name: str, is_local: int, df_sub: pd.DataFrame) -> dict | None:
    df_t = _build_team_df(team_name, df_sub)
    if df_t is None:
        return None

    features = {'Local': is_local}
    for col in COLS_PARA_ROLLING:
        features[f'{col}_prom_3'] = float(df_t[col].tail(3).mean())
        features[f'{col}_prom_5'] = float(df_t[col].tail(5).mean())

    return features


def run_model(modelo, stats: dict) -> tuple[float, int]:
    X = pd.DataFrame([stats])[FEATURES_FINAL]
    prob  = float(modelo.predict_proba(X)[0][1])
    clase = int(modelo.predict(X)[0])
    return round(prob * 100, 1), clase



@app.get("/predict-match")
@limiter.limit("120/minute")
def predict_match(
    request: Request,
    home: str = Query(..., description="Nombre del equipo local"),
    away: str = Query(..., description="Nombre del equipo visitante"),
    fecha: str | None = Query(None, description="Fecha del partido DD/MM/YYYY"),
):
    if any(m is None for m in [modelo_xg, modelo_tiros, modelo_goles]):
        raise HTTPException(status_code=503, detail="Modelos no disponibles")
    if df_historico is None:
        raise HTTPException(status_code=503, detail="Datos históricos no disponibles")

    as_of = None
    if fecha:
        parsed = pd.to_datetime(fecha, format='%d/%m/%Y', errors='coerce')
        if pd.notna(parsed):
            as_of = parsed

    home_stats = compute_team_stats(home, is_local=1, as_of_date=as_of)
    away_stats = compute_team_stats(away, is_local=0, as_of_date=as_of)

    if home_stats is None:
        raise HTTPException(status_code=404, detail=f"Sin datos históricos para: {home}")
    if away_stats is None:
        raise HTTPException(status_code=404, detail=f"Sin datos históricos para: {away}")

    def predict_all(stats: dict) -> dict:
        xg_p,  xg_c  = run_model(modelo_xg,   stats)
        tir_p, tir_c = run_model(modelo_tiros, stats)
        gol_p, gol_c = run_model(modelo_goles, stats)
        return {
            "xg":    {"probabilidad": xg_p,  "alto": xg_c  == 1},
            "tiros": {"probabilidad": tir_p, "alto": tir_c == 1},
            "goles": {"probabilidad": gol_p, "alto": gol_c == 1},
        }

    return {
        "local":     {"equipo": home, **predict_all(home_stats)},
        "visitante": {"equipo": away, **predict_all(away_stats)},
    }

```

## Memorias anteriores de Claude
Las notas de [liga1-xg-predictor-1](docs/contexto/claude/liga1-xg-predictor-1/memory/MEMORY.md) y [liga1-xg-predictor-aws](docs/contexto/claude/liga1-xg-predictor-aws/memory/MEMORY.md) documentan etapas previas. Para citar la versión final, usar la tesis vigente. La evaluación posterior abarcó 144 partidos, participaron cuatro expertos y siete usuarios, y la tesis presenta los resultados en el capítulo VI.
