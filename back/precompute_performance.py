"""
Precalcula el rendimiento del modelo por ronda (usado por /model-performance)
y lo guarda en modelos/model_performance.json.

Este calculo puede tardar ~30 segundos y bloquear el limite duro de 30s que
impone API Gateway para invocar Lambda. Por eso se ejecuta aqui, de forma
manual/offline, y el endpoint solo lee el resultado ya guardado (mismo patron
que shap_values.json).

Correr despues de cada actualizacion de datos (junto con migrate_to_postgres.py):
    cd back
    python precompute_performance.py
"""
import json
import os

import main


def run():
    main.cargar_recursos()
    main._precompute_performance()

    out_path = os.path.join(os.path.dirname(__file__), "modelos", "model_performance.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(main._perf_by_round, f, ensure_ascii=False)

    print(f"OK: {len(main._perf_by_round)} rondas precomputadas -> {out_path}")


if __name__ == "__main__":
    run()
