"""Sirve las webs en http://localhost:8765 y atiende los botones ⭐ Favorito y 🗑 Eliminar.

Uso:
    python servir.py

POST /api/favorito {"url": ..., "activar": true | false}
  - true: lo marca con ⭐ en favoritos.json (borde luminoso, no se puede eliminar)
  - false: quita la ⭐; el piso sigue en la selección
POST /api/nota {"url": ..., "texto": ...}
  - guarda la nota del piso (máx. 500 caracteres) en pisos.db, tabla notas
POST /api/eliminar {"url": ..., "titulo": ...}
  - lo apunta en eliminados.json (buscar.py ya no lo volverá a mostrar)
  - lo borra de la base de datos local (pisos.db) y de la caché
  - regenera las webs
  - los favoritos no se pueden eliminar (responde 403)
"""
import json
import threading
import tomllib
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from buscador import webs
from buscador.db import BD

RAIZ = Path(__file__).parent
PUERTO = 8765
bloqueo = threading.Lock()


def _config():
    return tomllib.loads((RAIZ / "config.toml").read_text(encoding="utf-8"))


class Manejador(SimpleHTTPRequestHandler):
    def _responder(self, codigo: int, datos: dict):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_POST(self):
        if self.path not in ("/api/eliminar", "/api/favorito", "/api/nota"):
            self.send_error(404)
            return
        try:
            largo = int(self.headers.get("Content-Length", 0))
            datos = json.loads(self.rfile.read(largo) or b"{}")
            url = str(datos["url"])
        except (ValueError, KeyError):
            self._responder(400, {"error": "Falta la url"})
            return
        try:
            with bloqueo:
                bd = BD(str(RAIZ / "pisos.db"))
                if self.path == "/api/favorito":
                    if datos.get("activar", True):
                        nuevo = webs.anadir_favorito(url, bd, _config())
                        print(f"⭐ {'marcado' if nuevo else '(ya lo estaba)'}: {url}")
                    else:
                        webs.quitar_estrella(url, bd, _config())
                        print(f"⭐ desmarcado: {url}")
                elif self.path == "/api/nota":
                    webs.guardar_nota(url, str(datos.get("texto", "")), bd, _config())
                    print(f"Nota guardada: {url}")
                else:
                    webs.eliminar(url, str(datos.get("titulo", "")), bd, _config())
                    print(f"Eliminado: {datos.get('titulo', '')} · {url}")
        except PermissionError as e:
            self._responder(403, {"error": str(e)})
            return
        except ValueError as e:
            self._responder(404, {"error": str(e)})
            return
        self._responder(200, {"ok": True})

    def end_headers(self):
        # Que el navegador no muestre una versión vieja de la web tras un cambio
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), partial(Manejador, directory=str(RAIZ)))
    print(f"Webs en http://localhost:{PUERTO}/informe.html  (Ctrl+C para parar)")
    servidor.serve_forever()
