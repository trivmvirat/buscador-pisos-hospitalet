"""Buscador de pisos de alquiler cerca de L'Hospitalet de Llobregat.

Uso:
    python buscar.py               # busca en todos los portales y genera informe.html
    python buscar.py --sin-portales  # solo reprocesa lo leído desde Chrome (entrada/)
"""
import argparse
import json
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

from buscador import detalles, geo, webs
from buscador.db import BD
from buscador.fuentes import FUENTES, chrome
from buscador.modelo import Anuncio

RAIZ = Path(__file__).parent
# Con ubicación por barrio el error puede ser de varios minutos: se deja pasar
# con margen y se recalcula con la ficha (coordenadas exactas) cuando la hay
MARGEN_APROX_MIN = 5
# Alquiler de temporada aunque el portal no lo marque
RE_TEMPORADA = re.compile(
    r"(?<!larga )temporada|temporal|temporary|por meses|estancia m[ií]nima|estudiantes|vacacional"
    r"|32\)? d[ií]as|treinta y dos|1[01] meses|once meses|inferiores a \d+ meses"
)


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    t = "".join(c for c in t if c.isalnum())
    # "L'Hospitalet de Llobregat" y "Hospitalet de Llobregat" son el mismo municipio
    return t.removeprefix("l") if t.startswith("lhospitalet") else t


def recoger(cfg, sin_portales: bool) -> list[Anuncio]:
    f, red = cfg["filtros"], cfg["red"]
    cache = RAIZ / "cache" / "portales.json"
    if sin_portales and cache.exists():
        directos = [Anuncio(**d) for d in json.loads(cache.read_text(encoding="utf-8"))]
        print(f"  {len(directos)} anuncios de la última búsqueda en portales (cache)")
    else:
        directos = []
        for nombre, fuente in FUENTES.items():
            c = cfg["fuentes"].get(nombre, {})
            if c.get("activa"):
                directos += fuente.buscar(c["municipios"], f["precio_max"], red["paginas_max"], red["pausa_segundos"])
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps([a.to_dict() for a in directos], ensure_ascii=False), encoding="utf-8")
    return directos + list(chrome.cargar(RAIZ / "entrada"))


def favoritos_guardados(bd, todos) -> list[Anuncio]:
    """Favoritos que hoy no salen en los portales: se muestran con los datos guardados en pisos.db."""
    vistos = {a.url for a in todos}
    faltan = set(webs.favoritos()) - vistos
    campos = Anuncio.__dataclass_fields__
    guardados = []
    for (datos,) in bd.con.execute("SELECT datos FROM anuncios"):
        d = json.loads(datos)
        if d["url"] in faltan:
            a = Anuncio(**{k: v for k, v in d.items() if k in campos})
            # Las copias de otros portales se guardan como dict: se vuelven a unir en deduplicar()
            a.extra = {k: v for k, v in a.extra.items() if k not in ("duplicados", "tambien_en")}
            guardados.append(a)
    if guardados:
        print(f"  {len(guardados)} favoritos no salen hoy en los portales: se usan sus datos guardados")
    return guardados


def pasa_filtros(a, f) -> bool:
    if not (f["precio_min"] <= a.precio <= f["precio_max"]):
        return False
    # Los favoritos los ha elegido el usuario: no se descartan por el texto del anuncio
    if a.url not in webs.favoritos():
        texto = f"{a.titulo} {a.anunciante} {a.url} {a.descripcion}".lower()
        if f["excluir_temporales"] and (a.temporal or RE_TEMPORADA.search(texto)):
            return False
        if any(x.lower() in texto for x in f.get("excluir_anunciantes", [])):
            return False
    if f["habitaciones_min"] and (a.habitaciones or 0) < f["habitaciones_min"]:
        return False
    if f["m2_min"] and a.m2 and a.m2 < f["m2_min"]:
        return False
    return True


def deduplicar(anuncios):
    """Une el mismo piso publicado en varios portales; se queda con el de coordenadas exactas."""
    anuncios.sort(key=lambda a: (a.coords_aprox, -len(a.imagenes)))
    vistos, unicos = {}, []
    for a in anuncios:
        claves = []
        if a.extra.get("uuid"):
            claves.append(("uuid", a.extra["uuid"]))
        if a.m2:
            claves.append(("datos", a.precio, a.m2, a.habitaciones, _norm(a.municipio)))
        previo = next((vistos[k] for k in claves if k in vistos), None)
        if previo:
            if a.fuente != previo.fuente:
                previo.extra.setdefault("tambien_en", []).append((a.fuente, a.url))
            previo.extra.setdefault("duplicados", []).append(a)
            continue
        for k in claves:
            vistos[k] = a
        unicos.append(a)
    return unicos


def fusionar(a):
    """Completa un anuncio con lo mejor de sus copias en otros portales."""
    for d in a.extra.get("duplicados", []):
        if len(d.imagenes) > len(a.imagenes):
            a.imagenes = d.imagenes
        if len(d.descripcion) > len(a.descripcion):
            a.descripcion = d.descripcion
        if len(d.caracteristicas) > len(a.caracteristicas):
            a.caracteristicas = d.caracteristicas
        if a.coords_aprox and not d.coords_aprox and d.lat is not None:
            a.lat, a.lon, a.coords_aprox = d.lat, d.lon, False
        a.temporal = a.temporal or d.temporal
        a.anunciante = a.anunciante or d.anunciante
        a.telefono = a.telefono or d.telefono
        a.email = a.email or d.email
        a.planta = a.planta or d.planta


