"""
Scraper de alineaciones (Sofascore) para los partidos ya jugados de la
temporada 2026.

Sofascore bloquea clientes HTTP simples (requests, cloudscraper) con un 403
via Cloudflare, asi que usamos un navegador real automatizado (Playwright):
se navega una sola vez a sofascore.com y, dentro de esa misma pagina, se
hacen fetch() repetidos a /api/v1/event/{id}/lineups para cada partido -
eso evita el bloqueo y es rapido (~0.1s por partido).

El match_id de cada partido se extrae de la columna url_partido del propio
CSV (el numero despues de "#id:").

Guarda el resultado en back/modelos/lineups_2026.json, con el mismo patron
que shap_values.json / model_performance.json: un archivo precalculado que
el endpoint /lineups solo lee, sin volver a scrapear en cada peticion.

Correr despues de cada actualizacion de jornada (junto con
migrate_to_postgres.py y precompute_performance.py):
    cd back
    python scrape_lineups.py
"""
import json
import os
import re
import time

import pandas as pd
from playwright.sync_api import sync_playwright

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "partidos_liga1_2026.csv")
OUT_PATH = os.path.join(os.path.dirname(__file__), "modelos", "lineups_2026.json")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"
)


def normalize_date(fecha: str) -> str:
    """'8/05/2026' -> '08/05/2026' (mismo formato que usa el frontend)."""
    parts = str(fecha).strip().split("/")
    if len(parts) != 3:
        return str(fecha).strip()
    d, m, y = parts
    return f"{d.zfill(2)}/{m.zfill(2)}/{y}"


def extract_match_id(url: str) -> str | None:
    if not isinstance(url, str):
        return None
    match = re.search(r"#id:(\d+)", url)
    return match.group(1) if match else None


def simplify_team(team_data: dict) -> dict:
    players = []
    for p in team_data.get("players", []):
        player = p.get("player", {})
        stats = p.get("statistics", {}) or {}
        players.append({
            "playerId":   player.get("id"),
            "name":       player.get("name"),
            "shortName":  player.get("shortName"),
            "jerseyNumber": p.get("jerseyNumber"),
            "position":   p.get("position"),       # G / D / M / F
            "substitute": bool(p.get("substitute")),
            "rating":     stats.get("rating"),
            "minutesPlayed": stats.get("minutesPlayed"),
            "goals":      stats.get("goals"),
            "goalAssist": stats.get("goalAssist"),
        })
    return {
        "formation": team_data.get("formation"),
        "players":   players,
    }


def scrape():
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: no se encontro {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8-sig")
    df.columns = df.columns.str.strip()

    # Solo partidos ya jugados (con marcador)
    jugados = df[df["goles_local"].notna() & df["goles_visitante"].notna()].copy()
    jugados["match_id"] = jugados["url_partido"].apply(extract_match_id)
    jugados = jugados[jugados["match_id"].notna()]

    print(f"Partidos jugados con match_id: {len(jugados)} de {len(df)} totales en el fixture.")

    results = []
    errores = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto("https://www.sofascore.com/", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        for i, (_, row) in enumerate(jugados.iterrows(), start=1):
            match_id = row["match_id"]
            home = row["equipo_local"]
            away = row["equipo_visitante"]
            fecha = normalize_date(row["fecha"])

            try:
                result = page.evaluate(f"""async () => {{
                    const res = await fetch('https://www.sofascore.com/api/v1/event/{match_id}/lineups');
                    return {{status: res.status, body: await res.text()}};
                }}""")

                if result["status"] != 200:
                    print(f"[{i}/{len(jugados)}] {home} vs {away} ({fecha}) -> HTTP {result['status']}, se omite")
                    errores.append(f"{home} vs {away} ({fecha}): HTTP {result['status']}")
                    continue

                data = json.loads(result["body"])
                if not data.get("home", {}).get("players"):
                    print(f"[{i}/{len(jugados)}] {home} vs {away} ({fecha}) -> sin alineacion confirmada, se omite")
                    continue

                results.append({
                    "fecha":      fecha,
                    "home_team":  home,
                    "away_team":  away,
                    "home":       simplify_team(data.get("home", {})),
                    "away":       simplify_team(data.get("away", {})),
                })
                print(f"[{i}/{len(jugados)}] {home} vs {away} ({fecha}) -> OK")

            except Exception as e:
                print(f"[{i}/{len(jugados)}] {home} vs {away} ({fecha}) -> ERROR: {e}")
                errores.append(f"{home} vs {away} ({fecha}): {e}")

            time.sleep(0.3)  # pausa pequeña, por cortesia hacia el servidor

        browser.close()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)

    print(f"\nOK: {len(results)} alineaciones guardadas -> {OUT_PATH}")
    if errores:
        print(f"\n{len(errores)} partidos sin alineacion (normal si no hay datos en Sofascore para ese partido):")
        for e in errores:
            print(" -", e)


if __name__ == "__main__":
    scrape()
