"""Ficha completa de cada anuncio: todas las fotos, descripción, características y coordenadas.

Solo se descarga para los pisos que ya han pasado los filtros, y se guarda en la BD
para no repetirlo en cada búsqueda. Los portales leídos desde Chrome guardan su ficha
en entrada/detalles/<portal>.json (ver chrome/extractor.js).
"""
import json
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup

from .http import get_html
from .modelo import Anuncio

FOTOCASA_FEATS = {
    "air_conditioner": "Aire acondicionado", "heating": "Calefacción", "furnished": "Amueblado",
    "elevator": "Ascensor", "parking": "Parking", "terrace": "Terraza", "balcony": "Balcón",
    "yard": "Patio", "swimming_pool": "Piscina", "garden": "Jardín", "storage_room": "Trastero",
    "pets_allowed": "Admite mascotas", "washing_machine": "Lavadora", "equiped_kitchen": "Cocina equipada",
    "internet": "Internet", "tv": "Televisión", "fridge": "Nevera", "dishwasher": "Lavavajillas",
}
HABITACLIA_FEATS = {
    "FURNISHED": "Amueblado", "AIR_CONDITIONER": "Aire acondicionado", "HEATING": "Calefacción",
    "ELEVATOR": "Ascensor", "PRIVATE_PARKING": "Parking", "TERRACE": "Terraza", "BALCONY": "Balcón",
    "PETS_ALLOWED": "Admite mascotas", "WASHING_MACHINE": "Lavadora", "TV": "Televisión",
    "PRIVATE_GARDEN": "Jardín", "SWIMMING_POOL": "Piscina", "STORAGE_ROOM": "Trastero",
}


def caracteristicas_fotocasa(features: list[dict]) -> list[str]:
    return [FOTOCASA_FEATS[f["key"]] for f in features if f["key"] in FOTOCASA_FEATS]


def _pisos_com(html: str) -> dict:
    sopa = BeautifulSoup(html, "html.parser")
    # Cada foto aparece en varios tamaños; nos quedamos con la grande (xl-wp) una sola vez
    vistas, imagenes = set(), []
    for url in re.findall(r"https://fotos\.imghs\.net/[a-z-]+-wp/\d+/\w+/[\w-]+\.jpg", html):
        nombre = url.rsplit("/", 1)[1]
        if "/prof-wp/" in url or nombre in vistas:
            continue
        vistas.add(nombre)
        imagenes.append(re.sub(r"/[a-z]+-wp/", "/xl-wp/", url, count=1))
    desc = sopa.select_one(".description__content")
    coords = re.search(r"latitude=([\d.-]+)&(?:amp;)?longitude=([\d.-]+)", html)
    return {
        "imagenes": imagenes,
        "descripcion": desc.get_text("\n", strip=True) if desc else "",
        "caracteristicas": [f.get_text(" ", strip=True) for f in sopa.select(".features__feature")],
        "lat": float(coords.group(1)) if coords else None,
        "lon": float(coords.group(2)) if coords else None,
    }


def _habitaclia(html: str) -> dict:
    # Los datos van en el payload de Next.js, con las comillas escapadas
    datos = html.replace('\\"', '"')
    imagenes = list(dict.fromkeys(
        u + "?rule=original"
        for u in re.findall(r"https://static\.fotocasa\.es/images/ads/[0-9a-f-]{36}", html)
    ))
    desc = re.search(r'"description":"((?:[^"\\]|\\.)*)"', datos)
    try:
        descripcion = json.loads(f'"{desc.group(1)}"') if desc else ""
    except json.JSONDecodeError:
        descripcion = desc.group(1) if desc else ""
    feats = re.search(r'"features":\{"has":\[([^\]]*)\]', datos)
    tiene = re.findall(r'"([A-Z_]+)"', feats.group(1)) if feats else []
    coords = re.search(r'"coordinates":\{"latitude":([\d.-]+),"longitude":([\d.-]+)', datos)
    return {
        "imagenes": imagenes,
        "descripcion": descripcion,
        "caracteristicas": [HABITACLIA_FEATS.get(t, t.replace("_", " ").capitalize()) for t in tiene],
        "lat": float(coords.group(1)) if coords else None,
        "lon": float(coords.group(2)) if coords else None,
    }


DESCARGABLES = {"pisos.com": _pisos_com, "Habitaclia": _habitaclia}


RE_TEMPORAL = re.compile(
    r"alquiler temporal|contrato temporal|piso temporal|temporada|32\)? d[ií]as|fines de ocio"
    r"|m[aá]x(?:imo)?\.? ?11 meses|meses no renovable|septiembre? ?\d{4} ?- ?junio",
    re.I,
)


def _aplicar(a: Anuncio, d: dict):
    if d.get("temporal") or RE_TEMPORAL.search(d.get("descripcion") or ""):
        a.temporal = True
    if d.get("imagenes"):
        a.imagenes = d["imagenes"]
    a.descripcion = d.get("descripcion") or a.descripcion
    a.caracteristicas = d.get("caracteristicas") or a.caracteristicas
    for campo in ("planta", "anunciante"):
        if d.get(campo):
            setattr(a, campo, d[campo])
    if d.get("lat") and d.get("lon"):
        a.lat, a.lon, a.coords_aprox = d["lat"], d["lon"], False
    elif d.get("ubicacion"):
        # Idealista no da coordenadas, pero sí calle y barrio: se vuelve a geocodificar con ellos
        a.barrio = ", ".join(d["ubicacion"][:2])
        a.lat = a.lon = None


def completar(anuncios: list[Anuncio], bd, carpeta_chrome: Path, pausa: float, descargar=True) -> list[Anuncio]:
    """Completa los anuncios con su ficha. Devuelve los de Chrome a los que aún les falta."""
    chrome = {}
    for f in (carpeta_chrome.glob("*.json") if carpeta_chrome.exists() else []):
        chrome.update(json.loads(f.read_text(encoding="utf-8")))

    pendientes_chrome = []
    for a in anuncios:
        d = bd.detalle_get(a.id)
        if d is None and a.id in chrome:
            d = chrome[a.id]
            bd.detalle_set(a.id, d)
        if d is None and a.fuente in DESCARGABLES and descargar:
            print(f"  ficha · {a.fuente} · {a.titulo[:50]}")
            html = get_html(a.url)
            if html:
                d = DESCARGABLES[a.fuente](html)
                bd.detalle_set(a.id, d)
            time.sleep(pausa)
        if d is not None:
            _aplicar(a, d)
        elif a.fuente not in DESCARGABLES and a.fuente != "Fotocasa":
            pendientes_chrome.append(a)
    return pendientes_chrome
