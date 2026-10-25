"""Web (informe.html) con los pisos seleccionados: galería de fotos y todos los datos del anuncio."""
import html
import re
from datetime import datetime

CSS = """
:root { --bg:#f5f4f0; --card:#fff; --txt:#1d1d1b; --sub:#6b6a66; --line:#e2e0da; --chip:#efede8;
        --nuevo:#1f7a4d; --bajada:#b5541b; --acento:#2457c5; --aviso:#b3261e; --fav:#a66a00; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#151514; --card:#1f1f1d; --txt:#ecebe7; --sub:#a09f9a; --line:#34332f; --chip:#2a2a27;
          --nuevo:#5cc48d; --bajada:#f0915a; --acento:#8aaeff; --aviso:#ff8a80; --fav:#f2c14e; } }
* { box-sizing:border-box; }
body { margin:0; padding:24px 16px 48px; background:var(--bg); color:var(--txt);
       font:15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width:1150px; margin:0 auto; }
h1 { font-size:24px; margin:0 0 4px; }
.sub { color:var(--sub); margin:0 0 18px; }
.barra { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:18px; }
.barra button, .barra select { border:1px solid var(--line); background:var(--card); color:var(--txt);
  padding:6px 12px; border-radius:999px; cursor:pointer; font:inherit; }
.barra button[aria-pressed=true] { border-color:var(--acento); color:var(--acento); }
.lista { display:flex; flex-direction:column; gap:18px; }
.piso { background:var(--card); border:1px solid var(--line); border-radius:14px; overflow:hidden;
        display:grid; grid-template-columns:minmax(0, 1.25fr) minmax(0, 1fr); }
@media (max-width: 760px) { .piso { grid-template-columns:1fr; } }
.galeria { position:relative; background:#000; min-height:260px; }
.fotos { display:flex; overflow-x:auto; scroll-snap-type:x mandatory; height:100%; scrollbar-width:thin; }
.fotos img { flex:0 0 100%; width:100%; height:100%; max-height:440px; aspect-ratio:4/3; object-fit:cover;
             scroll-snap-align:start; cursor:zoom-in; }
.nav { position:absolute; top:50%; translate:0 -50%; border:0; width:36px; height:36px; border-radius:50%;
       background:rgba(0,0,0,.55); color:#fff; font-size:18px; cursor:pointer; }
.nav.prev { left:8px; } .nav.next { right:8px; }
.contador { position:absolute; bottom:8px; right:10px; background:rgba(0,0,0,.6); color:#fff;
            font-size:12px; padding:2px 8px; border-radius:999px; }
.sin-fotos { color:#aaa; display:grid; place-items:center; height:100%; min-height:260px; }
.datos { padding:16px 18px; display:flex; flex-direction:column; gap:8px; min-width:0; }
.cabeza { display:flex; justify-content:space-between; gap:12px; align-items:baseline; flex-wrap:wrap; }
.precio { font-size:24px; font-weight:700; }
.coche { font-weight:600; color:var(--acento); }
.titulo { font-weight:600; font-size:16px; margin:0; }
.lugar, .aprox { color:var(--sub); font-size:14px; }
.cifras { display:flex; gap:14px; flex-wrap:wrap; font-size:14px; }
.cifras b { font-size:16px; }
.chips { display:flex; gap:6px; flex-wrap:wrap; }
.chip { font-size:12px; padding:2px 9px; border-radius:999px; background:var(--chip); color:var(--sub); }
.chip.nuevo { background:transparent; border:1px solid var(--nuevo); color:var(--nuevo); }
.chip.bajada { background:transparent; border:1px solid var(--bajada); color:var(--bajada); }
.chip.aviso { background:transparent; border:1px solid var(--aviso); color:var(--aviso); font-weight:600; }
.nav-webs { display:flex; gap:14px; flex-wrap:wrap; margin:0 0 14px; font-size:14px; }
.nav-webs a { color:var(--acento); text-decoration:none; }
.nav-webs a[aria-current] { color:var(--txt); font-weight:700; }
details { font-size:14px; }
details summary { cursor:pointer; color:var(--acento); }
.desc { white-space:pre-line; margin:8px 0 0; color:var(--txt); max-height:320px; overflow:auto; }
.enlaces { display:flex; gap:10px; flex-wrap:wrap; margin-top:auto; padding-top:6px; }
.enlaces { align-items:center; }
.enlaces a { color:var(--acento); font-weight:600; text-decoration:none; }
.estrella { margin-left:auto; border:1px solid var(--line); background:transparent; color:var(--sub);
            padding:4px 10px; border-radius:999px; cursor:pointer; font:inherit; font-size:13px; }
.estrella:hover { border-color:var(--fav); color:var(--fav); }
.estrella.activa { border-color:var(--fav); color:var(--fav); font-weight:600; }
.estrella.activa:hover { background:color-mix(in srgb, var(--fav) 15%, transparent); }
.estrella:disabled { opacity:.5; cursor:wait; }
.estrella + .eliminar { margin-left:0; }
.eliminar { margin-left:auto; border:1px solid var(--line); background:transparent; color:var(--sub);
            padding:4px 10px; border-radius:999px; cursor:pointer; font:inherit; font-size:13px; }
.eliminar:hover { border-color:var(--aviso); color:var(--aviso); }
.eliminar:disabled { opacity:.45; cursor:not-allowed; }
.eliminar:disabled:hover { border-color:var(--line); color:var(--sub); }
/* Favoritos: borde luminoso para destacar los pisos buenos */
.piso.favorito { border:2px solid var(--fav);
  box-shadow:0 0 0 3px color-mix(in srgb, var(--fav) 35%, transparent),
             0 0 22px 4px color-mix(in srgb, var(--fav) 55%, transparent); }
.eliminar.confirmar { background:var(--aviso); border-color:var(--aviso); color:#fff; font-weight:600; }
.error-eliminar { color:var(--aviso); font-size:13px; margin:4px 0 0; }
.vacio { color:var(--sub); padding:40px 0; text-align:center; }
.notas label { display:flex; flex-direction:column; gap:4px; font-size:14px; font-weight:600; }
.notas textarea { font:inherit; font-weight:400; font-size:14px; color:var(--txt); background:var(--bg);
                  border:1px solid var(--line); border-radius:8px; padding:8px; resize:vertical; width:100%; }
.notas textarea:focus { outline:2px solid var(--acento); border-color:transparent; }
.notas-pie { display:flex; align-items:center; gap:10px; font-size:13px; color:var(--sub); margin-top:4px; }
.guardar-nota { border:1px solid var(--line); background:transparent; color:var(--acento); padding:3px 10px;
                border-radius:999px; cursor:pointer; font:inherit; font-size:13px; font-weight:600; }
.guardar-nota:disabled { opacity:.5; cursor:wait; }
.contacto { display:flex; gap:14px; flex-wrap:wrap; font-size:15px; }
.contacto a { color:var(--acento); font-weight:600; text-decoration:none; overflow-wrap:anywhere; }
dialog { border:0; padding:0; background:transparent; max-width:96vw; max-height:96vh; }
dialog::backdrop { background:rgba(0,0,0,.85); }
dialog img { max-width:96vw; max-height:92vh; display:block; }
"""

