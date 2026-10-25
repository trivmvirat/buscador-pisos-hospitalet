import json
import sqlite3
from datetime import datetime

ESQUEMA = """
CREATE TABLE IF NOT EXISTS anuncios (
    id TEXT PRIMARY KEY,
    datos TEXT NOT NULL,
    precio INTEGER,
    precio_inicial INTEGER,
    primera_vez TEXT,
    ultima_vez TEXT
);
CREATE TABLE IF NOT EXISTS geocache (
    consulta TEXT PRIMARY KEY,
    lat REAL,
    lon REAL
);
CREATE TABLE IF NOT EXISTS rutas (
    clave TEXT PRIMARY KEY,
    segundos REAL
);
CREATE TABLE IF NOT EXISTS detalles (
    id TEXT PRIMARY KEY,
    datos TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notas (
    url TEXT PRIMARY KEY,
    texto TEXT NOT NULL,
    actualizada TEXT
);
"""
MAX_NOTA = 500


class BD:
    def __init__(self, ruta: str):
        self.con = sqlite3.connect(ruta)
        self.con.executescript(ESQUEMA)

    def guardar(self, anuncio: dict) -> str:
        """Inserta o actualiza. Devuelve 'nuevo', 'bajada' o 'visto'."""
        ahora = datetime.now().isoformat(timespec="seconds")
        fila = self.con.execute(
            "SELECT precio FROM anuncios WHERE id = ?", (anuncio["id"],)
        ).fetchone()
        datos = json.dumps(anuncio, ensure_ascii=False)
        if fila is None:
            self.con.execute(
                "INSERT INTO anuncios VALUES (?, ?, ?, ?, ?, ?)",
                (anuncio["id"], datos, anuncio["precio"], anuncio["precio"], ahora, ahora),
            )
            estado = "nuevo"
        else:
            self.con.execute(
                "UPDATE anuncios SET datos = ?, precio = ?, ultima_vez = ? WHERE id = ?",
                (datos, anuncio["precio"], ahora, anuncio["id"]),
            )
            estado = "bajada" if anuncio["precio"] < fila[0] else "visto"
        self.con.commit()
        return estado

    def info(self, id_: str) -> tuple[int, str]:
        """(precio_inicial, primera_vez) de un anuncio ya guardado."""
        return self.con.execute(
            "SELECT precio_inicial, primera_vez FROM anuncios WHERE id = ?", (id_,)
        ).fetchone()

    def geo_get(self, consulta):
        return self.con.execute(
            "SELECT lat, lon FROM geocache WHERE consulta = ?", (consulta,)
        ).fetchone()

    def geo_set(self, consulta, lat, lon):
        self.con.execute("INSERT OR REPLACE INTO geocache VALUES (?, ?, ?)", (consulta, lat, lon))
        self.con.commit()

    def detalle_get(self, id_):
        fila = self.con.execute("SELECT datos FROM detalles WHERE id = ?", (id_,)).fetchone()
        return json.loads(fila[0]) if fila else None

    def detalle_set(self, id_, datos: dict):
        self.con.execute(
            "INSERT OR REPLACE INTO detalles VALUES (?, ?)",
            (id_, json.dumps(datos, ensure_ascii=False)),
        )
        self.con.commit()

    def notas(self) -> dict[str, str]:
        return dict(self.con.execute("SELECT url, texto FROM notas").fetchall())

    def nota_set(self, url: str, texto: str):
        """Guarda la nota del piso (máx. 500 caracteres). Una nota vacía la borra."""
        texto = texto.strip()[:MAX_NOTA]
        if texto:
            self.con.execute(
                "INSERT OR REPLACE INTO notas VALUES (?, ?, ?)",
                (url, texto, datetime.now().isoformat(timespec="seconds")),
            )
        else:
            self.con.execute("DELETE FROM notas WHERE url = ?", (url,))
        self.con.commit()

    def ruta_get(self, clave):
        fila = self.con.execute("SELECT segundos FROM rutas WHERE clave = ?", (clave,)).fetchone()
        return fila[0] if fila else None

    def ruta_set(self, clave, segundos):
        self.con.execute("INSERT OR REPLACE INTO rutas VALUES (?, ?)", (clave, segundos))
        self.con.commit()
