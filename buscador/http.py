import requests

UA_NAVEGADOR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
# Nominatim y OSRM piden identificarse con un User-Agent propio
UA_PROYECTO = "buscador-pisos-hospitalet/0.1 (uso personal)"

sesion = requests.Session()
sesion.headers.update({
    "User-Agent": UA_NAVEGADOR,
    "Accept-Language": "es-ES,es;q=0.9",
})


def get_html(url: str) -> str | None:
    """Devuelve el HTML o None si el portal responde con error o bloqueo."""
    try:
        r = sesion.get(url, timeout=30)
    except requests.RequestException as e:
        print(f"    ! error de red: {e}")
        return None
    if r.status_code != 200:
        print(f"    ! HTTP {r.status_code} en {url}")
        return None
    r.encoding = "utf-8"
    return r.text
