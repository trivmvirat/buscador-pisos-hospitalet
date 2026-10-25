"""Anuncios de portales que bloquean peticiones automáticas (Idealista, Wolorent, yaencontre).

Se leen desde Chrome con chrome/extractor.js y se guardan en entrada/<portal>.json:
{"portal": "idealista", "fecha": "2026-10-24T12:00:00", "anuncios": [ {...}, ... ]}
"""
import json
from datetime import datetime
from pathlib import Path

from ..modelo import Anuncio

NOMBRES = {"idealista": "Idealista", "wolorent": "Wolorent", "yaencontre": "yaencontre"}
DIAS_CADUCIDAD = 2


def cargar(carpeta: Path):
    for fichero in sorted(carpeta.glob("*.json")):
        datos = json.loads(fichero.read_text(encoding="utf-8"))
        portal = datos.get("portal") or fichero.stem
        fecha = datos.get("fecha")
        edad = ""
        if fecha:
            dias = (datetime.now() - datetime.fromisoformat(fecha)).days
            edad = f", leído hace {dias} días" if dias else ", leído hoy"
            if dias > DIAS_CADUCIDAD:
                print(f"  ! {fichero.name} tiene {dias} días: conviene volver a leerlo desde Chrome")
        anuncios = datos.get("anuncios", [])
        print(f"  {NOMBRES.get(portal, portal)} (Chrome) · {len(anuncios)} anuncios{edad}")
        for a in anuncios:
            if a.get("no_disponible") or not a.get("precio"):
                continue
            yield Anuncio(
                id=f"{portal}:{a['id']}",
                fuente=NOMBRES.get(portal, portal),
                titulo=a.get("titulo") or "",
                url=a.get("url") or "",
                precio=int(a["precio"]),
                municipio=a.get("municipio") or "",
                barrio=a.get("barrio") or "",
                habitaciones=a.get("habitaciones"),
                banos=a.get("banos"),
                m2=a.get("m2"),
                coords_aprox=True,
                temporal=bool(a.get("temporal")),
                imagenes=[a["imagen"]] if a.get("imagen") else [],
                descripcion=a.get("texto") or "",
                planta=a.get("planta") or "",
            )
