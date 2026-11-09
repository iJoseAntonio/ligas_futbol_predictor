"""
Descarga los JSON de Sofascore que necesita sofascore_json_a_csv.py, usando una
pestaña de Google Chrome abierta por el usuario (no un navegador automatizado
aparte). Así las peticiones salen del mismo navegador con el que se navega
Sofascore, a un ritmo pausado.

Pasos:
  1. Cerrar Chrome y abrirlo con depuración remota (PowerShell):
       & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9333 --user-data-dir="$env:TEMP\\chrome-sofascore"
  2. En esa ventana, abrir https://www.sofascore.com/es-la/football/tournament/peru/liga-1/406
     (si Sofascore pide verificación, completarla a mano).
  3. Ejecutar:
       cd back
       python sofascore_descargar_json.py Clausura 14 json_c14
     (se pueden pasar varias rondas: Clausura 14 15)
  4. Convertir a filas del CSV:
       python sofascore_json_a_csv.py json_c14 clausura14.csv

Guarda en la carpeta:
  ronda_<Torneo>_<n>.json  (partidos de la ronda)
  stats_<id>.json          (estadisticas de cada partido terminado)

Requiere: pip install playwright   (no hace falta "playwright install":
se conecta al Chrome que ya esta abierto)
"""
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

CDP_URL = "http://localhost:9333"
SEASON = "/api/v1/unique-tournament/406/season/88529"
PAUSA_S = 1.5  # entre peticiones, para no saturar la API


def fetch_json(page, path):
    """Pide un JSON desde la pestaña de Sofascore (mismo origen, mismas cookies)."""
    res = page.evaluate(
        """async (p) => {
            const r = await fetch(p, {cache: 'no-store'});
            return {status: r.status, body: r.ok ? await r.json() : null};
        }""",
        path,
    )
    time.sleep(PAUSA_S)
    return res["status"], res["body"]


def guardar(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def main(torneo, rondas, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception:
            sys.exit(f"No se encontro Chrome en {CDP_URL}. Abrelo con --remote-debugging-port=9333 (ver paso 1).")
        pages = [pg for ctx in browser.contexts for pg in ctx.pages if "sofascore.com" in pg.url]
        if not pages:
            sys.exit("Abre una pestaña de sofascore.com en ese Chrome y vuelve a ejecutar.")
        page = pages[0]

        for n in rondas:
            status, data = fetch_json(page, f"{SEASON}/events/round/{n}/prefix/{torneo}")
            if status != 200:
                print(f"Ronda {torneo} {n}: HTTP {status}. Si es 403, recarga la pestaña de Sofascore "
                      f"(completa la verificacion si aparece) y reintenta.")
                continue
            guardar(os.path.join(carpeta, f"ronda_{torneo}_{n}.json"), data)
            eventos = data.get("events", [])
            print(f"Ronda {torneo} {n}: {len(eventos)} partidos")

            for e in eventos:
                eid, vs = e["id"], f"{e['homeTeam']['name']} vs {e['awayTeam']['name']}"
                if e["status"]["type"] != "finished":
                    print(f"  {eid} {vs}: {e['status']['type']}, sin estadisticas")
                    continue
                status, stats = fetch_json(page, f"/api/v1/event/{eid}/statistics")
                if status != 200:
                    print(f"  {eid} {vs}: HTTP {status}")
                    continue
                guardar(os.path.join(carpeta, f"stats_{eid}.json"), stats)
                claves = {it["key"] for per in stats["statistics"] if per["period"] == "ALL"
                          for g in per["groups"] for it in g["statisticsItems"]}
                aviso = "" if "expectedGoals" in claves else "  <- aun sin xG"
                print(f"  {eid} {vs}: ok{aviso}")

    print(f"\nListo. Siguiente paso: python sofascore_json_a_csv.py {carpeta} salida.csv")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("Uso: python sofascore_descargar_json.py <Apertura|Clausura> <ronda> [ronda ...] <carpeta>")
    torneo, *rondas, carpeta = sys.argv[1:]
    main(torneo, [int(r) for r in rondas], carpeta)
