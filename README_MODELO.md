# Modelo predictivo de la Liga 1 del Perú

Esta guía conecta la metodología de la tesis con la programación de xG Fútbol. La unidad de predicción es **un equipo en un partido**. La aplicación calcula tres probabilidades antes del encuentro y repite el procedimiento para el otro equipo. Una consulta de partido produce seis pronósticos.

| Clasificador | La clase positiva significa que el equipo alcanza… |
|---|---|
| Goles esperados (xG) | Al menos 1,5 xG acumulados durante el encuentro |
| Tiros a puerta | Al menos cinco tiros a puerta |
| Goles anotados | Al menos dos goles |

Los indicadores pueden cumplirse simultáneamente. Un pronóstico del 65 % para xG representa una probabilidad estimada de alcanzar 1,5 xG. Para determinar el resultado real se consulta el xG del equipo registrado por el proveedor de estadísticas. La tesis trabaja a escala de equipo y partido.

## 1. De los partidos a la matriz de predictores

En el periodo de desarrollo se recopilaron estadísticas de **1 078 partidos**. Al distinguir el local y el visitante se obtuvieron **2 156 registros equipo-partido**. Tras la preparación quedaron **2 123 registros**. La tesis atribuye los faltantes al desplazamiento temporal y a divisiones por cero en indicadores derivados. El documento no desglosa los 33 registros por causa.

El backend identifica 26 estadísticas originales por equipo. A partir de ellas combina cuatro indicadores:

| Indicador | Cálculo por equipo y partido |
|---|---|
| Precisión de pases | Pases precisos / pases intentados |
| Precisión de tiros | Tiros a puerta / tiros totales |
| Conversión de xG | Goles anotados / goles esperados |
| Proporción de tiros dentro del área | Tiros dentro del área / tiros totales |

Se conservan 24 estadísticas originales para las ventanas móviles. Pases y pases precisos se representan mediante su razón, tras observar una correlación de Pearson cercana a 0,99. Las 24 estadísticas y los cuatro indicadores dan 28 variables. Para cada una se obtiene una media de tres encuentros anteriores y otra de cinco. La condición de local (1) o visitante (0) completa **28 × 2 + 1 = 57 predictores**. El orden exacto se define en `FEATURES_FINAL` y se aplica antes de llamar al modelo. [Implementación y listas de columnas](back/main.py)

**Ejemplo.** Si los tiros a puerta en los cinco partidos anteriores fueron 2, 6, 3, 4 y 5, el promedio de tres es 4 y el de cinco también es 4. Ambos valores se conocen antes del partido que se pronostica. Durante la preparación descrita en la tesis se desplaza la serie un partido antes de calcular los promedios. En la API se obtiene el mismo corte temporal filtrando por fecha antes de tomar los últimos encuentros. La implementación en línea admite ventanas parciales cuando hay menos de tres o cinco antecedentes y rellena con cero las divisiones indefinidas de los indicadores derivados.

## 2. Entrenamiento, validación temporal y SMOTE

| Etapa | Observaciones | Función |
|---|---:|---|
| Entrenamiento | 1 701 registros, hasta el 23/08/2025 | Ajustar hiperparámetros mediante cinco particiones temporales y entrenar los clasificadores |
| Prueba interna | 422 registros, del 24/08/2025 al 27/04/2026 | Comparar los cuatro algoritmos después del ajuste |
| Evaluación posterior de la tesis | 144 partidos, 288 registros por indicador, del 02/05 al 11/10/2026 | Contrastar los pronósticos con lo ocurrido en 16 jornadas posteriores |

**Por qué se usa el tiempo.** Una división aleatoria puede hacer que un modelo aprenda con partidos posteriores a los que se pretende pronosticar. El procedimiento documentado usa cinco particiones de `TimeSeriesSplit` dentro del bloque de entrenamiento. Cada validación se realiza sobre un tramo posterior al que se utilizó para ajustar esa configuración.

**Qué hace SMOTE.** Para cada indicador se identifica la clase minoritaria dentro del bloque de ajuste. SMOTE toma un registro de esa clase y uno de sus vecinos de la misma clase y genera una combinación intermedia de sus predictores. Esquemáticamente, se calcula `x_nuevo = x + λ × (x_vecino − x)`, con λ entre 0 y 1. La muestra sintética conserva la etiqueta minoritaria. Representa un punto de entrenamiento en el espacio de características y no corresponde a un encuentro disputado.

**Dónde se aplica.** Para cada ensayo de Optuna y cada partición temporal se toman las filas originales del tramo de ajuste, se balancea ese tramo con SMOTE, se entrena el clasificador y se puntúa en las filas reales de la validación posterior. Optuna compara las configuraciones mediante el promedio de los cinco resultados. Con los hiperparámetros elegidos se balancea el bloque completo de entrenamiento para el ajuste final por indicador. La estrategia descrita llega a una proporción 1:1 en entrenamiento. La prueba interna y las jornadas posteriores conservan las frecuencias observadas. Aplicar SMOTE antes de dividir permitiría que la construcción de vecinos utilizara información del periodo de validación.

