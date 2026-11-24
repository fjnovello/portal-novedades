"""Configuración del Portal de Novedades Odontológicas de Consulmed.

Para sumar una fuente nueva alcanza con agregar una línea en FUENTES.
- rss(...)   : feed RSS/Atom directo del medio.
- gnews(...) : búsqueda de Google Noticias (sirve para medios que bloquean
               su RSS o no lo tienen, y para cubrir idiomas y países).
"""
from urllib.parse import quote_plus

# --- Datos del sitio -------------------------------------------------------
SITIO = {
    "nombre": "Novedades Odontológicas",
    "marca": "Consulmed",
    "lema": "Todo lo nuevo de la odontología mundial, en español",
    "url": "https://consulmed.com.ar/novedades",  # cambiar si se publica en otra dirección
    "url_consulmed": "https://consulmed.com.ar",
    "telefono": "(011) 5217-4400",
    "telefono_link": "tel:+541152174400",
    "facebook": "https://www.facebook.com/ConsulmedARG/",
    "instagram": "https://www.instagram.com/consulmedodontologia",
    # Dirección del formulario de alta del newsletter (por ejemplo, un formulario de Doppler).
    # Vacío = el portal muestra "próximamente" en lugar del formulario.
    "suscripcion_url": "",
    # Código de Google Tag Manager para medir visitas (ej.: el mismo que usa consulmed.com.ar).
    "gtm": "GTM-TK345L5",
}

# --- Secciones -------------------------------------------------------------
# slug: (nombre, descripción, color de fondo, ícono Font Awesome 4.7, color de texto)
SECCIONES = {
    "tecnologia": ("Tecnología e innovación",
                   "Odontología digital, inteligencia artificial, escáneres intraorales, CAD/CAM e impresión 3D.",
                   "#0054a6", "fa-microchip", "#ffffff"),
    "tratamientos": ("Tratamientos y clínica",
                     "Implantes, ortodoncia, endodoncia, periodoncia, estética y nuevas técnicas clínicas.",
                     "#448ccb", "fa-user-md", "#ffffff"),
    "lanzamientos": ("Lanzamientos",
                     "Nuevos productos, equipos, materiales y servicios para el consultorio y el paciente.",
                     "#f26522", "fa-rocket", "#ffffff"),
    "investigacion": ("Investigación científica",
                      "Estudios, ensayos clínicos y papers publicados en revistas de referencia.",
                      "#1b1464", "fa-flask", "#ffffff"),
    "industria": ("Industria y mercado",
                  "Empresas, adquisiciones, cadenas odontológicas, seguros dentales y financiamiento.",
                  "#05173d", "fa-line-chart", "#ffffff"),
    "salud-publica": ("Salud pública y regulación",
                      "Políticas sanitarias, aprobaciones regulatorias, prevención y epidemiología bucal.",
                      "#118408", "fa-balance-scale", "#ffffff"),
    "argentina": ("Argentina y Latinoamérica",
                  "Novedades de la odontología en Argentina y la región.",
                  "#6dcff6", "fa-map-marker", "#05173d"),
}
SECCION_POR_DEFECTO = "tratamientos"
SECCIONES_CORTO = {"tecnologia": "Tecnología", "tratamientos": "Tratamientos",
                   "lanzamientos": "Lanzamientos", "investigacion": "Investigación",
                   "industria": "Industria", "salud-publica": "Salud pública",
                   "argentina": "Argentina"}

IDIOMAS = {"en": "inglés", "es": "español", "pt": "portugués", "fr": "francés",
           "de": "alemán", "it": "italiano"}