JS = """
document.querySelectorAll('.galeria').forEach(g => {
  const fotos = g.querySelector('.fotos'), cont = g.querySelector('.contador');
  if (!fotos) return;
  const total = fotos.children.length;
  const actual = () => Math.round(fotos.scrollLeft / fotos.clientWidth);
  const pinta = () => { if (cont) cont.textContent = (actual() + 1) + ' / ' + total; };
  fotos.addEventListener('scroll', pinta, { passive: true });
  g.querySelectorAll('.nav').forEach(b => b.addEventListener('click', () => {
    const i = Math.max(0, Math.min(total - 1, actual() + (b.classList.contains('next') ? 1 : -1)));
    fotos.scrollTo({ left: i * fotos.clientWidth, behavior: 'smooth' });
  }));
  pinta();
});
// Foto a pantalla completa
const dlg = document.querySelector('dialog'), grande = dlg.querySelector('img');
document.querySelectorAll('.fotos img').forEach(img => img.addEventListener('click', () => {
  grande.src = img.src; dlg.showModal();
}));
dlg.addEventListener('click', () => dlg.close());
// Filtro y orden
const lista = document.querySelector('.lista');
let filtro = 'todos';
document.querySelectorAll('[data-f]').forEach(b => b.addEventListener('click', () => {
  filtro = b.dataset.f;
  document.querySelectorAll('[data-f]').forEach(x => x.setAttribute('aria-pressed', x === b));
  lista.querySelectorAll('.piso').forEach(p => p.hidden = filtro === 'nuevos' && !p.dataset.nuevo);
}));
// Eliminar un piso de todas las webs (lo guarda servir.py en eliminados.json)
const contar = () => {
  const n = lista.querySelectorAll('.piso').length;
  const h1 = document.querySelector('h1');
  h1.textContent = h1.textContent.replace(/\\d+ pisos/, n + ' pisos');
  const todos = document.querySelector('[data-f="todos"]');
  todos.textContent = 'Todos (' + n + ')';
  const nuevos = document.querySelector('[data-f="nuevos"]');
  nuevos.textContent = 'Nuevos (' + lista.querySelectorAll('.piso[data-nuevo]').length + ')';
};
// Confirmación en el propio botón: algunos navegadores bloquean confirm() y alert()
const avisar = (piso, ref, texto) => {
  let aviso = piso.querySelector('.error-eliminar');
  if (!aviso) {
    aviso = document.createElement('p');
    aviso.className = 'error-eliminar';
    ref.closest('.enlaces').after(aviso);
  }
  aviso.textContent = texto;
};
// 📝 Notas de cada piso (servir.py las guarda en pisos.db)
lista.addEventListener('input', e => {
  const t = e.target.closest('.notas textarea');
  if (!t) return;
  const piso = t.closest('.piso');
  piso.querySelector('.cuenta').textContent = t.value.length + '/500';
  piso.querySelector('.estado-nota').textContent = 'Sin guardar';
});
lista.addEventListener('click', async e => {
  const g = e.target.closest('.guardar-nota');
  if (!g) return;
  const piso = g.closest('.piso');
  const estado = piso.querySelector('.estado-nota');
  g.disabled = true;
  estado.textContent = 'Guardando…';
  try {
    const r = await fetch('/api/nota', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: piso.dataset.url, texto: piso.querySelector('.notas textarea').value }),
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    estado.textContent = '✓ Guardada';
  } catch (err) {
    estado.textContent = 'No se pudo guardar: abre la web con «python servir.py» (' + err.message + ')';
  } finally {
    g.disabled = false;
  }
});
// ⭐ Añadir a favoritos (servir.py lo guarda en favoritos.json y regenera las webs)
lista.addEventListener('click', async e => {
  const s = e.target.closest('button.estrella');
  if (!s) return;
  const piso = s.closest('.piso');
  const activar = !s.classList.contains('activa');
  const antes = s.textContent;
  s.disabled = true;
  s.textContent = activar ? 'Marcando…' : 'Quitando…';
  try {
    const r = await fetch('/api/favorito', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: piso.dataset.url, activar }),
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    location.reload();
  } catch (err) {
    s.disabled = false;
    s.textContent = antes;
    avisar(piso, s, 'No se pudo cambiar la estrella. Abre la web con «python servir.py» en http://localhost:8765 (' + err.message + ').');
  }
});
lista.addEventListener('click', async e => {
  const b = e.target.closest('.eliminar');
  if (!b) return;
  const piso = b.closest('.piso');
  if (!b.classList.contains('confirmar')) {
    b.classList.add('confirmar');
    b.textContent = '¿Seguro? Pulsa otra vez';
    b._espera = setTimeout(() => { b.classList.remove('confirmar'); b.textContent = '🗑 Eliminar'; }, 4000);
    return;
  }
  clearTimeout(b._espera);
  b.disabled = true;
  b.textContent = 'Eliminando…';
  try {
    const r = await fetch('/api/eliminar', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: piso.dataset.url, titulo: b.dataset.titulo }),
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    piso.remove();
    contar();
  } catch (err) {
    b.disabled = false;
    b.classList.remove('confirmar');
    b.textContent = '🗑 Eliminar';
    avisar(piso, b, 'No se pudo eliminar. Abre la web con «python servir.py» en http://localhost:8765 (' + err.message + ').');
  }
});
document.querySelector('#orden').addEventListener('change', e => {
  const k = e.target.value;
  [...lista.children].sort((a, b) => (+a.dataset[k]) - (+b.dataset[k])).forEach(p => lista.appendChild(p));
});
"""


