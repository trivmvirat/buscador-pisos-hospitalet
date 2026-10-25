# Buscador de pisos de alquiler · L'Hospitalet de Llobregat

Busca pisos de alquiler en varios portales y se queda con los que están a **20 minutos o
menos en coche** de Avinguda del Carrilet 3, Edifici D (L'Hospitalet). El precio máximo es **1.200 €/mes**.
El resultado es una web, `informe.html`, con todas las fotos y los datos de cada piso.

## Cómo se usa

```bash
pip install -r requirements.txt
```

```bash
python buscar.py
```

Al terminar, abre `informe.html` en el navegador. Cada búsqueda guarda los pisos en `pisos.db`,
así que en la siguiente se marcan como **Nuevo** los que no estaban y se avisa de las bajadas de precio.

Los filtros (precio, habitaciones, m², minutos, factor de tráfico, municipios) están en `config.toml`.

## Arrancar la web (Visual Studio Code)

`python servir.py` (o **F5 → «Arrancar webs de pisos»** en VS Code) levanta la web y abre tu
selección en el navegador. No busca en los portales: solo muestra tus pisos y atiende ⭐, 🗑 y notas.
Para buscar pisos nuevos, ejecuta `python buscar.py` una vez cuando quieras.

### En otro ordenador

Tus datos (favoritos, notas, eliminados, contactados, base de datos) **no están en GitHub**.
Cópialos desde el ordenador original: descomprime `mis-datos-pisos.zip` dentro de la carpeta del
proyecto y luego ejecuta `python servir.py`.

## Webs que genera

- `informe.html`: todos los pisos que cumplen los filtros.
- `favoritos.html`: solo los de `favoritos.json` (tu selección). Los posibles anuncios falsos llevan un aviso ⚠️.

Las dos se enlazan entre sí desde arriba y se regeneran en cada `python buscar.py`.

Cada piso tiene:

- **☆ / ★ Favorito**: se activa y desactiva con un clic. Marcado con ★ lleva un borde dorado
  luminoso y su botón 🗑 queda bloqueado (🔒): no se puede eliminar.
- **🗑 Eliminar**: dos clics. Lo borra de las webs, de `pisos.db` y de la caché (también sus copias
  en otros portales) y lo apunta en `eliminados.json` para que no vuelva.
- **📝 Mis notas**: hasta 500 caracteres, guardadas en `pisos.db` (tabla `notas`).

Estos botones necesitan el servidor local (no funcionan abriendo el archivo con doble clic):

```bash
python servir.py
```

Y entra en http://localhost:8765/informe.html. Al eliminar un piso desaparece de las dos webs, sale de
`favoritos.json` y se apunta en `eliminados.json`, así que no vuelve a salir en próximas búsquedas.
Para recuperarlo, borra su entrada de `eliminados.json` y vuelve a ejecutar `buscar.py`.
Un piso se añade a la selección por la URL de su anuncio en `favoritos.json`.

## Portales

| Portal | Cómo se lee | Ubicación |
|---|---|---|
| Fotocasa | `buscar.py` directamente | exacta |
| Habitaclia | `buscar.py` + ficha de cada piso | exacta (de la ficha) |
| pisos.com | `buscar.py` + ficha de cada piso | exacta (de la ficha) |
| Idealista | desde Chrome (`chrome/extractor.js`) | calle/barrio (aproximada) |
| yaencontre | desde Chrome (`chrome/extractor.js`) | exacta (de la ficha) |
| Wolorent | desde Chrome (`chrome/extractor.js`) | barrio (aproximada) |

Idealista, yaencontre y Wolorent bloquean las peticiones automáticas. Por eso se leen desde
tu Chrome (lo hace Claude con la extensión de Chrome) y se guardan en `entrada/`:

1. `entrada/<portal>.json`: los resultados de las búsquedas de `[chrome].urls` en `config.toml`.
2. `buscar.py` deja en `entrada/fichas_pendientes.txt` las fichas de esos portales que todavía no tiene.
3. Esas fichas (todas las fotos, descripción, características) se guardan en `entrada/detalles/<portal>.json`.
4. `python buscar.py --sin-portales` vuelve a generar la web sin repetir la búsqueda en los
   portales directos (usa `cache/portales.json`).

Se pide a Claude, por ejemplo: *«actualiza los pisos de Idealista y yaencontre desde Chrome
y regenera el informe»*.

## Cómo se calcula el tiempo en coche

- Geocodificación con Nominatim y rutas con OSRM (ambos de OpenStreetMap, gratuitos).
- OSRM da el tiempo **sin tráfico**; se multiplica por `factor_trafico` (1,3) para aproximar la hora punta.
- Si la ubicación es aproximada (solo el barrio), en la primera criba se dan 5 minutos de margen.
  Después se recalcula con la ubicación de la ficha.
- Se descartan los alquileres de temporada (`excluir_temporales = true`).

## Estructura

```
buscar.py              script principal
config.toml            filtros, municipios y URLs
buscador/fuentes/      lectores de Fotocasa, Habitaclia, pisos.com y de entrada/ (Chrome)
buscador/detalles.py   fichas completas (fotos, descripción, coordenadas)
buscador/geo.py        geocodificación y minutos en coche
buscador/informe.py    genera informe.html
chrome/extractor.js    lector de Idealista / yaencontre / Wolorent para Chrome
```

Uso personal: hay pausas entre peticiones para no cargar los portales. Las webs pueden cambiar
su estructura; si un portal deja de devolver anuncios, el script lo indica en la salida.