# --- Notas completas --------------------------------------------------------
# Solo se publica la traducción COMPLETA cuando el texto lo permite:
#  - "comunicado": comunicados de prensa de empresas y universidades (se emiten para que los medios los publiquen).
#  - "cc-by": artículos científicos de acceso abierto con licencia Creative Commons Atribución.
#  - "dominio-publico": textos del gobierno de EE.UU. (FDA, NIH).
# Para cualquier otro medio se publica título, resumen propio y el acceso a la nota original traducida.
# Si un medio autoriza por escrito la traducción de sus notas, agregá su dominio acá con "autorizado".
LICENCIA_POR_DOMINIO = {
    "prnewswire.com": "comunicado", "businesswire.com": "comunicado", "globenewswire.com": "comunicado",
    "eurekalert.org": "comunicado", "newswire.ca": "comunicado", "einpresswire.com": "comunicado",
    "fda.gov": "dominio-publico", "nih.gov": "dominio-publico", "cdc.gov": "dominio-publico",
    "plos.org": "cc-by", "frontiersin.org": "cc-by", "biomedcentral.com": "cc-by",
    "nature.com/articles/s41368": "cc-by", "nature.com/articles/s41405": "cc-by",
}
LICENCIAS = {
    "comunicado": "Comunicado de prensa difundido por {fuente} para su publicación en medios. Traducción completa al español: Consulmed.",
    "cc-by": "Artículo de acceso abierto publicado por {fuente} bajo licencia Creative Commons Atribución 4.0 (CC BY 4.0), que permite su traducción citando la fuente. Se traduce el resumen científico (abstract). Traducción: Consulmed.",
    "dominio-publico": "Texto oficial de dominio público publicado por {fuente}. Traducción completa al español: Consulmed.",
    "autorizado": "Nota traducida y publicada con autorización de {fuente}. Traducción: Consulmed.",
}
MAX_NOTAS_COMPLETAS_POR_CORRIDA = 40
MAX_PALABRAS_NOTA_COMPLETA = 2500

# --- Parámetros del proceso ------------------------------------------------
DIAS_ATRAS_PRIMERA_CARGA = 21     # en la primera corrida no trae nada más viejo que esto
MAX_NUEVOS_POR_CORRIDA = 150      # tope de notas a traducir por corrida (controla el costo de la API)
LOTE_TRADUCCION = 8               # notas por llamada a la API
MODELO_CLAUDE = "claude-haiku-5-5"  # se puede cambiar con la variable de entorno CLAUDE_MODEL
NOTAS_POR_PAGINA = 24
MAX_IMAGENES_REDES = 400       # imágenes para compartir en redes: solo para las notas más recientes

# Palabras que confirman que una nota es de odontología (para fuentes generales)
PALABRAS_DENTALES = [
    "dental", "dentist", "teeth", "tooth", "oral health", "oral care", "orthodon", "implant",
    "periodon", "endodon", "caries", "cavity", "cavities", "gum disease", "aligner", "intraoral",
    "maxillofacial", "enamel", "denture", "odont", "dentaire", "dentiste", "zahn", "dientes",
    "diente", "bucal", "dentista", "dentário", "dentária", "denti", "gengiv", "encía", "encias",
    "ortodon", "implante", "periodont", "prótesis dental", "fluor", "fluoride", "mouth",
]

# --- Fuentes ---------------------------------------------------------------
def rss(nombre, url, idioma, region="mundo", filtrar=False, licencia=None):
    return {"nombre": nombre, "url": url, "idioma": idioma, "tipo": "rss",
            "region": region, "filtrar": filtrar, "licencia": licencia}


def gnews(consulta, idioma="en", pais="US", region="mundo", nombre=None, filtrar=True, licencia=None):
    ceid = {"en": "US:en", "es": "AR:es-419", "pt": "BR:pt-419", "fr": "FR:fr",
            "de": "DE:de", "it": "IT:it"}[idioma]
    hl = {"en": "en-US", "es": "es-419", "pt": "pt-BR", "fr": "fr", "de": "de", "it": "it"}[idioma]
    url = (f"https://news.google.com/rss/search?q={quote_plus(consulta + ' when:7d')}"
           f"&hl={hl}&gl={pais}&ceid={ceid}")
    return {"nombre": nombre or f"Google Noticias: {consulta}", "url": url, "idioma": idioma,
            "tipo": "gnews", "region": region, "filtrar": filtrar, "licencia": licencia}