def _e(t) -> str:
    return html.escape(str(t if t is not None else ""))


def _telefono_bonito(tel: str) -> str:
    """+34910781711 -> 910 78 17 11 (formato habitual en España)."""
    n = tel.removeprefix("+34").removeprefix("0034")
    if len(n) == 9 and n.isdigit():
        return f"{n[:3]} {n[3:5]} {n[5:7]} {n[7:]}"
    return tel


def _ficha(a: dict) -> str:
    fotos = a.get("imagenes") or []
    if fotos:
        imgs = "".join(
            f'<img src="{_e(u)}" alt="Foto {i + 1}" loading="{"eager" if i == 0 else "lazy"}" referrerpolicy="no-referrer">'
            for i, u in enumerate(fotos)
        )
        nav = '<button class="nav prev" aria-label="Foto anterior">‹</button>' \
              '<button class="nav next" aria-label="Foto siguiente">›</button>' if len(fotos) > 1 else ""
        galeria = f'<div class="fotos">{imgs}</div>{nav}<span class="contador"></span>'
    else:
        galeria = '<div class="sin-fotos">Sin fotos</div>'

    cifras = []
    if a.get("habitaciones") is not None:
        cifras.append(f"<span><b>{a['habitaciones']}</b> hab.</span>")
    if a.get("banos"):
        cifras.append(f"<span><b>{a['banos']}</b> baño{'s' if a['banos'] != 1 else ''}</span>")
    if a.get("m2"):
        cifras.append(f"<span><b>{a['m2']}</b> m²</span>")
        cifras.append(f"<span><b>{a['precio'] / a['m2']:.1f}</b> €/m²</span>")
    if a.get("planta"):
        cifras.append(f"<span>{_e(a['planta'])}</span>")

    chips = []
    if a.get("aviso"):
        chips.append(f'<span class="chip aviso" title="{_e(a["aviso"])}">⚠️ {_e(a["aviso"])}</span>')
    if a["estado"] == "nuevo":
        chips.append('<span class="chip nuevo">Nuevo</span>')
    if a["precio"] < a.get("precio_inicial", a["precio"]):
        chips.append(f'<span class="chip bajada">Antes {a["precio_inicial"]} €</span>')
    chips += [f'<span class="chip">{_e(c)}</span>' for c in a.get("caracteristicas", [])]

    enlaces = [f'<a href="{_e(a["url"])}" target="_blank" rel="noopener">Ver en {_e(a["fuente"])} ↗</a>']
    enlaces += [
        f'<a href="{_e(u)}" target="_blank" rel="noopener">{_e(f)} ↗</a>'
        for f, u in a.get("tambien_en", [])
    ]
    desc = a.get("descripcion") or ""
    bloque_desc = f"<details><summary>Descripción del anuncio</summary><p class=\"desc\">{_e(desc)}</p></details>" if desc else ""
    anunciante = f'<div class="lugar">Anunciante: {_e(a["anunciante"])}</div>' if a.get("anunciante") else ""
    contacto = []
    tel = re.sub(r"[^\d+]", "", a.get("telefono") or "")
    # Algunas plataformas (p. ej. Spotahome) publican +34 910 000 000 como relleno
    if tel and not re.search(r"0{6}$", tel):
        contacto.append(f'<a href="tel:{_e(tel)}">📞 {_e(_telefono_bonito(tel))}</a>')
    # Buzones automáticos de reenvío, no de una persona
    if a.get("email") and "robot.zapier.com" not in a["email"]:
        contacto.append(f'<a href="mailto:{_e(a["email"])}">✉️ {_e(a["email"])}</a>')
    if contacto:
        anunciante += f'<div class="contacto">{"".join(contacto)}</div>'
    aprox = '<div class="aprox">Ubicación aproximada (por barrio)</div>' if a.get("coords_aprox") else ""
    lugar = ", ".join(x for x in (a.get("barrio"), a.get("municipio")) if x)

    # Solo los marcados con ⭐ tienen el botón 🗑 bloqueado: no se pueden eliminar
    if a.get("estrella"):
        enlaces.append('<button class="estrella activa" type="button" title="Quitar la estrella">★ Favorito</button>')
        enlaces.append('<button class="eliminar" type="button" disabled '
                       'title="Los favoritos no se pueden eliminar">🔒 Eliminar</button>')
    else:
        enlaces.append('<button class="estrella" type="button" title="Añadir a favoritos">☆ Favorito</button>')
        enlaces.append(f'<button class="eliminar" type="button" data-titulo="{_e(a["titulo"])}">🗑 Eliminar</button>')

    return f"""<article class="piso{' favorito' if a.get('estrella') else ''}" data-url="{_e(a['url'])}" data-min="{a['minutos_coche']:.1f}" data-precio="{a['precio']}"{' data-nuevo="1"' if a['estado'] == 'nuevo' else ''}>
  <div class="galeria">{galeria}</div>
  <div class="datos">
    <div class="cabeza"><span class="precio">{a['precio']} €/mes</span>
      <span class="coche">🚗 {a['minutos_coche']:.0f} min</span></div>
    <h2 class="titulo">{_e(a['titulo'])}</h2>
    <div class="lugar">{_e(lugar)}</div>{aprox}
    <div class="cifras">{''.join(cifras)}</div>
    <div class="chips">{''.join(chips)}</div>
    {anunciante}
    {bloque_desc}
    <div class="notas">
      <label>📝 Mis notas
        <textarea maxlength="500" rows="3" placeholder="Visita, dudas, qué te han contestado…">{_e(a.get('nota', ''))}</textarea>
      </label>
      <div class="notas-pie"><span class="cuenta">{len(a.get('nota', ''))}/500</span>
        <button class="guardar-nota" type="button">Guardar nota</button><span class="estado-nota"></span></div>
    </div>
    <div class="enlaces">{''.join(enlaces)}</div>
  </div>
</article>"""


