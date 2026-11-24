#!/usr/bin/env python3
"""Portal de Novedades Odontológicas de Consulmed.

Uso:
  python actualizar.py buscar      # lee todas las fuentes y deja las notas nuevas en data/pendientes.json
  python actualizar.py traducir    # traduce, resume y clasifica las pendientes con la API de Claude
  python actualizar.py completar   # resuelve enlaces y traduce completas las notas con licencia que lo permite
  python actualizar.py importar ARCHIVO.json   # suma traducciones hechas a mano o por otro medio
  python actualizar.py construir   # genera el sitio estático en sitio/
  python actualizar.py todo        # buscar + traducir + completar + construir (lo que corre el robot cada 3 horas)

Requiere: pip install -r requirements.txt  y, para traducir, la variable ANTHROPIC_API_KEY.
"""
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import sys
import time
import unicodedata
import urllib.request
from email.utils import format_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
ARTICULOS = DATA / "articulos.json"
PENDIENTES = DATA / "pendientes.json"
ORIGINALES = DATA / "originales.json"
SALIDA = BASE / "sitio"
TZ_AR = ZoneInfo("America/Argentina/Buenos_Aires")
UA = "Mozilla/5.0 (compatible; ConsulmedNovedades/1.0; +https://consulmed.com.ar)"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------- utilidades
def leer_json(ruta, defecto):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return defecto


def guardar_json(ruta, datos):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(ruta) + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ruta)


def id_de(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def texto_plano(s, maximo=700):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maximo]


