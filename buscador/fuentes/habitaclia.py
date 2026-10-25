"""Habitaclia: tarjetas <article> sin coordenadas; la ubicación se geocodifica por barrio.

Habitaclia y Fotocasa son del mismo grupo y comparten anuncios: el UUID de la URL
coincide con `realEstateAdId` de Fotocasa, y se guarda en extra["uuid"] para deduplicar.
"""
import json
import re
import time

from bs4 import BeautifulSoup

from ..http import get_html
from ..modelo import Anuncio

BASE = "https://www.habitaclia.com"
RE_UUID = re.compile(r"/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/d")
# En el payload de Next.js de la página de resultados (comillas escapadas):
# ..."publisher":{..."name":"X"...},..."contact":{"email":...,"phone":...},"urls":{"canonical":".../<uuid>/d"
RE_CONTACTO = re.compile(
    r'"contact":\{"email":(null|"[^"]*"),"phone":(null|"[^"]*")\},"urls":\{"canonical":"[^"]*/([0-9a-f-]{36})/d"'
)
RE_ANUNCIANTE = re.compile(r'"publisher":\{"id":"[^"]*","name":"([^"]*)"')


def contactos(html: str) -> dict[str, dict]:
    """uuid -> {telefono, email, anunciante} de todos los anuncios de la página."""
    datos = html.replace('\\"', '"')
    out = {}
    for m in RE_CONTACTO.finditer(datos):
        # El anunciante es el último "publisher" antes de este "contact"
        previos = RE_ANUNCIANTE.findall(datos, max(0, m.start() - 4000), m.start())
        out[m.group(3)] = {
            "email": json.loads(m.group(1)) or "",
            "telefono": json.loads(m.group(2)) or "",
            "anunciante": previos[-1] if previos else "",
        }
    return out


def _url(zona: str, pagina: int, precio_max: int) -> str:
    sufijo = "" if pagina == 1 else f"/{pagina}"
    return f"{BASE}/alquiler/viviendas/{zona}/s{sufijo}?maxPrice={precio_max}"


def _numero(texto: str) -> int | None:
    m = re.search(r"\d[\d.]*", texto)
    return int(m.group().replace(".", "")) if m else None


def zona_por_url(url: str) -> tuple[str, str]:
    """(barrio, municipio) a partir de /alquiler/<tipo>/<barrio>/[<distrito>/]<municipio>/<uuid>/d."""
    partes = [p for p in url.split("/alquiler/", 1)[-1].split("/")[1:-2] if p != "n-a"]
    bonito = lambda s: s.replace("-", " ").title().replace("L Hospitalet", "L'Hospitalet")
    municipio = bonito(partes[-1].replace("barcelona-capital", "barcelona")) if partes else ""
    return (bonito(partes[0]) if len(partes) > 1 else ""), municipio


def _a_anuncio(art) -> Anuncio | None:
    enlace = next((a for a in art.find_all("a", href=True) if RE_UUID.search(a["href"])), None)
    precio = art.select_one(".tabular-nums")
    if not enlace or not precio:
        return None
    uuid = RE_UUID.search(enlace["href"]).group(1)
    titulo = enlace.get_text(strip=True)
    # "Piso en alquiler en Bellvitge - El Gornal - Granvia LH"
    barrio = titulo.split(" en alquiler en ", 1)[-1] if " en alquiler en " in titulo else ""
    textos = [s.get_text(strip=True) for s in art.find_all("span") if not s.find("span")]
    ubic = next((t for t in textos if t.endswith(", Barcelona")), "")
    municipio = ubic.rsplit(",", 1)[0] if ubic else ""
    barrio = "" if barrio.strip() in ("", "N/A") else barrio.strip()
    if not barrio or not municipio:
        b, m = zona_por_url(enlace["href"])
        barrio, municipio = barrio or b, municipio or m
        titulo = re.sub(r" en(?: N/A)?\s*$", f" en {barrio}", titulo) if barrio else titulo

    hab = banos = m2 = None
    for t in textos:
        tl = t.lower()
        if re.fullmatch(r"\d+ hab\.?", tl):
            hab = _numero(tl)
        elif re.fullmatch(r"\d+ baños?", tl):
            banos = _numero(tl)
        elif re.fullmatch(r"[\d.]+ m²", tl):
            m2 = _numero(tl)

    img = art.find("img")
    return Anuncio(
        id=f"habitaclia:{uuid}",
        fuente="Habitaclia",
        titulo=titulo.replace(" en alquiler en ", " en "),
        url=BASE + enlace["href"],
        precio=_numero(precio.get_text()) or 0,
        municipio=municipio,
        barrio=barrio,
        habitaciones=hab,
        banos=banos,
        m2=m2,
        coords_aprox=True,
        imagenes=[img["src"]] if img and img.get("src") else [],
        extra={"uuid": uuid},
    )


def buscar(zonas: list[str], precio_max: int, paginas_max: int, pausa: float):
    for zona in zonas:
        print(f"  Habitaclia · {zona}")
        for pagina in range(1, paginas_max + 1):
            html = get_html(_url(zona, pagina, precio_max))
            if not html:
                break
            sopa = BeautifulSoup(html, "html.parser")
            contacto = contactos(html)
            for art in sopa.find_all("article"):
                a = _a_anuncio(art)
                if a:
                    c = contacto.get(a.extra["uuid"], {})
                    a.telefono, a.email = c.get("telefono", ""), c.get("email", "")
                    a.anunciante = c.get("anunciante", "")
                    yield a
            if not sopa.select_one(f'a[aria-label="Página {pagina + 1}"]'):
                break
            time.sleep(pausa)
        time.sleep(pausa)
