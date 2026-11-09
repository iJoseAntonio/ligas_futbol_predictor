"""
Equivalencias entre los nombres de equipo que devuelve la API de Sofascore
y los nombres que usan bd_liga1.csv y partidos_liga1_2026.csv (los mismos con
los que se entrenaron los modelos).
"""

SOFASCORE_A_CSV = {
    "ACD Juan Pablo II": "ADC Juan Pablo II",
    "CD Juan Pablo II": "ADC Juan Pablo II",
    "Asociación Deportiva Tarma": "ADT",
    "Alianza Atlético de Sullana": "Alianza Atlético",
    "CD Moquegua": "Moquegua",
    "Club Atlético Grau": "Atlético Grau",
    "Club Sporting Cristal": "Sporting Cristal",
    "Cusco FC": "Cusco",
    "FC Cajamarca": "Cajamarca",
    "Los Chankas CYC": "Los Chankas",
    "Universidad Técnica de Cajamarca": "UTC",
    "Universitario de Deportes": "Universitario",
}


def normalizar_equipo(nombre):
    """Devuelve el nombre del CSV; si no hay equivalencia, el mismo nombre sin espacios extra."""
    if not isinstance(nombre, str):
        return nombre
    nombre = nombre.strip()
    return SOFASCORE_A_CSV.get(nombre, nombre)
