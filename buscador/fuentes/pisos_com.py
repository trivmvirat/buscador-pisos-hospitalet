"""pisos.com: tarjetas HTML sin coordenadas; la ubicación se geocodifica por barrio."""
import re
import time

from bs4 import BeautifulSoup

from ..http import get_html
from ..modelo import Anuncio

BASE = "https://www.pisos.com"


def _url(municipio: str, pagina: int, precio_max: int) -> str:
    sufijo = "" if pagina == 1 else f"{pagina}/"
    return f"{BASE}/alquiler/pisos-{municipio}/hasta-{precio_max}/{sufijo}"


def _numero(texto: str) -> int | None:
    m = re.search(r"\d[\d.]*", texto)
    return int(m.group().replace(".", "")) if m else None


def _a_anuncio(card) -> Anuncio | None:
    enlace = card.select_one("a.ad-preview__title")
    caja = card.select_one("[data-ad-price]")
    if not enlace or not caja:
        return None
    subtitulo = card.select_one(".ad-preview__subtitle")
    sub = subtitulo.get_text(strip=True) if subtitulo else ""
    # "Collblanc (L'Hospitalet de Llobregat)" -> barrio, municipio
    m = re.match(r"(.*?)\s*\(([^()]*)\)\s*$", sub)
    barrio, municipio = (m.group(1), m.group(2)) if m else (sub, "")

    hab = banos = m2 = None
    for c in card.select(".ad-preview__char"):
        t = c.get_text(strip=True).lower()
        if "hab" in t:
            hab = _numero(t)
        elif "baño" in t:
            banos = _numero(t)
        elif "m²" in t or "m2" in t:
            m2 = _numero(t)

    llamar = card.select_one("[data-number]")
    img = card.select_one(".carousel__main-photo img")
    desc = card.select_one(".ad-preview__description")
    texto_desc = desc.get_text(" ", strip=True).lower() if desc else ""
    return Anuncio(
        id=f"pisos.com:{card.get('id')}",
        fuente="pisos.com",
        titulo=enlace.get_text(strip=True),
        url=BASE + enlace["href"],
        precio=int(caja["data-ad-price"]),
        municipio=municipio,
        barrio=barrio,
        habitaciones=hab,
        banos=banos,
        m2=m2,
        coords_aprox=True,
        temporal=any(k in texto_desc for k in ("temporada", "temporal", "32) d", "estancias superiores")),
        imagenes=[img.get("src") or img.get("data-src")] if img else [],
        descripcion=desc.get_text(" ", strip=True) if desc else "",
        telefono=llamar["data-number"] if llamar else "",
    )


def buscar(municipios: list[str], precio_max: int, paginas_max: int, pausa: float):
    for mun in municipios:
        print(f"  pisos.com · {mun}")
        vistos: set[str] = set()
        for pagina in range(1, paginas_max + 1):
            html = get_html(_url(mun, pagina, precio_max))
            if not html:
                break
            sopa = BeautifulSoup(html, "html.parser")
            # js-similarAd = anuncios "similares" de otras zonas que el portal intercala
            cards = [c for c in sopa.select("div.ad-preview[id]") if "js-similarAd" not in c.get("class", [])]
            nuevos = 0
            for card in cards:
                if card["id"] in vistos:
                    continue
                vistos.add(card["id"])
                a = _a_anuncio(card)
                if a:
                    nuevos += 1
                    yield a
            # pisos.com repite la última página si se pide una que no existe
            if nuevos == 0 or not sopa.select_one(f'a[href$="/{pagina + 1}/"]'):
                break
            time.sleep(pausa)
        time.sleep(pausa)
