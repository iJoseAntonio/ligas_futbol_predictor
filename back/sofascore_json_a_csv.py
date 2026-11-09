"""
Convierte respuestas JSON de Sofascore, guardadas a mano desde el navegador,
en filas con el mismo formato que back/data/bd_liga1.csv.

No descarga nada: solo lee archivos. Para cada fecha:
  1. Abrir en el navegador y guardar (Ctrl+S) como ronda_<Torneo>_<n>.json:
       https://www.sofascore.com/api/v1/unique-tournament/406/season/88529/events/round/<n>/prefix/<Torneo>
  2. Para cada partido terminado, guardar como stats_<id>.json:
       https://www.sofascore.com/api/v1/event/<id>/statistics
  Todos los archivos van en una misma carpeta.

Uso:
    cd back
    python sofascore_json_a_csv.py <carpeta_json> <salida.csv>

Escribe solo las filas de partidos que aun no estan en bd_liga1.csv (por
match_id); no modifica bd_liga1.csv. Revisar la salida y luego pegarla al CSV.
"""
import glob
import json
import os
import re
import sys
import time

import pandas as pd

CSV = os.path.join(os.path.dirname(__file__), "data", "bd_liga1.csv")

# Columna del CSV -> clave de la API de Sofascore
KEYS = [
    ("Posesión de pelota", "ballPossession"), ("Goles esperados (xG)", "expectedGoals"),
    ("Tiros totales", "totalShotsOnGoal"), ("Tiros a puerta", "shotsOnGoal"),
    ("Disparos al palo", "hitWoodwork"), ("Tiros fuera", "shotsOffGoal"),
    ("Tiros bloqueados", "blockedScoringAttempt"), ("Tiros adentro del area", "totalShotsInsideBox"),
    ("Tiros desde fuera del area", "totalShotsOutsideBox"), ("Fueras de juego", "offsides"),
    ("Pases", "passes"), ("Pases precisos", "accuratePasses"), ("Saques de banda", "throwIns"),
    ("Pases al ultimo tercio", "finalThirdEntries"), ("Pases en ultimo tercio", "finalThirdPhaseStatistic"),
    ("Entradas", "totalTackle"), ("Intercepciones", "interceptionWon"), ("Recuperaciones", "ballRecovery"),
    ("Despejes", "totalClearance"), ("Corners", "cornerKicks"), ("Faltas", "fouls"),
    ("Tiros libres", "freeKicks"), ("Tarjetas amarillas", "yellowCards"), ("Tarjetas rojas", "redCards"),
    ("Atajadas", "goalkeeperSaves"), ("Saques de meta", "goalKicks"),
]


def match_id(url):
    m = re.search(r"#id:(\d+)", url)
    return m.group(1) if m else None


def num(v):
    v = float(v)
    return str(int(v)) if v == int(v) else str(v)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def team_names(bd, events):
    """Nombre en Sofascore -> nombre en el CSV, aprendido de partidos que ya estan en el CSV."""
    by_id = {match_id(r["url_partido"]): r for _, r in bd.iterrows()}
    names = {}
    for e in events:
        r = by_id.get(str(e["id"]))
        if r is not None:
            names[e["homeTeam"]["name"]] = r["equipo_local"]
            names[e["awayTeam"]["name"]] = r["equipo_visitante"]
    csv_teams = set(bd["equipo_local"]) | set(bd["equipo_visitante"])
    for e in events:
        for side in ("homeTeam", "awayTeam"):
            t = e[side]
            if t["name"] not in names and t.get("shortName") in csv_teams:
                names[t["name"]] = t["shortName"]
    return names


def build_row(e, prefix, stats, names, cols):
    items = {}
    period = next(s for s in stats["statistics"] if s["period"] == "ALL")
    for g in period["groups"]:
        for it in g["statisticsItems"]:
            items.setdefault(it["key"], it)

    row = {}
    t = time.gmtime(e["startTimestamp"] - 5 * 3600)  # hora de Lima
    row["fecha"] = f"{t.tm_mday}/{t.tm_mon:02d}/{t.tm_year}"
    row["jornada"] = f"{prefix} {e['roundInfo']['round']}"
    row["equipo_local"] = names[e["homeTeam"]["name"]]
    row["equipo_visitante"] = names[e["awayTeam"]["name"]]
    row["goles_local"] = f"{float(e['homeScore']['current']):.1f}"
    row["goles_visitante"] = f"{float(e['awayScore']['current']):.1f}"
    row["url_partido"] = f"https://www.sofascore.com/es-la/football/match/{e['slug']}/{e['customId']}#id:{e['id']}"

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


def main(folder, out_path):
    bd = pd.read_csv(CSV, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    cols = list(bd.columns)
    existentes = {match_id(u) for u in bd["url_partido"]}

    if not os.path.isdir(folder):
        sys.exit(f"No existe la carpeta: {os.path.abspath(folder)}")
    round_files = sorted(glob.glob(os.path.join(folder, "ronda_*.json")))
    if not round_files:
        print(f"No hay archivos ronda_<Torneo>_<n>.json en {os.path.abspath(folder)}")
        print("Archivos encontrados:", os.listdir(folder) or "ninguno")
        sys.exit(1)

    rounds = []
    for path in round_files:
        prefix = os.path.basename(path).split("_")[1]
        rounds.append((prefix, load_json(path)["events"]))
    all_events = [e for _, evs in rounds for e in evs]
    names = team_names(bd, all_events)

    rows, avisos = [], []
    for prefix, events in rounds:
        for e in sorted(events, key=lambda x: x["startTimestamp"]):
            eid = str(e["id"])
            vs = f"{e['homeTeam']['name']} vs {e['awayTeam']['name']}"
            if e["status"]["type"] != "finished":
                avisos.append(f"{eid} {vs}: no terminado ({e['status']['type']}), se omite")
                continue
            if eid in existentes:
                avisos.append(f"{eid} {vs}: ya esta en bd_liga1.csv, se omite")
                continue
            stats_path = os.path.join(folder, f"stats_{eid}.json")
            if not os.path.exists(stats_path):
                avisos.append(f"{eid} {vs}: falta stats_{eid}.json -> https://www.sofascore.com/api/v1/event/{eid}/statistics")
                continue
            sin_nombre = [n for n in (e["homeTeam"]["name"], e["awayTeam"]["name"]) if n not in names]
            if sin_nombre:
                avisos.append(f"{eid} {vs}: equipo sin equivalencia en el CSV: {sin_nombre}")
                continue
            new, faltan = build_row(e, prefix, load_json(stats_path), names, cols)
            rows.append(";".join(new))
            print(new[0], new[1], f"{new[2]} {new[4][:-2]}-{new[5][:-2]} {new[3]}", "| sin dato:", faltan or "-")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + ("\n" if rows else ""))
    print(f"\n{len(rows)} filas nuevas -> {out_path}")
    for a in avisos:
        print("AVISO:", a)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Uso: python sofascore_json_a_csv.py <carpeta_json> <salida.csv>")
    main(sys.argv[1], sys.argv[2])
