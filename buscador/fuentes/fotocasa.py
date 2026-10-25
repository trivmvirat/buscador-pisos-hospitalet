"""Fotocasa: los anuncios vienen como JSON en <script id="__initial_props__">."""
import json
import re
import time

from ..detalles import caracteristicas_fotocasa
from ..http import get_html
from ..modelo import Anuncio

BASE = "https://www.fotocasa.es"
RE_PROPS = re.compile(r'<script[^>]*id="__initial_props__"[^>]*>(.*?)</script>', re.S)

TIPOS = {
    "Flat": "Piso", "Study": "Estudio", "Apartment": "Apartamento",
    "Penthouse": "Ático", "Duplex": "Dúplex", "Loft": "Loft",
    "House": "Casa", "Chalet": "Chalet", "GroundFloor": "Planta baja",
}


def _url(municipio: str, pagina: int, precio_max: int) -> str:
    sufijo = "" if pagina == 1 else f"/{pagina}"
    return f"{BASE}/es/alquiler/viviendas/{municipio}/todas-las-zonas/l{sufijo}?maxPrice={precio_max}"


def _a_anuncio(e: dict) -> Anuncio:
    feats = {f["key"]: f["value"] for f in e.get("features", [])}
    dir_ = e.get("address") or {}
    coords = e.get("coordinates") or {}
    subtipo = e.get("buildingSubtype") or e.get("buildingType") or "Vivienda"
    # Fotocasa a veces manda "N/A" o "N/A, Sants" como ubicación
    sin_na = lambda x: ", ".join(p for p in (x or "").split(", ") if p and p != "N/A")
    barrio = next((sin_na(x) for x in (e.get("location"), dir_.get("neighborhood"), dir_.get("district")) if sin_na(x)), "")
    imgs = [m["src"] for m in e.get("multimedia", []) if m.get("type") == "image"]
    return Anuncio(
        id=f"fotocasa:{e['id']}",
        fuente="Fotocasa",
        titulo=f"{TIPOS.get(subtipo, subtipo)} en {barrio}".strip(),
        url=BASE + (e.get("detail") or {}).get("es-ES", ""),
        precio=int(e.get("rawPrice") or 0),
        municipio=dir_.get("municipality") or "",
        barrio=", ".join(x for x in (barrio, dir_.get("district")) if x and x != barrio) or barrio,
        habitaciones=feats.get("rooms"),
        banos=feats.get("bathrooms"),
        m2=feats.get("surface"),
        lat=coords.get("latitude"),
        lon=coords.get("longitude"),
        temporal=bool(e.get("isTemporaryRental")),
        imagenes=imgs,
        descripcion=e.get("description") or "",
        caracteristicas=caracteristicas_fotocasa(e.get("features", [])),
        anunciante=e.get("clientAlias") or "",
        telefono=e.get("phone") or "",
        extra={"uuid": e.get("realEstateAdId")},
    )


def buscar(municipios: list[str], precio_max: int, paginas_max: int, pausa: float):
    for mun in municipios:
        print(f"  Fotocasa · {mun}")
        for pagina in range(1, paginas_max + 1):
            html = get_html(_url(mun, pagina, precio_max))
            if not html:
                break
            m = RE_PROPS.search(html)
            if not m:
                print("    ! no se encontró el JSON de resultados (¿cambio en la web o bloqueo?)")
                break
            resultado = json.loads(m.group(1)).get("initialSearch", {}).get("result", {})
            items = resultado.get("realEstates") or []
            for e in items:
                try:
                    yield _a_anuncio(e)
                except (KeyError, TypeError, ValueError) as err:
                    print(f"    ! anuncio ignorado: {err}")
            total = (resultado.get("resultsV2") or {}).get("totalItems", 0)
            tam = ((resultado.get("resultsV2") or {}).get("page") or {}).get("size", 30)
            if not items or pagina * tam >= total:
                break
            time.sleep(pausa)
        time.sleep(pausa)
