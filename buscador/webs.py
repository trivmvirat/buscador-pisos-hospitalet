"""Genera informe.html (Todos) y favoritos.html (Mi selección) y gestiona favoritos y eliminados.

Lo usan buscar.py (tras cada búsqueda) y servir.py (al pulsar ⭐ o 🗑 en la web).
"""
import json
import re
from datetime import date, datetime
from pathlib import Path

from . import informe
from .db import BD

RAIZ = Path(__file__).resolve().parent.parent
RUTA_FAV = RAIZ / "favoritos.json"
RUTA_ELIM = RAIZ / "eliminados.json"


def _leer(ruta: Path, defecto):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else defecto


def _escribir(ruta: Path, datos):
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")


def favoritos() -> dict[str, dict]:
    return {p["url"]: p for p in _leer(RUTA_FAV, {"pisos": []})["pisos"]}


def urls_eliminadas() -> set[str]:
    return {e["url"] for e in _leer(RUTA_ELIM, [])}


def _urls(d: dict) -> list[str]:
    # El mismo piso puede estar en varios portales
    return [d["url"]] + [u for _, u in d.get("tambien_en", [])]


def generar(filas: list[dict], cfg: dict, bd: BD) -> tuple[int, int]:
    """Escribe las dos webs. Devuelve (pisos en total, favoritos)."""
    fav = favoritos()
    notas = bd.notas()
    elegidos = []
    for d in filas:
        d["nota"] = next((notas[u] for u in _urls(d) if u in notas), "")
        f = next((fav[u] for u in _urls(d) if u in fav), None)
        d["favorito"] = f is not None
        # Solo los marcados con ⭐ llevan borde luminoso y no se pueden eliminar
        d["estrella"] = bool(f and f.get("estrella"))
        d["aviso"] = f.get("aviso", "") if f else ""
        if f:
            elegidos.append(d)
    informe.generar(filas, cfg, str(RAIZ / "informe.html"))
    informe.generar(elegidos, cfg, str(RAIZ / "favoritos.html"), f"Mi selección · {len(elegidos)} pisos")
    return len(filas), len(elegidos)


def filas_actuales(bd: BD) -> list[dict]:
    """Los pisos que muestra ahora informe.html, con sus datos guardados en pisos.db."""
    texto = (RAIZ / "informe.html").read_text(encoding="utf-8")
    import html as _html
    en_web = [
        (_html.unescape(m.group(1)), bool(m.group(2)))
        for m in re.finditer(r'<article class="piso[^"]*" data-url="([^"]+)"[^>]*?( data-nuevo="1")?>', texto)
    ]
    por_url = {}
    for (datos,) in bd.con.execute("SELECT datos FROM anuncios"):
        d = json.loads(datos)
        por_url[d["url"]] = d
    filas = []
    for url, nuevo in en_web:
        d = por_url.get(url)
        if not d:
            continue
        d["estado"] = "nuevo" if nuevo else "visto"
        d["precio_inicial"], d["primera_vez"] = bd.info(d["id"])
        filas.append(d)
    return filas


def anadir_favorito(url: str, bd: BD, cfg: dict) -> bool:
    """Marca el piso con ⭐ (lo añade a favoritos.json si no estaba) y regenera las webs.

    Devuelve False si ya estaba marcado.
    """
    fav = _leer(RUTA_FAV, {"pisos": []})
    filas = filas_actuales(bd)
    d = next((x for x in filas if url in _urls(x)), None)
    if d is None:
        raise ValueError("Ese piso no está en la web")
    urls = set(_urls(d))
    entrada = next((p for p in fav["pisos"] if p["url"] in urls), None)
    if entrada and entrada.get("estrella"):
        return False
    if entrada is None:
        entrada = {
            "titulo": d["titulo"], "url": d["url"], "precio": d["precio"],
            "minutos_coche": round(d["minutos_coche"], 1), "anadido": date.today().isoformat(),
        }
        fav["pisos"].append(entrada)
    entrada["estrella"] = True
    _escribir(RUTA_FAV, fav)
    generar(filas, cfg, bd)
    return True


def guardar_nota(url: str, texto: str, bd: BD, cfg: dict):
    """Guarda la nota del piso en pisos.db (tabla notas) y regenera las webs."""
    filas = filas_actuales(bd)
    d = next((x for x in filas if url in _urls(x)), None)
    if d is None:
        raise ValueError("Ese piso no está en la web")
    bd.nota_set(d["url"], texto)
    generar(filas, cfg, bd)


def eliminar(url: str, titulo: str, bd: BD, cfg: dict):
    """Elimina el piso por completo: de las webs, de la base de datos local y de la caché.

    Queda apuntado en eliminados.json para que no vuelva en próximas búsquedas y sale de
    favoritos.json. Los marcados con ⭐ no se pueden eliminar (lanza PermissionError).
    """
    filas = filas_actuales(bd)
    d = next((x for x in filas if url in _urls(x)), None)
    urls = set(_urls(d)) if d else {url}
    fav = _leer(RUTA_FAV, {"pisos": []})
    if any(p.get("estrella") for p in fav["pisos"] if p["url"] in urls):
        raise PermissionError("Los favoritos marcados con ⭐ no se pueden eliminar")
    if any(p["url"] in urls for p in fav["pisos"]):
        fav["pisos"] = [p for p in fav["pisos"] if p["url"] not in urls]
        _escribir(RUTA_FAV, fav)

    # Habitaclia y Fotocasa comparten anuncios con el mismo uuid y distinta URL:
    # se eliminan todas las copias para que no vuelva por el otro portal
    cache = RAIZ / "cache" / "portales.json"
    anuncios_cache = _leer(cache, [])
    uuids = {(a.get("extra") or {}).get("uuid") for a in anuncios_cache if a["url"] in urls} - {None}
    urls |= {a["url"] for a in anuncios_cache if (a.get("extra") or {}).get("uuid") in uuids}

    elim = _leer(RUTA_ELIM, [])
    ya = {e["url"] for e in elim}
    for u in urls - ya:
        elim.append({"url": u, "titulo": titulo, "fecha": datetime.now().isoformat(timespec="seconds")})
    _escribir(RUTA_ELIM, elim)

    # Borrado local: base de datos y caché de la última búsqueda
    for (id_, datos) in bd.con.execute("SELECT id, datos FROM anuncios").fetchall():
        if json.loads(datos)["url"] in urls:
            bd.con.execute("DELETE FROM anuncios WHERE id = ?", (id_,))
            bd.con.execute("DELETE FROM detalles WHERE id = ?", (id_,))
    bd.con.commit()
    if cache.exists():
        _escribir(cache, [a for a in anuncios_cache if a["url"] not in urls])

    generar([x for x in filas if not set(_urls(x)) & urls], cfg, bd)
