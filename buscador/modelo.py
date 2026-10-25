from dataclasses import dataclass, field, asdict


@dataclass
class Anuncio:
    id: str                      # "<fuente>:<id del portal>"
    fuente: str
    titulo: str
    url: str
    precio: int
    municipio: str = ""
    barrio: str = ""
    habitaciones: int | None = None
    banos: int | None = None
    m2: int | None = None
    lat: float | None = None
    lon: float | None = None
    coords_aprox: bool = False   # True si la ubicación se ha deducido del barrio
    temporal: bool = False
    imagenes: list[str] = field(default_factory=list)
    descripcion: str = ""
    planta: str = ""
    caracteristicas: list[str] = field(default_factory=list)
    anunciante: str = ""
    telefono: str = ""
    email: str = ""
    minutos_coche: float | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
