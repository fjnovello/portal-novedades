# Novedades Odontológicas · Consulmed

Portal que reúne, traduce al español de Argentina y clasifica las novedades de odontología de todo el mundo (tecnología, tratamientos, lanzamientos, investigación, industria, salud pública y Argentina), con la estética de consulmed.com.ar.

## Cómo funciona

Cada 3 horas un robot hace cuatro pasos:

1. **Buscar** (`python actualizar.py buscar`): lee las fuentes de `config.py` (feeds RSS de revistas y medios, comunicados de prensa y búsquedas de Google Noticias en 6 idiomas), descarta lo viejo, lo que no es odontología y lo repetido, y deja las notas nuevas en `data/pendientes.json`.
2. **Traducir** (`python actualizar.py traducir`): manda las notas de a 8 a la API de Claude, que devuelve título traducido, resumen propio, "por qué importa", sección, etiquetas, importancia y si la nota es relevante. El resultado se acumula en `data/articulos.json`, la base del portal.
3. **Completar** (`python actualizar.py completar`): convierte los enlaces de Google Noticias en el enlace real del medio y, para las notas cuya licencia lo permite, descarga el texto original y lo traduce **completo** al español.
4. **Construir** (`python actualizar.py construir`): genera el sitio estático en `sitio/`.

`python actualizar.py todo` hace los cuatro pasos seguidos.

## Notas completas: cuáles sí y cuáles no

Se publican **traducidas completas** en el portal:
- **Comunicados de prensa** de empresas y universidades (PR Newswire, Business Wire, GlobeNewswire, EurekAlert!): se emiten para que los medios los publiquen. Acá están casi todos los lanzamientos de productos y muchas investigaciones.
- **Artículos científicos de acceso abierto con licencia CC BY** (Frontiers, PLOS ONE, BDJ Open, International Journal of Oral Science): se traduce el resumen científico completo.
- **Textos oficiales de dominio público** (FDA y otros organismos de EE.UU.).
- **Medios que den autorización por escrito**: se agrega su dominio en `LICENCIA_POR_DOMINIO` con el valor `"autorizado"`.

Las notas de **medios periodísticos** (DrBicuspid, Dental Tribune, Becker's, etc.) se publican con título traducido, resumen propio y el botón **"Leer la nota completa en español"**, que abre la nota del medio traducida al instante por Google. Traducir y republicar esas notas enteras sin permiso es una obra derivada que infringe derechos de autor, y Google penaliza el contenido copiado.

## Puesta en línea

El robot corre gratis en GitHub Actions y publica el sitio por una de dos vías:

**Opción A: en el hosting actual de consulmed.com.ar, por FTP**
1. Crear un repositorio en GitHub y subir esta carpeta, sin `sitio/`.
2. En **Settings → Secrets and variables → Actions → Secrets**, cargar `ANTHROPIC_API_KEY`, `FTP_SERVIDOR`, `FTP_USUARIO` y `FTP_CLAVE`. Las claves se escriben ahí directamente; no hace falta pasárselas a nadie.
3. En **Variables**, opcional: `FTP_CARPETA` (por defecto `./novedades/`) y `FTP_PROTOCOLO` (`ftps` o `ftp`).
4. **Actions → Actualizar novedades → Run workflow.** El portal queda en `consulmed.com.ar/novedades/` y se actualiza solo.

**Opción B: GitHub Pages en un subdominio**
1. Igual que arriba, pero sin los secretos de FTP. Variable `DOMINIO_PROPIO`: `novedades.consulmed.com.ar`.
2. **Settings → Pages → Source: GitHub Actions.**
3. En el DNS de consulmed.com.ar: registro **CNAME** `novedades` → `<usuario-de-github>.github.io`.

En los dos casos, actualizar `SITIO["url"]` en `config.py` con la dirección final (se usa en el RSS, el sitemap y las etiquetas para buscadores).

## Probarlo en la computadora

```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...      # solo para traducir
python actualizar.py todo
open sitio/index.html
```

## Costos

GitHub Pages y GitHub Actions: sin costo para este uso. La API de Claude cobra por volumen: cada nota resumida consume del orden de 200 tokens de entrada y 150 de salida; una nota traducida completa, del orden de 1.500 de entrada y 2.000 de salida (tope por corrida en `MAX_NOTAS_COMPLETAS_POR_CORRIDA`). Con 300 a 500 notas nuevas por día son unos 3 millones de tokens de entrada y 2 millones de salida por mes. El tope `MAX_NUEVOS_POR_CORRIDA` en `config.py` limita el gasto, y el modelo se cambia con `MODELO_CLAUDE`.

## Ajustes frecuentes (todos en `config.py`)

- **Sumar una fuente**: una línea `rss(...)` o `gnews(...)` en `FUENTES`.
- **Secciones**: nombre, descripción, color e ícono en `SECCIONES`.
- **Newsletter**: pegar en `suscripcion_url` la dirección del formulario de Doppler (la herramienta que ya usa consulmed.com.ar).
- **Medición de visitas**: pegar el código de Google Tag Manager en `gtm`.

## Archivos

- `config.py`: fuentes, secciones y parámetros.
- `actualizar.py`: buscar, traducir, importar y construir.
- `plantillas/`: diseño de cada página (HTML con Jinja2).
- `static/`: estilos, scripts y logo.
- `data/articulos.json`: base de notas publicadas. `data/pendientes.json`: notas a traducir.
- `.github/workflows/actualizar.yml`: el robot que corre cada 3 horas y publica.