def calcular_minutos(bd, cfg, anuncios):
    origen = (cfg["origen"]["lat"], cfg["origen"]["lon"])
    sin_coords = [a for a in anuncios if a.lat is None]
    if sin_coords:
        print(f"Ubicando {len(sin_coords)} anuncios por barrio…")
    for a in sin_coords:
        c = geo.geocodificar(bd, a.barrio, a.municipio) or geo.geocodificar(bd, "", a.municipio)
        if c:
            a.lat, a.lon = c
    con_coords = [a for a in anuncios if a.lat is not None]
    minutos = geo.minutos_en_coche(bd, origen, [(a.lat, a.lon) for a in con_coords])
    for a, m in zip(con_coords, minutos):
        a.minutos_coche = None if m is None else m * cfg["filtros"]["factor_trafico"]


def dentro(a, maximo, margen=0) -> bool:
    return a.minutos_coche is not None and a.minutos_coche <= maximo + (margen if a.coords_aprox else 0)


def quitar_eliminados(anuncios):
    """Descarta los pisos borrados con el botón «Eliminar» de la web (eliminados.json)."""
    ruta = RAIZ / "eliminados.json"
    if not ruta.exists():
        return anuncios
    eliminados = {e["url"] for e in json.loads(ruta.read_text(encoding="utf-8"))}
    quedan = [
        a for a in anuncios
        if not ({a.url} | {u for _, u in a.extra.get("tambien_en", [])}) & eliminados
    ]
    if len(quedan) < len(anuncios):
        print(f"  {len(anuncios) - len(quedan)} pisos eliminados desde la web no se muestran")
    return quedan


def avisar_favoritos_perdidos(filas: list[dict]):
    vistos = {u for d in filas for u in [d["url"]] + [x for _, x in d.get("tambien_en", [])]}
    perdidos = [p["titulo"] for u, p in webs.favoritos().items() if u not in vistos]
    if perdidos:
        print(f"  ! {len(perdidos)} favoritos ya no aparecen en la búsqueda (¿retirados?): {perdidos}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--sin-portales", action="store_true", help="no consultar portales, solo entrada/")
    p.add_argument("--sin-fichas", action="store_true", help="no descargar fichas nuevas (vista rápida)")
    p.add_argument("--config", default=str(RAIZ / "config.toml"))
    args = p.parse_args()

    cfg = tomllib.loads(Path(args.config).read_text(encoding="utf-8"))
    f = cfg["filtros"]
    bd = BD(str(RAIZ / "pisos.db"))

    print("Buscando anuncios…")
    todos = recoger(cfg, args.sin_portales)
    todos += favoritos_guardados(bd, todos)
    candidatos = deduplicar([a for a in todos if pasa_filtros(a, f)])
    print(f"{len(todos)} anuncios leídos · {len(candidatos)} cumplen precio/tipo (sin duplicados)")
    candidatos = quitar_eliminados(candidatos)

    calcular_minutos(bd, cfg, candidatos)
    cerca = [a for a in candidatos if dentro(a, f["minutos_coche_max"], MARGEN_APROX_MIN)]
    print(f"{len(cerca)} a menos de {f['minutos_coche_max']} min (+{MARGEN_APROX_MIN} de margen si la ubicación es aproximada)")

    print("Completando fichas (fotos, descripción, ubicación exacta)…")
    copias = [d for a in cerca for d in a.extra.get("duplicados", [])]
    faltan = detalles.completar(cerca + copias, bd, RAIZ / "entrada" / "detalles", cfg["red"]["pausa_segundos"],
                                descargar=not args.sin_fichas)
    for a in cerca:
        fusionar(a)
    calcular_minutos(bd, cfg, cerca)  # con las coordenadas exactas de las fichas
    # La ficha puede revelar que es de temporada aunque el listado no lo dijera
    seleccion = sorted(
        (a for a in cerca if dentro(a, f["minutos_coche_max"]) and pasa_filtros(a, f)),
        key=lambda a: a.minutos_coche,
    )

    filas = []
    for a in seleccion:
        d = a.to_dict()
        d["tambien_en"] = a.extra.get("tambien_en", [])
        d["estado"] = bd.guardar(d)
        d["precio_inicial"], d["primera_vez"] = bd.info(a.id)
        filas.append(d)

    ruta = RAIZ / "informe.html"
    total, n_fav = webs.generar(filas, cfg, bd)
    print(f"Favoritos: {n_fav} en favoritos.html")
    avisar_favoritos_perdidos(filas)
    nuevos = [d for d in filas if d["estado"] == "nuevo"]
    print(f"\n{len(filas)} pisos seleccionados · {len(nuevos)} nuevos · informe: {ruta}")
    for d in nuevos:
        print(f"  NUEVO {d['precio']} € · {d['minutos_coche']:.0f} min · {d['titulo']} · {d['url']}")
    if faltan:
        print(f"\n{len(faltan)} fichas de portales de Chrome sin leer todavía (solo tienen 1 foto):")
        for a in faltan:
            print(f"  {a.id} · {a.url}")
        (RAIZ / "entrada" / "fichas_pendientes.txt").write_text(
            "\n".join(f"{a.id}\t{a.url}" for a in faltan), encoding="utf-8")


if __name__ == "__main__":
    main()