## 3. Cómo aprende XGBoost y por qué se eligió

Cada clasificador aprende una secuencia de árboles. El primer conjunto de predicciones deja errores. En cada iteración, XGBoost utiliza el gradiente y la curvatura de la función de pérdida para elegir divisiones y valores de hoja que mejoren la predicción acumulada. La tasa de aprendizaje regula cuánto añade cada árbol. Para un objetivo logístico binario, la suma de contribuciones se transforma mediante la función logística en una probabilidad entre 0 y 1. Durante la inferencia, el servicio recupera la probabilidad positiva con `predict_proba` y la clase con `predict`. La regla de decisión documentada en la tesis utiliza un punto de corte del 50 %.

| Hiperparámetro guardado | xG | Tiros a puerta | Goles | Qué controla |
|---|---:|---:|---:|---|
| n_estimators | 267 | 248 | 237 | Cantidad de árboles |
| max_depth | 6 | 6 | 6 | Profundidad máxima de cada árbol |
| learning_rate | 0,0408 | 0,0475 | 0,0403 | Peso de las correcciones sucesivas |
| subsample | 0,9324 | 0,9728 | 0,8706 | Fracción de observaciones muestreadas por iteración |
| colsample_bytree | 0,7787 | 0,7672 | 0,7541 | Fracción de variables candidatas por árbol |
| gamma | 0,7453 | 0,7094 | 0,7694 | Reducción mínima de pérdida para aceptar una división |
| min_child_weight | 1 | 1 | 1 | Suma mínima de hessianos en un nodo hijo |

Las configuraciones guardan `random_state=42` y `eval_metric=logloss`. Esta última es una métrica interna de XGBoost. El criterio que Optuna usó para comparar ensayos, según la tesis, fue la exactitud en los modelos de árboles y el F1 en regresión logística. [Configuraciones y resultados guardados](back/modelos/corregidos)

En los 422 registros de prueba, XGBoost obtuvo la mayor exactitud para xG (64,69 %, frente a 64,22 % de LightGBM). Random Forest obtuvo la mayor exactitud para tiros a puerta (62,80 %). La regresión logística lideró en AUC-ROC y F1 en los tres indicadores. Se eligió XGBoost por su desempeño en xG y para implementar e interpretar los tres clasificadores con una familia común. Los criterios de optimización distintos también influyen en la comparación. [Métricas de los cuatro algoritmos](back/modelos/corregidos/metricas_modelos.json)

## 4. Qué ocurre cuando se consulta un partido

1. El frontend envía los nombres de los equipos y la fecha a `GET /predict-match`. El backend FastAPI carga tres archivos de modelo con joblib y lee el histórico desde PostgreSQL en RDS cuando está configurado. También dispone de alternativas en S3 y en el CSV local.
2. Si la fecha tiene formato válido `DD/MM/YYYY`, `compute_team_stats` conserva únicamente encuentros con fecha estrictamente anterior. Cuando se omite la fecha o el texto no se puede interpretar, el código usa todo el histórico disponible. Para reproducir un partido pasado hay que indicar su fecha correctamente.
3. `_build_team_df` reúne el historial propio de cada equipo, eligiendo las columnas de local o de visitante en cada encuentro anterior. Ordena por fecha, construye los cuatro indicadores y entrega los datos para las medias. Si falta todo el historial de un equipo, la ruta devuelve 404. Si no se cargaron los modelos o el histórico, devuelve 503.
4. `run_model` ordena las 57 columnas, evalúa los tres clasificadores por equipo y devuelve el porcentaje positivo redondeado a un decimal y la clase predicha. El JSON tiene dos objetos, `local` y `visitante`. Cada uno contiene `equipo` y las entradas `xg`, `tiros` y `goles`, con `probabilidad` y `alto`. SMOTE y Optuna pertenecen al entrenamiento previo.
5. La web consulta los resultados observados mediante `/match-result`. El rendimiento por jornada se precalcula fuera de la petición y `/model-performance` sirve el resultado guardado. Al incorporar nuevas jornadas, la web puede abarcar un periodo mayor que el utilizado para las cifras cerradas de la tesis.

**Ejecución local.** Con Python y un entorno virtual activo, se puede iniciar la API desde la raíz del repositorio con los comandos siguientes. El directorio de ejecución importa porque las rutas de modelos y datos son relativas a `back`.

```sh
cd back
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Abrir `http://127.0.0.1:8000/docs`, seleccionar `GET /predict-match` e introducir dos nombres del histórico y la fecha del encuentro. El frontend es un sitio estático y consulta la dirección que configura su JavaScript. [Frontend](frontend/app.js) · [Dependencias](back/requirements.txt) · [Despliegue y estructura](README.md)

## 5. Cómo leer la evaluación estadística