WEBS = [("informe.html", "Todos"), ("favoritos.html", "Mi selección")]


def generar(anuncios: list[dict], cfg: dict, ruta: str, titulo: str | None = None):
    f = cfg["filtros"]
    actual = ruta.replace("\\", "/").rsplit("/", 1)[-1]
    nav = "".join(
        f'<a href="{w}"{" aria-current=page" if w == actual else ""}>{n}</a>' for w, n in WEBS
    )
    cabecera = titulo or f"{len(anuncios)} pisos a {f['minutos_coche_max']} min o menos en coche"
    nuevos = sum(1 for a in anuncios if a["estado"] == "nuevo")
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
    fuentes = sorted({a["fuente"] for a in anuncios})
    fichas = "\n".join(_ficha(a) for a in anuncios) or '<p class="vacio">Ningún piso cumple los filtros.</p>'
    doc = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>{_e(titulo.split(" · ")[0] if titulo else "Pisos en alquiler")}</title><style>{CSS}</style></head>
<body><main>
<nav class="nav-webs">{nav}</nav>
<h1>{_e(cabecera)}</h1>
<p class="sub">Hasta {f['precio_max']} €/mes · desde {_e(cfg['origen']['direccion'])} ·
tiempo estimado con tráfico (×{f['factor_trafico']}) · {_e(', '.join(fuentes))} · actualizado {ahora}</p>
<div class="barra">
  <button data-f="todos" aria-pressed="true">Todos ({len(anuncios)})</button>
  <button data-f="nuevos" aria-pressed="false">Nuevos ({nuevos})</button>
  <select id="orden" aria-label="Ordenar">
    <option value="min">Más cerca primero</option>
    <option value="precio">Más barato primero</option>
  </select>
</div>
<div class="lista">
{fichas}
</div>
</main>
<dialog><img alt=""></dialog>
<script>{JS}</script></body></html>"""
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(doc)
