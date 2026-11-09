"""
Agrega a data/bd_liga1.csv las estadisticas de los partidos terminados que
estan en data/partidos_liga1_2026.csv pero aun no en bd_liga1.csv.

Las estadisticas se leen de los JSON ya descargados en raw_stats/<event_id>.json
(la carpeta que llena Sofascore_API_Data.ipynb). No descarga nada.

Uso (desde back/):
    python actualizar_bd_liga1.py              # solo muestra lo que agregaria
    python actualizar_bd_liga1.py --guardar    # agrega las filas a bd_liga1.csv
    python actualizar_bd_liga1.py --stats ../raw_stats --guardar
"""
import argparse
import json
import os
import re
import shutil

import pandas as pd

from sofascore_json_a_csv import KEYS, num
from team_names import normalizar_equipo

BASE = os.path.dirname(os.path.abspath(__file__))
BD = os.path.join(BASE, "data", "bd_liga1.csv")
PARTIDOS = os.path.join(BASE, "data", "partidos_liga1_2026.csv")
STATS_DEFAULT = os.path.join(BASE, "..", "raw_stats")

# Sofascore omite una estadistica cuando vale 0 en ambos equipos (tarjetas rojas,
# palos, fueras de juego...), y ahi el 0 es correcto. Pero si falta alguna de estas,
# el JSON esta incompleto (descargado antes de que Sofascore la publicara) y el 0
# contaminaria los promedios moviles del modelo: el partido se omite.
CRITICAS = {"Posesión de pelota", "Goles esperados (xG)", "Tiros totales", "Tiros a puerta", "Pases", "Pases precisos"}


def match_id(url):
    m = re.search(r"#id:(\d+)", str(url))
    return m.group(1) if m else None


def items_all(stats):
    """key -> item del periodo ALL (si una key se repite en varios grupos, la primera)."""
    items = {}
    period = next((s for s in stats.get("statistics", []) if s.get("period") == "ALL"), None)
    if period is None:
        return items
    for g in period.get("groups", []):
        for it in g.get("statisticsItems", []):
            items.setdefault(it["key"], it)
    return items


def build_row(p, stats, cols):
    items = items_all(stats)
    eid = p["event_id"]
    row = {
        "fecha": p["fecha"],
        "jornada": f"{p['fase']} {p['round']}",
        "equipo_local": normalizar_equipo(p["equipo_local"]),
        "equipo_visitante": normalizar_equipo(p["equipo_visitante"]),
        "goles_local": f"{float(p['goles_local']):.1f}",
        "goles_visitante": f"{float(p['goles_visitante']):.1f}",
        # Sin slug del partido se usa una URL minima; lo importante es el "#id:"
        "url_partido": p["url_partido"] or f"https://www.sofascore.com/es-la/football/match/#id:{eid}",
    }
    faltan = []
    for col, key in KEYS:
        it = items.get(key)
        for side, suf in (("home", "_local"), ("away", "_visitante")):
            if it is None:
                val = "0"
            elif key == "ballPossession":
                val = num(float(it[side + "Value"]) / 100)
            elif key == "finalThirdPhaseStatistic":
                val = f"{it[side + 'Value']}/{it[side + 'Total']}"
            else:
                val = num(it[side + "Value"])
            row[col + suf] = val
        if it is None:
            faltan.append(col)
    row["Saques de meta_visitante"] = f"{float(row['Saques de meta_visitante']):.1f}"
    return [row[c] for c in cols], faltan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default=STATS_DEFAULT, help="carpeta con <event_id>.json")
    ap.add_argument("--guardar", action="store_true", help="escribir en bd_liga1.csv")
    args = ap.parse_args()

    bd = pd.read_csv(BD, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    cols = list(bd.columns)
    en_bd = {match_id(u) for u in bd["url_partido"]}

    partidos = pd.read_csv(PARTIDOS, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    terminados = partidos[(partidos["estado"] == "finished") & (partidos["goles_local"] != "")]
    pendientes = terminados[~terminados["event_id"].isin(en_bd)].copy()
    pendientes["_f"] = pd.to_datetime(pendientes["fecha"], format="%d/%m/%Y")
    pendientes["_h"] = pendientes["hora"].replace("", "00:00")
    pendientes = pendientes.sort_values(["_f", "_h"])

    equipos_bd = set(bd["equipo_local"]) | set(bd["equipo_visitante"])
    filas, avisos = [], []
    for _, p in pendientes.iterrows():
        eid = p["event_id"]
        vs = f"{p['fase']} {p['round']} | {p['equipo_local']} vs {p['equipo_visitante']} ({eid})"
        ruta = os.path.join(args.stats, f"{eid}.json")
        if not os.path.exists(ruta):
            avisos.append(f"{vs}: falta {os.path.basename(ruta)} en {os.path.abspath(args.stats)}")
            continue
        with open(ruta, encoding="utf-8") as f:
            stats = json.load(f)
        if not items_all(stats):
            avisos.append(f"{vs}: el JSON no tiene estadisticas del periodo ALL")
            continue
        fila, faltan = build_row(p, stats, cols)
        criticas = sorted(CRITICAS & set(faltan))
        if criticas:
            avisos.append(f"{vs}: faltan {criticas}; borra {os.path.basename(ruta)} y vuelve a descargar las estadisticas")
            continue
        nuevos = {fila[2], fila[3]} - equipos_bd
        if nuevos:
            avisos.append(f"{vs}: equipo sin equivalencia en bd_liga1 {sorted(nuevos)} (agregar a team_names.py)")
            continue
        filas.append(fila)
        print(f"{fila[0]:>10} {fila[1]:<12} {fila[2]} {fila[4][:-2]}-{fila[5][:-2]} {fila[3]}"
              f" | xG {fila[9]}-{fila[10]} | sin dato: {', '.join(faltan) or '-'}")

    print(f"\n{len(filas)} partidos nuevos para bd_liga1.csv ({len(terminados)} terminados en el fixture, {len(bd)} filas en bd)")
    for a in avisos:
        print("AVISO:", a)

    if args.guardar and filas:
        shutil.copy(BD, BD + ".bak")
        nuevo = pd.concat([bd, pd.DataFrame(filas, columns=cols)], ignore_index=True)
        # Mismo formato que el archivo original: CRLF y sin salto de linea al final
        texto = nuevo.to_csv(sep=";", index=False, lineterminator="\r\n").rstrip("\r\n")
        with open(BD, "w", encoding="utf-8-sig", newline="") as f:
            f.write(texto)
        print(f"Guardado: {len(nuevo)} filas en {BD} (copia anterior en bd_liga1.csv.bak)")
    elif filas:
        print("Para agregarlas: python actualizar_bd_liga1.py --guardar")


if __name__ == "__main__":
    main()