def normalizar(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", s)


def palabras(s):
    return {w for w in normalizar(s).split() if len(w) > 3}


def parecido(a, b):
    pa, pb = palabras(a), palabras(b)
    if not pa or not pb:
        return 0.0
    return len(pa & pb) / len(pa | pb)


def slugify(s, largo=70):
    s = normalizar(s).strip()
    s = re.sub(r"\s+", "-", s)
    return s[:largo].strip("-")


PATRON_DENTAL = re.compile(r"\b(" + "|".join(re.escape(p) for p in config.PALABRAS_DENTALES) + ")", re.I)


def es_dental(texto):
    # \b evita falsos positivos como "incidental" o "identity"
    return bool(PATRON_DENTAL.search(texto or ""))


# ------------------------------------------------------------------- buscar
def buscar():
    import feedparser

    articulos = leer_json(ARTICULOS, [])
    pendientes = leer_json(PENDIENTES, [])
    vistos = {a["id"] for a in articulos} | {p["id"] for p in pendientes}
    titulos_recientes = [a.get("titulo_original", "") for a in articulos[:600]] + \
                        [p["titulo_original"] for p in pendientes]
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=config.DIAS_ATRAS_PRIMERA_CARGA)
    nuevos, informe = [], []

    for f in config.FUENTES:
        try:
            req = urllib.request.Request(f["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=25) as r:
                feed = feedparser.parse(r.read())
        except Exception as e:  # una fuente caída no frena al resto
            informe.append(f"  ✗ {f['nombre']}: {e}")
            continue
        sumadas = 0
        for e in feed.entries:
            url = e.get("link")
            titulo = texto_plano(e.get("title", ""), 300)
            if not url or not titulo:
                continue
            fuente = f["nombre"]
            if f["tipo"] == "gnews":
                origen = (e.get("source") or {}).get("title")
                if origen:
                    fuente = origen
                    titulo = re.sub(r"\s+[-–|]\s+" + re.escape(origen) + r"\s*$", "", titulo)
                resumen = ""  # la descripción de Google Noticias no aporta texto propio
            else:
                resumen = texto_plano(e.get("summary") or e.get("description") or "")
            ident = id_de(url)
            if ident in vistos:
                continue
            fecha_t = e.get("published_parsed") or e.get("updated_parsed")
            fecha = (dt.datetime(*fecha_t[:6], tzinfo=dt.timezone.utc) if fecha_t
                     else dt.datetime.now(dt.timezone.utc))
            if fecha < limite:
                continue
            if f["filtrar"] and not es_dental(titulo + " " + resumen):
                continue
            if any(parecido(titulo, t) > 0.7 for t in titulos_recientes):
                continue  # la misma noticia ya entró por otra fuente
            vistos.add(ident)
            titulos_recientes.append(titulo)
            nuevos.append({
                "id": ident, "url": url, "fuente": fuente, "idioma": f["idioma"],
                "region": f["region"], "fecha": fecha.isoformat(),
                "titulo_original": titulo, "resumen_original": resumen,
                "licencia": f.get("licencia"),
            })
            sumadas += 1
        informe.append(f"  ✓ {f['nombre']}: {len(feed.entries)} leídas, {sumadas} nuevas")

    nuevos.sort(key=lambda x: x["fecha"], reverse=True)
    pendientes = nuevos + pendientes
    guardar_json(PENDIENTES, pendientes)
    print("\n".join(informe))
    print(f"→ {len(nuevos)} notas nuevas. Pendientes de traducir: {len(pendientes)}")
    return len(nuevos)


# ----------------------------------------------------------------- traducir
PROMPT_SISTEMA = """Sos el editor del portal "Novedades Odontológicas" de Consulmed, empresa argentina que presta, administra y financia servicios odontológicos. Recibís notas de medios de todo el mundo (en cualquier idioma) y para cada una devolvés su versión para lectores argentinos: odontólogos, clínicas, prepagas y obras sociales.

Reglas:
- Escribí 100% en español de Argentina, registro periodístico profesional (sin voseo en el cuerpo de la nota). Usá el vocabulario local: odontólogo, consultorio, prepaga, obra social, ANMAT cuando corresponda.
- "titulo": traducción fiel y natural del título, máximo 120 caracteres. Mantené sin traducir nombres propios, marcas y productos.
- "resumen": resumen PROPIO de la noticia en 3 a 4 oraciones (entre 60 y 100 palabras), redactado con tus palabras y sin copiar frases del original. Tiene que contar lo esencial: qué pasó, quién, dónde, y las cifras o resultados clave. Usá solo información presente en el título y el texto recibido; no inventes cifras, fechas ni detalles. Si solo hay título, escribí una sola oración que lo explique sin agregar datos.
- "por_que_importa": una oración sobre la relevancia práctica para odontólogos o financiadores en Argentina. Si el material no alcanza para decir algo concreto y prudente, dejalo vacío.
- "seccion": una de: tecnologia, tratamientos, lanzamientos, investigacion, industria, salud-publica, argentina. Usá "argentina" solo si la nota trata sobre Argentina o Latinoamérica.
- "argentina": true si trata sobre Argentina o Latinoamérica.
- "etiquetas": de 2 a 4 temas cortos en español, en minúscula (ej.: "implantes", "inteligencia artificial").
- "relevante": false si la nota no trata sobre odontología, salud bucal o la industria dental. También false para: policiales, necrológicas, política universitaria o partidaria, notas de color, aniversarios y eventos sociales, apertura de un consultorio individual, sitios web nuevos de clínicas, avisos de empleo, publicidad de clínicas o productos de consumo sin información nueva, y reportes de mercado de consultoras ("el mercado alcanzará US$X en 2033").
- "importancia": de 1 a 5 según el impacto para el sector (5 = noticia mayor).

Respondé ÚNICAMENTE con un arreglo JSON, un objeto por nota y en el mismo orden, con las claves: id, titulo, resumen, por_que_importa, seccion, argentina, etiquetas, relevante, importancia."""


def api_claude(sistema, contenido, max_tokens=4000):
    """Llama a la API de Claude y devuelve el texto de la respuesta (o None)."""
    clave = os.environ.get("ANTHROPIC_API_KEY")
    if not clave:
        raise SystemExit("Falta la variable de entorno ANTHROPIC_API_KEY.")
    modelo = os.environ.get("CLAUDE_MODEL", config.MODELO_CLAUDE)
    cuerpo = {"model": modelo, "max_tokens": max_tokens, "system": sistema,
              "messages": [{"role": "user", "content": contenido}]}
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=json.dumps(cuerpo).encode("utf-8"),
        headers={"x-api-key": clave, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    for intento in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                resp = json.loads(r.read())
            return "".join(b.get("text", "") for b in resp["content"])
        except Exception as e:
            espera = 10 * (intento + 1)
            print(f"  reintento en {espera}s ({e})")
            time.sleep(espera)
    return None


def llamar_claude(items):
    entrada = [{"id": i["id"], "idioma": i["idioma"], "medio": i["fuente"],
                "titulo": i["titulo_original"], "texto": i["resumen_original"]} for i in items]
    texto = api_claude(PROMPT_SISTEMA, json.dumps(entrada, ensure_ascii=False))
    if not texto:
        return []
    try:
        return json.loads(texto[texto.find("["): texto.rfind("]") + 1])
    except ValueError:
        return []


def incorporar(traducciones, pendientes, articulos):
    """Une las traducciones con sus notas originales y las suma a articulos."""
    por_id = {p["id"]: p for p in pendientes}
    existentes = {a["id"] for a in articulos}
    usados_slug = {a["slug"] for a in articulos}
    agregadas = 0
    for t in traducciones:
        p = por_id.get(t.get("id"))
        if not p or p["id"] in existentes:
            continue
        a = dict(p)
        a.update({
            "titulo": (t.get("titulo") or p["titulo_original"]).strip(),
            "resumen": (t.get("resumen") or "").strip(),
            "por_que_importa": (t.get("por_que_importa") or "").strip(),
            "seccion": t.get("seccion") if t.get("seccion") in config.SECCIONES else config.SECCION_POR_DEFECTO,
            "argentina": bool(t.get("argentina")),
            "etiquetas": [e.strip().lower() for e in (t.get("etiquetas") or [])][:4],
            "relevante": t.get("relevante", True) is not False,
            "importancia": int(t.get("importancia") or 2),
            "traducido": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        if a["seccion"] == "argentina":
            a["argentina"] = True
        # descarta duplicados entre idiomas (misma noticia, distinto medio)
        if a["relevante"] and any(parecido(a["titulo"], b["titulo"]) > 0.6
                                  for b in articulos[:400] if b.get("relevante")):
            a["relevante"] = False
            a["duplicado"] = True
        slug = slugify(a["titulo"]) or a["id"]
        if slug in usados_slug:
            slug = f"{slug}-{a['id'][:5]}"
        usados_slug.add(slug)
        a["slug"] = slug
        articulos.append(a)
        existentes.add(a["id"])
        agregadas += 1
    articulos.sort(key=lambda x: x["fecha"], reverse=True)
    return agregadas


def preparar_contexto(item):
    """Resuelve el enlace real y, si la fuente trajo poco texto, lee el comienzo de la nota."""
    if "news.google.com" in item["url"]:
        item["url_google"] = item["url"]
        item["url"] = resolver_url(item["url"])
    if len(item.get("resumen_original", "")) >= 300 or "news.google.com" in item["url"]:
        return
    try:
        import trafilatura
        texto = trafilatura.extract(descargar(item["url"]), include_comments=False,
                                    include_tables=False, favor_precision=True) or ""
        if len(texto.split()) >= 40:
            item["resumen_original"] = " ".join(texto.split()[:350])
    except Exception as e:
        print(f"  sin contexto de {item['fuente']}: {e}")


def traducir():
    pendientes = leer_json(PENDIENTES, [])
    if not pendientes:
        print("No hay notas pendientes.")
        return
    articulos = leer_json(ARTICULOS, [])
    tanda = pendientes[: config.MAX_NUEVOS_POR_CORRIDA]
    total = 0
    for i in range(0, len(tanda), config.LOTE_TRADUCCION):
        lote = tanda[i: i + config.LOTE_TRADUCCION]
        for item in lote:
            preparar_contexto(item)
        resultado = llamar_claude(lote)
        total += incorporar(resultado, lote, articulos)
        hechos = {r.get("id") for r in resultado}
        pendientes = [p for p in pendientes if p["id"] not in hechos]
        guardar_json(ARTICULOS, articulos)
        guardar_json(PENDIENTES, pendientes)
        print(f"  traducidas {min(i + len(lote), len(tanda))}/{len(tanda)}")
    print(f"→ {total} notas incorporadas. Quedan {len(pendientes)} pendientes.")


def importar(ruta):
    traducciones = leer_json(ruta, [])
    pendientes = leer_json(PENDIENTES, [])
    articulos = leer_json(ARTICULOS, [])
    por_id = {a["id"]: a for a in articulos}
    for t in traducciones:  # correcciones sobre notas ya publicadas (ej.: marcar duplicadas)
        if t.get("id") in por_id:
            for campo in ("relevante", "duplicado", "titulo", "resumen", "por_que_importa"):
                if campo in t:
                    por_id[t["id"]][campo] = t[campo]
    n = incorporar(traducciones, pendientes, articulos)
    por_id = {a["id"]: a for a in articulos}
    for t in traducciones:  # traducciones completas
        if t.get("id") in por_id and t.get("cuerpo"):
            por_id[t["id"]]["cuerpo"] = t["cuerpo"].strip()
    hechos = {t.get("id") for t in traducciones}
    guardar_json(ARTICULOS, articulos)
    guardar_json(PENDIENTES, [p for p in pendientes if p["id"] not in hechos])
    print(f"→ {n} notas importadas.")


# ---------------------------------------------------------------- completar
PROMPT_COMPLETA = """Sos traductor profesional del portal "Novedades Odontológicas" de Consulmed (Argentina). Vas a recibir el texto de una publicación cuya licencia permite traducirla completa. Traducila COMPLETA y con fidelidad al español de Argentina, en registro periodístico profesional (sin voseo).

Reglas:
- No resumas, no agregues información, no opines. Mantené cifras, nombres propios, marcas y citas (las citas van traducidas, entre comillas).
- Respetá la estructura: un párrafo por párrafo del original. Si el original tiene subtítulos, escribilos en una línea que empiece con "## ". Las listas, con líneas que empiecen con "- ".
- Omití solo lo que no es contenido: datos de contacto de prensa, avisos legales sobre declaraciones a futuro, botones, menús, referencias bibliográficas y textos repetidos.
- Si es el resumen (abstract) de un artículo científico, respetá sus apartados (Antecedentes, Métodos, Resultados, Conclusiones) como subtítulos "## ".
- Usá terminología odontológica correcta en español (ej.: "periimplantitis", "alineadores", "escáner intraoral").

Respondé solo con la traducción, sin comentarios."""


def licencia_de(url, actual=None):
    if actual:
        return actual
    for dominio, lic in config.LICENCIA_POR_DOMINIO.items():
        if dominio in url:
            return lic
    return None


def resolver_url(url):
    """Convierte un enlace de Google Noticias en el enlace real del medio."""
    if "news.google.com" not in url:
        return url
    try:
        from googlenewsdecoder import gnewsdecoder
        r = gnewsdecoder(url, interval=1)
        if r.get("status") and r.get("decoded_url"):
            return r["decoded_url"]
    except Exception as e:
        print(f"  no se pudo resolver {url[:60]}…: {e}")
    return url


def descargar(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,es;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def texto_de_pagina(url, licencia):
    """Texto a traducir: el abstract en artículos científicos, el cuerpo completo en el resto."""
    pagina = descargar(url)
    if licencia == "cc-by":
        candidatos = re.findall(
            r'<meta[^>]+(?:name|property)="(?:dc\.description|citation_abstract|description|og:description)"[^>]+content="([^"]+)"',
            pagina, flags=re.I)
        candidatos += re.findall(
            r'<meta[^>]+content="([^"]+)"[^>]+(?:name|property)="(?:dc\.description|citation_abstract|description|og:description)"',
            pagina, flags=re.I)
        bloque = re.search(r'id="Abs1-content"[^>]*>(.*?)</div>', pagina, flags=re.S)  # revistas de Nature
        if bloque:
            candidatos.append(bloque.group(1))
        if candidatos and len(max(candidatos, key=len).split()) > 60:
            return texto_plano(max(candidatos, key=len), 6000)
    import trafilatura
    texto = trafilatura.extract(pagina, include_comments=False, include_tables=False,
                                favor_precision=True) or ""
    palabras_ = texto.split()
    if len(palabras_) > config.MAX_PALABRAS_NOTA_COMPLETA:
        texto = " ".join(palabras_[: config.MAX_PALABRAS_NOTA_COMPLETA])
    return texto.strip()


def completar():
    articulos = leer_json(ARTICULOS, [])
    originales = leer_json(ORIGINALES, {})
    con_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
    resueltas = completas = 0
    for a in articulos:
        if not a.get("relevante", True):
            continue
        if "news.google.com" in a["url"] and not a.get("url_google"):
            a["url_google"] = a["url"]
            a["url"] = resolver_url(a["url"])
            resueltas += 1
        a["licencia"] = licencia_de(a["url"], a.get("licencia"))
    guardar_json(ARTICULOS, articulos)

    candidatas = [a for a in articulos if a.get("relevante", True) and a.get("licencia")
                  and not a.get("cuerpo") and not a.get("sin_texto")][: config.MAX_NOTAS_COMPLETAS_POR_CORRIDA]
    for a in candidatas:
        if a["id"] not in originales:
            try:
                originales[a["id"]] = texto_de_pagina(a["url"], a["licencia"])
            except Exception as e:
                print(f"  sin texto: {a['fuente']} ({e})")
                originales[a["id"]] = ""
            guardar_json(ORIGINALES, originales)
        texto = originales[a["id"]]
        if len(texto.split()) < 60:
            a["sin_texto"] = True
            continue
        if not con_api:
            continue
        traduccion = api_claude(PROMPT_COMPLETA, f"Medio: {a['fuente']}\nTítulo: {a['titulo_original']}\n\n{texto}",
                                max_tokens=8000)
        if traduccion and len(traduccion.split()) > 40:
            a["cuerpo"] = traduccion.strip()
            completas += 1
            guardar_json(ARTICULOS, articulos)
    guardar_json(ARTICULOS, articulos)
    print(f"→ {resueltas} enlaces resueltos, {completas} notas traducidas completas.")


def md_a_html(texto):
    """Convierte el formato simple de las traducciones (## subtítulos, - listas) a HTML."""
    partes, lista = [], []
    for bloque in re.split(r"\n\s*\n", texto.strip()):
        for linea in bloque.split("\n") if bloque.lstrip().startswith("- ") else [bloque]:
            linea = linea.strip()
            if linea.startswith("- "):
                lista.append(f"<li>{html.escape(linea[2:])}</li>")
                continue
            if lista:
                partes.append("<ul>" + "".join(lista) + "</ul>")
                lista = []
            if linea.startswith("## "):
                partes.append(f"<h2>{html.escape(linea[3:])}</h2>")
            elif linea:
                partes.append(f"<p>{html.escape(' '.join(linea.split()))}</p>")
    if lista:
        partes.append("<ul>" + "".join(lista) + "</ul>")
    return "\n".join(partes)


def leer_en_espanol(url, idioma):
    """Enlace para leer la nota original traducida por Google al español."""
    if idioma == "es" or "news.google.com" in url:
        return url
    from urllib.parse import quote
    return f"https://translate.google.com/translate?sl={idioma}&tl=es&hl=es-419&u={quote(url, safe='')}"


# ------------------------------------------------- imágenes para redes sociales
def _degradado(ancho, alto, c1, c2):
    from PIL import Image
    base = Image.new("RGB", (ancho, alto), c1)
    tope = Image.new("RGB", (ancho, alto), c2)
    mascara = Image.new("L", (2, 2))
    mascara.putdata([0, 120, 120, 255])  # diagonal: arriba a la izquierda c1, abajo a la derecha c2
    mascara = mascara.resize((ancho, alto), Image.BILINEAR)
    return Image.composite(tope, base, mascara)


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _partir(texto, fuente, ancho_max, draw):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = (actual + " " + palabra).strip()
        if draw.textlength(prueba, font=fuente) <= ancho_max:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def imagen_redes(destino, titulo, seccion=None, pie=""):
    """Imagen de 1200x630 con la marca Consulmed para la vista previa en redes sociales."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    img = _degradado(W, H, _hex("#0054a6"), _hex("#1b1464"))
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(0, W, 24):  # trama de puntos como en el sitio
        for y in range(0, H, 24):
            d.ellipse((x, y, x + 2.4, y + 2.4), fill=(255, 255, 255, 22))
    fuentes = BASE / "recursos" / "fuentes"
    negrita = lambda t: ImageFont.truetype(str(fuentes / "Nunito-800.ttf"), t)
    media = lambda t: ImageFont.truetype(str(fuentes / "Nunito-700.ttf"), t)
    color_sec = _hex(config.SECCIONES[seccion][2]) if seccion else _hex("#6dcff6")
    d.rectangle((0, 0, 14, H), fill=color_sec)
    logo = Image.open(BASE / "static" / "img" / "logo.png").convert("RGBA")
    logo = logo.resize((int(logo.width * 1.25), int(logo.height * 1.25)))
    img.paste(logo, (70, 56), logo)
    d.line((70 + logo.width + 24, 58, 70 + logo.width + 24, 56 + logo.height), fill=(255, 255, 255, 120), width=3)
    d.text((70 + logo.width + 46, 58), "NOVEDADES", font=media(20), fill=_hex("#cfebf9"))
    d.text((70 + logo.width + 46, 80), "ODONTOLÓGICAS", font=negrita(26), fill=(255, 255, 255))
    for tam in (60, 54, 48, 42):
        f = negrita(tam)
        lineas = _partir(titulo, f, W - 150, d)
        if len(lineas) <= 4:
            break
    lineas = lineas[:4]
    alto_bloque = (62 if seccion else 0) + int(tam * 1.18) * len(lineas)
    y = 150 + max(0, (H - 100 - 150 - alto_bloque) // 2)  # centrado entre encabezado y pie
    if seccion:
        nombre = config.SECCIONES[seccion][0].upper()
        fs = negrita(20)
        ancho = d.textlength(nombre, font=fs) + 36
        d.rounded_rectangle((70, y, 70 + ancho, y + 38), radius=19, fill=color_sec)
        d.text((88, y + 7), nombre, font=fs, fill=_hex(config.SECCIONES[seccion][4]))
        y += 62
    for linea in lineas:
        d.text((70, y), linea, font=f, fill=(255, 255, 255))
        y += int(tam * 1.18)
    d.text((70, H - 66), pie, font=media(22), fill=_hex("#cfebf9"))
    img.save(destino, "JPEG", quality=86, optimize=True, progressive=True)


# ---------------------------------------------------------------- construir
def fecha_ar(iso):
    return dt.datetime.fromisoformat(iso).astimezone(TZ_AR)


def fecha_larga(iso):
    d = fecha_ar(iso)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def fecha_corta(iso):
    d = fecha_ar(iso)
    return f"{d.day} {MESES[d.month - 1][:3]}. {d.year} · {d:%H:%M}"


def construir():
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    todos = leer_json(ARTICULOS, [])
    notas = [a for a in todos if a.get("relevante", True)]
    url_sitio = config.SITIO["url"].rstrip("/")
    for a in notas:
        a["cuerpo_html"] = md_a_html(a["cuerpo"]) if a.get("cuerpo") else ""
        a["url_portal"] = f"{url_sitio}/nota/{a['slug']}.html"
    notas.sort(key=lambda x: x["fecha"], reverse=True)
    ahora = dt.datetime.now(dt.timezone.utc)

    if SALIDA.exists():
        try:
            shutil.rmtree(SALIDA)
        except OSError:
            pass  # si la carpeta no se puede borrar, se sobrescriben los archivos
    for carpeta in ("nota", "seccion", "ultimas"):
        (SALIDA / carpeta).mkdir(parents=True, exist_ok=True)
    shutil.copytree(BASE / "static", SALIDA / "static", dirs_exist_ok=True)
    (SALIDA / "static" / "og").mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(BASE / "plantillas"),
                      autoescape=select_autoescape(["html", "xml"]))
    env.filters["fecha_larga"] = fecha_larga
    env.filters["fecha_corta"] = fecha_corta
    env.filters["idioma"] = lambda c: config.IDIOMAS.get(c, c)
    env.globals["leer_en_espanol"] = leer_en_espanol
    env.globals["licencias"] = config.LICENCIAS

    fuentes_activas = sorted({a["fuente"] for a in notas})
    idiomas_activos = sorted({a["idioma"] for a in notas})
    por_seccion = {s: [a for a in notas if a["seccion"] == s or (s == "argentina" and a.get("argentina"))]
                   for s in config.SECCIONES}
    comunes = {
        "sitio": config.SITIO, "secciones": config.SECCIONES, "cortos": config.SECCIONES_CORTO, "idiomas": config.IDIOMAS,
        "generado": fecha_corta(ahora.isoformat()), "anio": fecha_ar(ahora.isoformat()).year,
        "total_notas": len(notas), "total_fuentes": len(fuentes_activas),
        "total_idiomas": len(idiomas_activos), "conteo_seccion": {k: len(v) for k, v in por_seccion.items()},
        "ultimas_ticker": notas[:10], "total_completas": sum(1 for a in notas if a.get("cuerpo")),
    }

    def render(plantilla, destino, raiz, **ctx):
        html_ = env.get_template(plantilla).render(raiz=raiz, **comunes, **ctx)
        (SALIDA / destino).write_text(html_, encoding="utf-8")

    def paginar(lista, n=config.NOTAS_POR_PAGINA):
        return [lista[i:i + n] for i in range(0, len(lista), n)] or [[]]

    # Portada
    hace_72h = (ahora - dt.timedelta(hours=72)).isoformat()
    recientes = [a for a in notas if a["fecha"] >= hace_72h] or notas[:20]
    principal = sorted(recientes, key=lambda a: (a.get("importancia", 2), a["fecha"]), reverse=True)[:1]
    ids_p = {a["id"] for a in principal}
    secundarias = [a for a in sorted(recientes, key=lambda a: (a.get("importancia", 2), a["fecha"]), reverse=True)
                   if a["id"] not in ids_p][:4]
    usados = ids_p | {a["id"] for a in secundarias}
    hace_7d = (ahora - dt.timedelta(days=7)).isoformat()
    destacadas = sorted([a for a in notas if a["fecha"] >= hace_7d],
                        key=lambda a: (a.get("importancia", 2), a["fecha"]), reverse=True)[:6]
    bloques = [(s, [a for a in por_seccion[s] if a["id"] not in usados][:4]) for s in config.SECCIONES]
    render("index.html", "index.html", "",
           principal=principal[0] if principal else None, secundarias=secundarias,
           ultimas=[a for a in notas if a["id"] not in usados][:12],
           destacadas=destacadas, bloques=bloques, argentina=por_seccion["argentina"][:5])

    # Secciones
    for s, lista in por_seccion.items():
        paginas = paginar(lista)
        for i, pagina in enumerate(paginas, 1):
            nombre = f"{s}.html" if i == 1 else f"{s}-{i}.html"
            render("seccion.html", f"seccion/{nombre}", "../", slug=s, notas=pagina, activa=s,
                   pagina=i, total_paginas=len(paginas), base_pag=s)

    # Últimas novedades (archivo completo)
    paginas = paginar(notas, 30)
    for i, pagina in enumerate(paginas, 1):
        nombre = "index.html" if i == 1 else f"{i}.html"
        render("ultimas.html", f"ultimas/{nombre}", "../", notas=pagina, pagina=i, activa="ultimas",
               total_paginas=len(paginas))

    # Imágenes para redes sociales: una por nota (las más recientes); las demás usan la de portada
    cache_og = DATA / "imagenes"
    cache_og.mkdir(exist_ok=True)
    try:
        portada = cache_og / "portada.jpg"
        if not portada.exists():
            imagen_redes(portada, config.SITIO["lema"], None, config.SITIO["url"].replace("https://", ""))
        shutil.copy(portada, SALIDA / "static" / "og" / "portada.jpg")
        for a in notas[: config.MAX_IMAGENES_REDES]:
            archivo = cache_og / f"{a['id']}.jpg"
            if not archivo.exists():
                pie = f"{a['fuente']}  ·  {fecha_larga(a['fecha'])}"
                imagen_redes(archivo, a["titulo"], a["seccion"], pie)
            shutil.copy(archivo, SALIDA / "static" / "og" / f"{a['slug']}.jpg")
            a["imagen_redes"] = f"{url_sitio}/static/og/{a['slug']}.jpg"
    except Exception as e:  # sin Pillow o sin fuentes, el sitio igual se genera
        print(f"  imágenes para redes omitidas: {e}")
    for a in notas:
        a.setdefault("imagen_redes", f"{url_sitio}/static/og/portada.jpg")

    # Notas
    for a in notas:
        relacionadas = [b for b in por_seccion[a["seccion"]] if b["id"] != a["id"]][:4]
        render("nota.html", f"nota/{a['slug']}.html", "../", a=a, relacionadas=relacionadas,
               activa=a["seccion"])

    # Otras páginas
    fuentes_info = []
    for f in config.FUENTES:
        fuentes_info.append({"nombre": f["nombre"], "idioma": f["idioma"], "tipo": f["tipo"],
                             "notas": sum(1 for a in notas if a["fuente"] == f["nombre"])})
    render("fuentes.html", "fuentes.html", "", fuentes=fuentes_info, medios=fuentes_activas)
    render("buscar.html", "buscar.html", "")
    render("404.html", "404.html", "")

    # Índice de búsqueda (como .js para que funcione también abriendo el archivo local)
    indice = [{"t": a["titulo"], "r": a["resumen"], "s": a["seccion"], "f": a["fuente"],
               "d": a["fecha"][:10], "u": f"nota/{a['slug']}.html",
               "e": " ".join(a.get("etiquetas", []))} for a in notas]
    (SALIDA / "static" / "js" / "indice.js").write_text(
        "window.INDICE=" + json.dumps(indice, ensure_ascii=False) + ";", encoding="utf-8")

    # RSS propio, sitemap y robots
    url = config.SITIO["url"].rstrip("/")
    items = []
    for a in notas[:60]:
        items.append(
            f"<item><title>{html.escape(a['titulo'])}</title>"
            f"<link>{url}/nota/{a['slug']}.html</link><guid isPermaLink=\"false\">{a['id']}</guid>"
            f"<pubDate>{format_datetime(dt.datetime.fromisoformat(a['fecha']))}</pubDate>"
            f"<category>{html.escape(config.SECCIONES[a['seccion']][0])}</category>"
            f"<description>{html.escape(a['resumen'])} (Fuente: {html.escape(a['fuente'])})</description></item>")
    (SALIDA / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        f"<title>{config.SITIO['nombre']} | {config.SITIO['marca']}</title><link>{url}/</link>"
        f"<description>{config.SITIO['lema']}</description><language>es-AR</language>"
        + "".join(items) + "</channel></rss>", encoding="utf-8")
    urls = [f"{url}/", f"{url}/ultimas/", f"{url}/fuentes.html"] + \
           [f"{url}/seccion/{s}.html" for s in config.SECCIONES] + \
           [f"{url}/nota/{a['slug']}.html" for a in notas]
    (SALIDA / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>", encoding="utf-8")
    (SALIDA / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {url}/sitemap.xml\n")
    if os.environ.get("DOMINIO_PROPIO"):
        (SALIDA / "CNAME").write_text(os.environ["DOMINIO_PROPIO"] + "\n")
    print(f"→ Sitio generado en {SALIDA}: {len(notas)} notas, {len(fuentes_activas)} medios, "
          f"{len(idiomas_activos)} idiomas.")


# ---------------------------------------------------------------------- main
if __name__ == "__main__":
    os.chdir(BASE)
    accion = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if accion == "buscar":
        buscar()
    elif accion == "traducir":
        traducir()
    elif accion == "completar":
        completar()
    elif accion == "importar":
        importar(sys.argv[2])
    elif accion == "construir":
        construir()
    elif accion == "todo":
        buscar()
        if os.environ.get("ANTHROPIC_API_KEY"):
            traducir()
        else:
            print("Sin ANTHROPIC_API_KEY: se omite la traducción.")
        completar()
        construir()
    else:
        print(__doc__)
