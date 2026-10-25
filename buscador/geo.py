"""Geocodificación (Nominatim) y tiempos en coche (OSRM), ambos de OpenStreetMap."""
import time

import requests

from .db import BD
from .http import UA_PROYECTO

NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSRM_TABLE = "https://router.project-osrm.org/table/v1/driving/"
LOTE_OSRM = 80


def geocodificar(bd: BD, barrio: str, municipio: str) -> tuple[float, float] | None:
    consulta = ", ".join(x for x in (barrio, municipio, "Barcelona, España") if x)
    cache = bd.geo_get(consulta)
    if cache:
        return None if cache[0] is None else cache
    time.sleep(1.1)  # política de uso de Nominatim: máximo 1 petición/segundo
    try:
        r = requests.get(
            NOMINATIM,
            params={"q": consulta, "format": "json", "limit": 1},
            headers={"User-Agent": UA_PROYECTO},
            timeout=30,
        )
        r.raise_for_status()
        res = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"    ! geocodificación fallida para '{consulta}': {e}")
        return None
    coords = (float(res[0]["lat"]), float(res[0]["lon"])) if res else (None, None)
    bd.geo_set(consulta, *coords)
    return None if coords[0] is None else coords


def _clave(lat, lon, origen):
    # ~10 m de precisión: anuncios del mismo edificio comparten ruta
    return f"{origen[0]:.4f},{origen[1]:.4f}>{lat:.4f},{lon:.4f}"


def minutos_en_coche(bd: BD, origen: tuple[float, float], destinos: list[tuple[float, float]]) -> list[float | None]:
    """Minutos sin tráfico desde origen a cada destino (None si no hay ruta)."""
    resultado: list[float | None] = [None] * len(destinos)
    pendientes = []
    for i, (lat, lon) in enumerate(destinos):
        seg = bd.ruta_get(_clave(lat, lon, origen))
        if seg is not None:
            resultado[i] = seg / 60
        else:
            pendientes.append(i)

    for ini in range(0, len(pendientes), LOTE_OSRM):
        lote = pendientes[ini:ini + LOTE_OSRM]
        puntos = [origen] + [destinos[i] for i in lote]
        coords = ";".join(f"{lon},{lat}" for lat, lon in puntos)  # OSRM usa lon,lat
        try:
            r = requests.get(
                OSRM_TABLE + coords,
                params={"sources": "0", "annotations": "duration"},
                headers={"User-Agent": UA_PROYECTO},
                timeout=60,
            )
            r.raise_for_status()
            duraciones = r.json()["durations"][0][1:]
        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"    ! OSRM falló: {e}")
            continue
        for i, seg in zip(lote, duraciones):
            if seg is not None:
                bd.ruta_set(_clave(*destinos[i], origen), seg)
                resultado[i] = seg / 60
        time.sleep(1)
    return resultado