FUENTES = [
    # Investigación
    rss("ScienceDaily", "https://www.sciencedaily.com/rss/health_medicine/dentistry.xml", "en"),
    rss("Medical Xpress", "https://medicalxpress.com/rss-feed/dentistry-news/", "en"),
    rss("British Dental Journal", "https://www.nature.com/bdj.rss", "en"),
    rss("Evidence-Based Dentistry", "https://www.nature.com/ebd.rss", "en"),
    rss("International Journal of Oral Science", "https://www.nature.com/ijos.rss", "en", licencia="cc-by"),
    rss("BDJ Open", "https://www.nature.com/bdjopen.rss", "en", licencia="cc-by"),
    rss("Frontiers in Dental Medicine", "https://www.frontiersin.org/journals/dental-medicine/rss", "en", licencia="cc-by"),
    rss("PLOS ONE", "https://journals.plos.org/plosone/feed/atom?q=dental", "en", filtrar=True, licencia="cc-by"),
    rss("FDA", "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml", "en", filtrar=True, licencia="dominio-publico"),
    # Medios profesionales
    rss("Dental Products Report", "https://www.dentalproductsreport.com/rss", "en"),
    rss("DentistryIQ", "https://www.dentistryiq.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D", "en"),
    rss("Dental Economics", "https://www.dentaleconomics.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22home%22%7D", "en"),
    rss("Dentistry (Reino Unido)", "https://dentistry.co.uk/feed/", "en"),
    rss("The Probe", "https://www.the-probe.co.uk/feed/", "en"),
    rss("Le Fil Dentaire", "https://www.lefildentaire.com/feed/", "fr"),
    rss("Information Dentaire", "https://www.information-dentaire.fr/feed/", "fr"),
    rss("Odontoiatria33", "https://www.odontoiatria33.it/rss.xml", "it"),
    rss("PR Newswire Salud", "https://www.prnewswire.com/rss/health-latest-news/health-latest-news-list.rss", "en", filtrar=True, licencia="comunicado"),
    # Comunicados de prensa de empresas y universidades (se publican traducidos completos)
    gnews("dental site:prnewswire.com", nombre="PR Newswire", licencia="comunicado"),
    gnews("dental site:businesswire.com", nombre="Business Wire", licencia="comunicado"),
    gnews("dental OR dentistry site:globenewswire.com", nombre="GlobeNewswire", licencia="comunicado"),
    gnews("dental OR teeth OR oral health site:eurekalert.org", nombre="EurekAlert!", licencia="comunicado"),
    # Medios que bloquean su RSS: se leen vía Google Noticias
    gnews("site:drbicuspid.com", nombre="DrBicuspid"),
    gnews("site:beckersdental.com", nombre="Becker's Dental + DSO Review"),
    gnews("site:dental-tribune.com", nombre="Dental Tribune"),
    gnews("site:adanews.ada.org", nombre="ADA News"),
    gnews("site:dentistrytoday.com", nombre="Dentistry Today"),
    gnews("site:zm-online.de", "de", "DE", nombre="zm-online"),
    # Búsquedas temáticas mundiales
    gnews("dental AI OR intraoral scanner OR dental 3D printing"),
    gnews("dental implant OR clear aligners OR orthodontics innovation"),
    gnews("FDA clearance dental"),
    gnews("dental product launch OR launches dental"),
    gnews("dental insurance OR dental service organization"),
    gnews("Zahnmedizin Innovation", "de", "DE"),
    gnews("innovation dentaire", "fr", "FR"),
    gnews("inovação odontologia", "pt", "BR", region="latam"),
    gnews("odontoiatria novità", "it", "IT"),
    # Argentina y Latinoamérica
    gnews("odontología Argentina", "es", "AR", region="ar"),
    gnews("odontólogos Argentina", "es", "AR", region="ar"),
    gnews("odontología ANMAT OR obra social odontología", "es", "AR", region="ar"),
    gnews("odontología novedades tratamiento", "es", "AR", region="latam"),
]
