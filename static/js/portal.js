/* Portal de Novedades Odontológicas · Consulmed */
(function () {
  // Menú en celulares
  var boton = document.querySelector('.menu-boton');
  var nav = document.querySelector('.navegacion');
  if (boton && nav) {
    boton.addEventListener('click', function () {
      var abierta = nav.classList.toggle('abierta');
      boton.setAttribute('aria-expanded', abierta ? 'true' : 'false');
    });
  }

  // Buscador del encabezado: navega a buscar.html con el término (sin enviar formularios)
  document.querySelectorAll('form.buscador[action]').forEach(function (f) {
    f.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var v = (f.querySelector('input').value || '').trim();
      if (!v) return;
      var e = encodeURIComponent(v);
      location.href = f.getAttribute('action') + '?q=' + e + '#' + e;
    });
  });

  // Compartir: copiar enlace y menú nativo del celular
  document.querySelectorAll('.compartir').forEach(function (bar) {
    var url = bar.getAttribute('data-url'), titulo = bar.getAttribute('data-titulo');
    var copiar = bar.querySelector('.red-copiar');
    if (copiar) copiar.addEventListener('click', function () {
      var listo = function () { copiar.classList.add('ok'); setTimeout(function () { copiar.classList.remove('ok'); }, 1800); };
      var alternativa = function () {
        var c = document.createElement('textarea'); c.value = url; document.body.appendChild(c); c.select();
        try { document.execCommand('copy'); listo(); } catch (e2) {}
        document.body.removeChild(c);
      };
      try { navigator.clipboard.writeText(url).then(listo, alternativa); } catch (e) { alternativa(); }
    });
    var nativo = bar.querySelector('.red-nativo');
    var enMarco = false; try { enMarco = window.self !== window.top; } catch (e) { enMarco = true; }
    if (nativo && navigator.share && !enMarco) {
      nativo.hidden = false;
      nativo.addEventListener('click', function () {
        try { navigator.share({ title: titulo, url: url }).catch(function () {}); } catch (e) {}
      });
    }
  });

  // Fechas relativas ("hace 3 horas") para lo publicado en los últimos 7 días
  var ahora = Date.now();
  document.querySelectorAll('time[data-relativa]').forEach(function (t) {
    var d = new Date(t.getAttribute('datetime')).getTime();
    if (isNaN(d)) return;
    var min = Math.round((ahora - d) / 60000);
    var txt = null;
    if (min < 1) txt = 'recién';
    else if (min < 60) txt = 'hace ' + min + ' min';
    else if (min < 1440) { var h = Math.round(min / 60); txt = 'hace ' + h + (h === 1 ? ' hora' : ' horas'); }
    else if (min < 10080) { var dd = Math.round(min / 1440); txt = dd === 1 ? 'ayer' : 'hace ' + dd + ' días'; }
    if (txt) { t.title = t.textContent; t.textContent = txt; }
  });

  // Filtros por sección en "Últimas novedades"
  var filtros = document.querySelectorAll('.filtro');
  filtros.forEach(function (f) {
    f.addEventListener('click', function () {
      filtros.forEach(function (x) { x.classList.remove('activo'); });
      f.classList.add('activo');
      var valor = f.getAttribute('data-filtro');
      document.querySelectorAll('.lista-archivo .fila').forEach(function (li) {
        var s = li.querySelector('.fila-seccion');
        li.classList.toggle('oculta', valor !== 'todas' && (!s || s.textContent.trim() !== valor));
      });
    });
  });
})();

/* Buscador (funciona sin servidor: el índice viene en static/js/indice.js) */
function normalizar(s) {
  return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}
function escapar(s) {
  return (s || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
}
function resaltar(texto, terminos) {
  var html = escapar(texto);
  terminos.forEach(function (t) {
    if (t.length < 3) return;
    var re = new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
    html = html.replace(re, '<mark>$1</mark>');
  });
  return html;
}
function buscarNovedades(q) {
  var lista = document.getElementById('resultados');
  var info = document.getElementById('resultado-info');
  if (!lista || !window.INDICE) return;
  var terminos = normalizar(q).split(/\s+/).filter(Boolean);
  try { if (history.replaceState) history.replaceState(null, '', '?q=' + encodeURIComponent(q) + '#' + encodeURIComponent(q)); } catch (e) {}
  if (!terminos.length) { lista.innerHTML = ''; info.textContent = ''; return; }
  var res = window.INDICE.map(function (n) {
    var titulo = normalizar(n.t), cuerpo = normalizar(n.r + ' ' + n.e + ' ' + n.f);
    var puntos = 0;
    for (var i = 0; i < terminos.length; i++) {
      var t = terminos[i];
      if (titulo.indexOf(t) >= 0) puntos += 3;
      else if (cuerpo.indexOf(t) >= 0) puntos += 1;
      else return null;
    }
    return { n: n, p: puntos };
  }).filter(Boolean).sort(function (a, b) { return b.p - a.p || (a.n.d < b.n.d ? 1 : -1); }).slice(0, 100);
  info.textContent = res.length ? res.length + ' resultado' + (res.length === 1 ? '' : 's') + ' para "' + q + '"' : 'No encontramos novedades para "' + q + '". Probá con otra palabra.';
  var S = window.SECCIONES || {};
  lista.innerHTML = res.map(function (r) {
    var n = r.n, s = S[n.s] || ['', '', '#0054a6'];
    return '<li class="fila" style="--color-seccion:' + s[2] + '"><time>' + n.d.split('-').reverse().join('/') + '</time><div>' +
      '<a class="fila-titulo" href="' + n.u + '">' + resaltar(n.t, terminos) + '</a>' +
      '<div class="fila-meta"><span class="fila-seccion">' + escapar(s[0]) + '</span> · ' + escapar(n.f) + '</div>' +
      '<p style="margin:6px 0 0;font-size:14px;color:#4a5568">' + resaltar(n.r, terminos) + '</p></div></li>';
  }).join('');
}
function iniciarBuscador() {
  var q = new URLSearchParams(location.search).get('q') || '';
  if (!q && location.hash.length > 1) { try { q = decodeURIComponent(location.hash.slice(1)); } catch (e) { q = ''; } }
  var campo = document.getElementById('q');
  if (campo) campo.value = q;
  if (q) buscarNovedades(q);
  if (campo) campo.addEventListener('input', function () { buscarNovedades(campo.value); });
}