| Métrica en los 144 partidos posteriores | xG ≥ 1,5 | Tiros a puerta ≥ 5 | Goles ≥ 2 |
|---|---:|---:|---:|
| Exactitud | 62,5 % | 57,3 % | 61,1 % |
| Clase mayoritaria del periodo | 57,3 % | 52,8 % | 60,8 % |
| Ventaja descriptiva | 5,2 pp | 4,5 pp | 0,3 pp |
| Precisión positiva | 0,593 | 0,631 | 0,508 |
| Sensibilidad | 0,390 | 0,461 | 0,283 |
| F1 | 0,471 | 0,532 | 0,364 |
| AUC-ROC | 0,628 | 0,607 | 0,540 |
| Brier | 0,247 | 0,259 | 0,259 |

**Matriz de confusión.** Un verdadero positivo (VP) es un equipo que alcanzó el umbral y fue clasificado como positivo. Un falso positivo (FP) es una predicción positiva cuyo umbral se incumplió. Los falsos negativos (FN) son casos positivos que escaparon al modelo y los verdaderos negativos (VN) son rechazos correctos. La exactitud es (VP + VN) / total, la precisión positiva es VP / (VP + FP), la sensibilidad es VP / (VP + FN) y la especificidad es VN / (VN + FP). F1 es la media armónica de precisión y sensibilidad.

**Ejemplo de interpretación.** En xG se acertaron 180 de las 288 clasificaciones (62,5 %), pero solo se detectó el 39,0 % de las actuaciones que alcanzaron 1,5 xG. La exactitud cuenta también los negativos bien clasificados. La referencia mayoritaria se obtuvo con las clases observadas en esas jornadas y sirve como comparación descriptiva. Para goles, el aumento fue de apenas 0,3 puntos porcentuales.

**Probabilidades y umbral.** AUC-ROC resume la capacidad de ordenar los casos positivos por encima de los negativos al variar el punto de corte. Un valor de 0,5 corresponde al ordenamiento esperado por azar. Brier promedia (p − y)², donde p es la probabilidad positiva e y el resultado observado (0 o 1). Menor Brier indica menor error probabilístico. Asignar siempre 0,50 da 0,250 en todos los casos. El valor 0,247 de xG representa una mejora pequeña sobre esa referencia.

**Incertidumbre.** La tesis reporta intervalos del 95 % con Wilson para la exactitud y 2 000 réplicas bootstrap para AUC-ROC. En xG, la exactitud de 62,5 % tiene un intervalo de 56,8 % a 67,9 %. En goles, el intervalo del AUC-ROC (0,473 a 0,608) incluye 0,5. Cada partido aporta dos registros relacionados, por lo que los intervalos y los valores p de la prueba binomial unilateral se interpretan como aproximados. No se especifica en la tesis si el bootstrap remuestreó partidos completos o registros individuales.

## 6. Qué explica SHAP

SHAP distribuye entre los predictores la diferencia entre la salida del modelo para una observación y su valor de referencia. El signo indica la dirección de cada contribución en la escala de salida del explicador. Para el ranking global se promedia el valor absoluto por predictor sobre las **422 observaciones reales de la prueba interna**. Ese promedio mide magnitud y evita que las contribuciones positivas y negativas se cancelen. Los valores explican cómo el modelo usa la información y requieren cautela para interpretar causas deportivas.

La localía ocupó el primer lugar en los tres clasificadores. El segundo predictor fue el promedio de atajadas en tres partidos para xG, el promedio de despejes en cinco partidos para tiros a puerta y el promedio de goles en cinco partidos para goles anotados. La ruta `/shap-values` lee un archivo precalculado. [Resultados SHAP](back/modelos/shap_values.json)

## 7. Mapa de programación y alcance de la reproducción

| Tarea | Punto de entrada |
|---|---|
| Descargar estadísticas y transformar JSON a CSV | [Descarga](back/sofascore_descargar_json.py) y [conversión](back/sofascore_json_a_csv.py) |
| Incorporar jornadas y normalizar equipos | [Actualización](back/actualizar_bd_liga1.py) y [nombres de equipos](back/team_names.py) |
| Revisar qué datos recibe el modelo y cómo obtiene la clase | [Servicio FastAPI](back/main.py), funciones `compute_team_stats`, `_build_team_df`, `run_model` y `predict_match` |
| Recalcular el rendimiento por jornada después de actualizar los datos | [Script offline](back/precompute_performance.py), ejecutado desde `back`; escribe `modelos/model_performance.json` |
| Revisar arquitectura y despliegue | [Contenedor Lambda](back/Dockerfile), [workflow del backend](.github/workflows/deploy-aws.yml) y [workflow del frontend](.github/workflows/deploy-frontend.yml) |
| Continuar con el contexto de la investigación y la sustentación | [Contexto de tesis y programación](Contexto_tesis_y_programacion.md) |

El servicio carga los artefactos de `back/modelos/corregidos`. El backend, sus archivos de configuración y los resultados guardados permiten inspeccionar la inferencia. La descripción del entrenamiento, el diseño estadístico y los 144 partidos corresponde a la evaluación documentada en la tesis. Para repetir el ajuste completo desde cero harían falta también el código de entrenamiento original y la instantánea de los datos empleada en ese experimento.
