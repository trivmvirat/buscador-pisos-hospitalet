// Lector de Idealista, yaencontre y Wolorent desde Chrome (estos portales bloquean
// las peticiones automáticas, pero no al navegador del usuario).
//
// Uso (lo hace Claude con la extensión de Chrome): abrir cualquier página del portal,
// pegar este fichero en la consola y llamar a
//   await piso.listas([url1, url2, ...])   -> { portal, fecha, anuncios: [...] }
//   await piso.fichas([url1, url2, ...])   -> { "<portal>:<id>": {imagenes, descripcion, ...} }
// Las URLs deben ser del mismo portal que la pestaña. El resultado se guarda en
// entrada/<portal>.json y entrada/detalles/<portal>.json para que lo procese buscar.py.
window.piso = (() => {
  const num = (t) => {
    const m = (t || "").match(/\d[\d.]*/);
    return m ? parseInt(m[0].replace(/\./g, ""), 10) : null;
  };
  const busca = (re, t) => {
    const m = (t || "").match(re);
    return m ? num(m[1]) : null;
  };
  const limpio = (t) => (t || "").replace(/\s+/g, " ").trim();
  const temporal = (t) => /alquiler temporal|temporada|meses m[aá]ximo|estancia m[ií]nima|estudiantes/i.test(t || "");
  const espera = (ms) => new Promise((r) => setTimeout(r, ms));
  const host = location.hostname;
  const portal = host.includes("idealista") ? "idealista" : host.includes("yaencontre") ? "yaencontre"
    : host.includes("wolorent") ? "wolorent" : null;

  async function descargar(url) {
    const r = await fetch(url, { credentials: "include" });
    if (!r.ok) throw new Error(`HTTP ${r.status} en ${url}`);
    const html = await r.text();
    return { html, doc: new DOMParser().parseFromString(html, "text/html") };
  }

  // ---------- Páginas de resultados ----------
  const lista = {
    idealista(doc) {
      const anuncios = [...doc.querySelectorAll("article.item[data-element-id]")].map((a) => {
        const link = a.querySelector("a.item-link");
        const det = [...a.querySelectorAll(".item-detail")].map((x) => limpio(x.textContent));
        const titulo = limpio(link?.textContent);
        // "Estudio en Calle de Pujós, Collblanc, Hospitalet de Llobregat"
        const partes = titulo.replace(/^.*? en /, "").split(", ");
        const desc = limpio(a.querySelector(".item-description")?.textContent);
        const img = a.querySelector("img");
        return {
          id: a.dataset.elementId,
          titulo,
          url: `https://www.idealista.com/inmueble/${a.dataset.elementId}/`,
          precio: num(a.querySelector(".item-price")?.textContent),
          municipio: partes.length > 1 ? partes[partes.length - 1] : "",
          barrio: partes.slice(0, -1).join(", "),
          habitaciones: det.some((d) => /hab/.test(d)) ? num(det.find((d) => /hab/.test(d))) : null,
          m2: num(det.find((d) => /m²/.test(d))),
          planta: det.find((d) => /planta|bajo|exterior|interior/i.test(d)) || "",
          imagen: (img?.getAttribute("src") || img?.dataset.src || "").split("?")[0],
          temporal: temporal(desc),
          texto: desc,
        };
      });
      const sig = doc.querySelector(".pagination li.next a");
      return { anuncios, siguiente: sig ? new URL(sig.getAttribute("href"), location.origin).href : null };
    },

    yaencontre(doc) {
      const anuncios = [...doc.querySelectorAll("article")].map((a) => {
        const link = [...a.querySelectorAll("a")].find((x) => /\/inmueble-/.test(x.getAttribute("href") || ""));
        if (!link) return null;
        const texto = limpio(a.textContent);
        // El h3 incluye el precio: "Estudio en Centre, Hospitalet de Llobregat, L´ 804 €/mes"
        const titulo = limpio((a.querySelector("h2, h3") || link).textContent).replace(/\s*[\d.]+\s*€.*$/, "");
        // "Hospitalet de Llobregat, L´" -> "L'Hospitalet de Llobregat"
        const lugar = titulo.replace(/^.*? en /, "")
          .replace(/(^|, )([^,]+), (L|El|La|Els|Les)[´']$/, (_, pre, m, art) => pre + (art === "L" ? `L'${m}` : `${art} ${m}`));
        const coma = lugar.lastIndexOf(", ");
        const href = new URL(link.getAttribute("href"), location.origin).href.split("?")[0];
        const img = a.querySelector("img");
        return {
          id: href.split("-").pop(),
          titulo,
          url: href,
          precio: busca(/([\d.]+)\s*€\/mes/, texto),
          municipio: coma > 0 ? lugar.slice(coma + 2) : "",
          barrio: coma > 0 ? lugar.slice(0, coma) : lugar,
          habitaciones: busca(/(\d+)\s*habs?\./, texto),
          banos: busca(/(\d+)\s*baños?/, texto),
          m2: busca(/([\d.]+)\s*m²(?!\/)/, texto.replace(/[\d.,]+\s*€\/m²/, "")),
          imagen: (img?.getAttribute("src") || "").split("?")[0],
          temporal: temporal(texto),
          texto: texto.slice(0, 400),
        };
      }).filter(Boolean);
      const sig = doc.querySelector('link[rel="next"]');
      return { anuncios, siguiente: sig ? sig.getAttribute("href") : null };
    },

    wolorent(doc) {
      const anuncios = [...doc.querySelectorAll('a[href*="/piso-en-alquiler/"]')].map((a) => {
        // <span>ESTADO</span> <p>873 €/mes</p> <p>Municipio</p> <p>descripción</p> <p>4 habs</p> <p>1 baño</p> <p>65 m<sup>2</sup></p>
        const ps = [...a.querySelectorAll("p")].map((p) => limpio(p.textContent));
        const estado = limpio(a.querySelector("span")?.textContent).toUpperCase();
        const desc = ps.reduce((x, y) => (y.length > x.length ? y : x), "");
        const iPrecio = ps.findIndex((p) => /€\/mes/.test(p));
        const href = new URL(a.getAttribute("href"), location.origin);
        const slug = href.pathname.split("/")[2] || "";
        return {
          id: href.pathname.split("/").pop(),
          titulo: slug.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase()),
          url: href.href.split("?")[0],
          precio: num(ps[iPrecio]),
          municipio: iPrecio >= 0 ? ps[iPrecio + 1] || "" : "",
          barrio: (desc.match(/^En ([^,]+),/) || [])[1] || "",
          habitaciones: busca(/(\d+)\s*habs?\b/, ps.join(" ")),
          banos: busca(/(\d+)\s*baños?/, ps.join(" ")),
          m2: busca(/(\d+)\s*m\s*(?:²|2)\b/, ps.filter((p) => p.length < 12).join(" ")),
          imagen: a.querySelector("img")?.getAttribute("src") || "",
          // ALQUILADO / RESERVADO ya no están disponibles
          no_disponible: /ALQUILADO|RESERVADO/.test(estado),
          temporal: temporal(desc),
          texto: desc,
        };
      });
      return { anuncios, siguiente: null };
    },
  };

  // ---------- Fichas (todas las fotos, descripción, características, coordenadas) ----------
  const unicas = (urls, clave) => {
    const vistas = new Set();
    return urls.filter((u) => {
      const k = clave(u);
      if (vistas.has(k)) return false;
      vistas.add(k);
      return true;
    });
  };

  const ficha = {
    idealista(doc, html) {
      const fotos = html.match(/https:\/\/img\d?\.idealista\.com\/blur\/WEB_DETAIL(?:_TOP)?\/0\/id\.pro\.es\.image\.master\/[\w/]+?\.jpg/g) || [];
      const comentario = doc.querySelector("div.comment");
      const parrafos = comentario ? [...comentario.querySelectorAll("p")].map((p) => p.textContent.trim()) : [];
      return {
        imagenes: unicas(fotos.map((u) => u.replace("WEB_DETAIL_TOP", "WEB_DETAIL")), (u) => u.split("/").pop()),
        descripcion: parrafos.reduce((x, y) => (y.length > x.length ? y : x), ""),
        caracteristicas: [...doc.querySelectorAll(".details-property_features li")].map((l) => limpio(l.textContent)),
        // #headerMap: calle, barrio, distrito, municipio, comarca
        ubicacion: [...doc.querySelectorAll("#headerMap li")].map((l) => limpio(l.textContent)),
        anunciante: limpio(doc.querySelector(".professional-name .name, .advertiser-name-container .name, .professional-name")?.textContent)
          .replace(/^Profesional\s*/, ""),
      };
    },

    yaencontre(doc, html) {
      let lat = null, lon = null, descripcion = "";
      for (const s of doc.querySelectorAll('script[type="application/ld+json"]')) {
        const txt = s.textContent;
        const g = txt.match(/"latitude":\s*([\d.-]+),\s*"longitude":\s*([\d.-]+)/);
        if (g) [lat, lon] = [parseFloat(g[1]), parseFloat(g[2])];
        try {
          const d = JSON.parse(txt);
          const nodos = d["@graph"] || [d];
          for (const n of nodos) if (n.description && n.description.length > descripcion.length) descripcion = n.description;
        } catch (e) { /* JSON-LD mal formado: se ignora */ }
      }
      // El JSON-LD corta la descripción a 100 caracteres; la completa está en p.readMoreText
      const completa = doc.querySelector("p.readMoreText")?.textContent.trim();
      if (completa) descripcion = completa;
      // Solo las 3 primeras fotos vienen en el HTML; el resto las carga la web con JavaScript
      const fotos = (html.match(/https:\/\/media\.yaencontre\.com\/img\/photo\/w\d+\/[\w/.-]+?\.jpg/g) || [])
        .map((u) => u.replace(/\/w\d+\//, "/w1024/"));
      return {
        imagenes: unicas(fotos, (u) => u.split("/").pop()),
        descripcion,
        caracteristicas: [...doc.querySelectorAll('[class*="feature"] li, [class*="haracter"] li')].map((l) => limpio(l.textContent)),
        lat, lon,
      };
    },

    wolorent(doc, html) {
      const fotos = html.match(/https:\/\/wolo\.fra1\.digitaloceanspaces\.com\/photos\/\w+\/[\w.-]+?\.(?:webp|jpg|jpeg)/g) || [];
      const ps = [...doc.querySelectorAll("main p")].map((p) => p.textContent.trim());
      return {
        imagenes: unicas(fotos, (u) => u.split("/").pop()),
        descripcion: ps.reduce((x, y) => (y.length > x.length ? y : x), ""),
        caracteristicas: [...doc.querySelectorAll("main li")].map((l) => limpio(l.textContent)).filter((t) => t && t.length < 60),
      };
    },
  };

  return {
    portal,

    async listas(urls, { paginasMax = 15, pausa = 1500 } = {}) {
      const vistos = new Map();
      for (const inicio of urls) {
        let url = inicio;
        for (let p = 0; url && p < paginasMax; p++) {
          const { doc } = await descargar(url);
          const r = lista[portal](doc);
          r.anuncios.forEach((a) => vistos.set(a.id, a));
          url = r.siguiente;
          await espera(pausa);
        }
      }
      return { portal, fecha: new Date().toISOString().slice(0, 19), anuncios: [...vistos.values()] };
    },

    async fichas(urls, { pausa = 1500 } = {}) {
      const out = {};
      for (const url of urls) {
        try {
          const { doc, html } = await descargar(url);
          const id = portal === "wolorent" ? new URL(url).pathname.split("/").pop()
            : portal === "idealista" ? url.match(/inmueble\/(\d+)/)[1] : url.split("-").pop();
          const d = ficha[portal](doc, html);
          d.descripcion = (d.descripcion || "").slice(0, 2500);
          out[`${portal}:${id}`] = d;
        } catch (e) {
          out[url] = { error: String(e) };
        }
        await espera(pausa);
      }
      return out;
    },

    // Wolorent carga más resultados con un botón en la página abierta
    async wolorentCompleto() {
      for (let i = 0; i < 30; i++) {
        const b = [...document.querySelectorAll("button")].find((x) => /mostrar más/i.test(x.textContent));
        if (!b) break;
        b.click();
        await espera(1500);
      }
      return { portal, fecha: new Date().toISOString().slice(0, 19), anuncios: lista.wolorent(document).anuncios };
    },
  };
})();
