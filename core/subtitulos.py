import os
import re
import textwrap

ESTILO_DEFECTO = {
    "fuente": "Arial",             # nombre de una fuente instalada (se ignora si das "archivo_fuente")
    "archivo_fuente": None,        # ruta a un .ttf/.otf propio, por ejemplo "C:/fuentes/MiFuente.ttf"
    "tamano": 56,                  # número: píxeles en un video de 1080 de ancho
    "color_texto": "#FFFFFF",
    "color_resaltado": "#FFFF00",  # color de la palabra que se dice
    "color_borde": "#000000",
    "grosor_borde": 5,             # píxeles (referencia 1080)
    "negrita": True,
    "mayusculas": True,
    "resaltar": True,              # False = todo el grupo del mismo color
    "max_palabras": 4,
    "posicion": 27,                # distancia desde abajo, en % de la altura
}

TITULO_DEFECTO = {
    "texto": "",
    "fuente": None,                # None = la misma que los subtítulos
    "archivo_fuente": None,
    "tamano": 64,
    "color_texto": "#FFFFFF",
    "color_borde": "#000000",
    "grosor_borde": 6,
    "negrita": True,
    "mayusculas": False,
    "posicion": 16,                # distancia desde ARRIBA, en % de la altura
    "x": None,                     # % del ancho donde queda el CENTRO del título (None = centrado arriba)
    "y": None,                     # % del alto donde queda el CENTRO del título
    "duracion": None,              # None = todo el clip; o segundos desde el inicio
    "max_lineas": 3,
}

_PRESETS_TAMANO = {"pequeno": 48, "mediano": 56, "grande": 72}


def _bgr(color, defecto):
    """'#RRGGBB' -> 'BBGGRR', el orden que usa ASS."""
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(color).strip())
    if not m:
        print(f"[Subtítulos] Color '{color}' no válido (usa #RRGGBB). Uso {defecto}.")
        m = re.fullmatch(r"#?([0-9a-fA-F]{6})", defecto)
    rr, gg, bb = m.group(1)[0:2], m.group(1)[2:4], m.group(1)[4:6]
    return f"{bb}{gg}{rr}".upper()


def nombre_de_fuente(archivo):
    """Nombre de familia de un .ttf/.otf (lo que ASS necesita). Usa fonttools."""
    try:
        from fontTools.ttLib import TTFont
        nombre = TTFont(archivo, fontNumber=0)["name"].getDebugName(1)
        if nombre:
            return nombre
    except Exception as e:
        print(f"[Subtítulos] No pude leer el nombre de la fuente ({e}). Uso el nombre del archivo.")
    return os.path.splitext(os.path.basename(archivo))[0]


def _t(segundos):
    """Formato de tiempo de ASS: H:MM:SS.cc"""
    cs = int(round(max(0.0, segundos) * 100))
    h, resto = divmod(cs, 360000)
    m, resto = divmod(resto, 6000)
    s, cs = divmod(resto, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _limpiar(texto, mayusculas):
    texto = re.sub(r"[.,;:]+$", "", texto.strip())
    return texto.upper() if mayusculas else texto


def _agrupar(palabras, max_palabras=4, max_chars=20, pausa=0.6):
    """Junta las palabras en grupos cortos: cortan las pausas, los finales de frase y el largo."""
    grupos, actual = [], []
    for p in palabras:
        if actual:
            hay_pausa = p["inicio"] - actual[-1]["fin"] > pausa
            fin_frase = actual[-1]["texto_original"].endswith((".", "?", "!"))
            largo = len(" ".join(w["texto"] for w in actual + [p]))
            if hay_pausa or fin_frase or len(actual) >= max_palabras or largo > max_chars:
                grupos.append(actual)
                actual = []
        actual.append(p)
    if actual:
        grupos.append(actual)
    return grupos


def _lineas_titulo(texto, max_chars, max_lineas):
    """Parte el título en líneas; si no cabe, lo recorta con puntos suspensivos."""
    texto = " ".join(str(texto).split()).replace("{", "(").replace("}", ")").replace("\\", "")
    lineas = textwrap.wrap(texto, width=max_chars) or [texto]
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = lineas[-1].rstrip(" .,;:") + "…"
    return lineas


def crear_ass(palabras, ruta_ass, ancho, alto, estilo=None, titulo=None, duracion_clip=None):
    """Crea un .ass con subtítulos estilo TikTok y/o un título fijo.
    'estilo' pisa ESTILO_DEFECTO y 'titulo' pisa TITULO_DEFECTO.
    Devuelve True si había algo que mostrar."""
    e = {**ESTILO_DEFECTO, **(estilo or {})}
    t = {**TITULO_DEFECTO, **titulo} if titulo else None
    if t and not str(t.get("texto") or "").strip():
        t = None

    limpias = []
    for p in palabras or []:
        texto = _limpiar(p["texto"], e["mayusculas"])
        if texto:
            limpias.append({"inicio": p["inicio"], "fin": p["fin"], "texto": texto,
                            "texto_original": p["texto"].strip()})
    if not limpias and not t:
        return False

    fuente = nombre_de_fuente(e["archivo_fuente"]) if e["archivo_fuente"] else e["fuente"]

    base = min(ancho, alto)
    tamano = e["tamano"]
    if isinstance(tamano, str):                      # compatibilidad con "pequeno" / "mediano" / "grande"
        tamano = _PRESETS_TAMANO.get(tamano.strip().lower().replace("ñ", "n"), 56)
    tam = max(20, int(tamano * base / 1080))
    borde = max(0, int(e["grosor_borde"] * base / 1080))
    margen_v = int(alto * e["posicion"] / 100)
    margen_h = int(ancho * 0.06)
    max_chars = int(max(14, min(28, (ancho * 0.88) / (tam * 0.62))))

    c_texto = _bgr(e["color_texto"], ESTILO_DEFECTO["color_texto"])
    c_resalte = _bgr(e["color_resaltado"], ESTILO_DEFECTO["color_resaltado"])
    c_borde = _bgr(e["color_borde"], ESTILO_DEFECTO["color_borde"])

    eventos = []
    grupos = _agrupar(limpias, max_palabras=int(e["max_palabras"]), max_chars=max_chars)
    for g_idx, grupo in enumerate(grupos):
        siguiente = grupos[g_idx + 1][0]["inicio"] if g_idx + 1 < len(grupos) else None

        if not e["resaltar"]:
            inicio = grupo[0]["inicio"]
            fin = grupo[-1]["fin"] + 0.2
            if siguiente is not None:
                fin = min(fin, siguiente)
            texto = " ".join(w["texto"] for w in grupo)
            eventos.append(f"Dialogue: 0,{_t(inicio)},{_t(max(fin, inicio + 0.1))},Default,,0,0,0,,{texto}")
            continue

        for i, palabra in enumerate(grupo):
            inicio = palabra["inicio"]
            if i + 1 < len(grupo):
                fin = grupo[i + 1]["inicio"]
            else:
                fin = palabra["fin"] + 0.2
                if siguiente is not None:
                    fin = min(fin, siguiente)
            fin = max(fin, inicio + 0.08)
            texto = " ".join(
                (f"{{\\c&H{c_resalte}&}}{w['texto']}{{\\c&H{c_texto}&}}" if j == i else w["texto"])
                for j, w in enumerate(grupo)
            )
            eventos.append(f"Dialogue: 0,{_t(inicio)},{_t(fin)},Default,,0,0,0,,{texto}")

    negrita = -1 if e["negrita"] else 0
    estilos = [
        f"Style: Default,{fuente},{tam},&H00{c_texto},&H00{c_texto},&H00{c_borde},&H80000000,"
        f"{negrita},0,0,0,100,100,0,0,1,{borde},0,2,{margen_h},{margen_h},{margen_v},1"
    ]

    if t:
        fuente_t = nombre_de_fuente(t["archivo_fuente"]) if t["archivo_fuente"] else (t["fuente"] or fuente)
        tam_t = max(20, int(t["tamano"] * base / 1080))
        borde_t = max(0, int(t["grosor_borde"] * base / 1080))
        margen_v_t = int(alto * t["posicion"] / 100)
        max_chars_t = int(max(10, min(32, (ancho * 0.86) / (tam_t * 0.58))))
        c_texto_t = _bgr(t["color_texto"], TITULO_DEFECTO["color_texto"])
        c_borde_t = _bgr(t["color_borde"], TITULO_DEFECTO["color_borde"])
        negrita_t = -1 if t["negrita"] else 0

        texto_t = str(t["texto"]).upper() if t["mayusculas"] else str(t["texto"])
        texto_t = "\\N".join(_lineas_titulo(texto_t, max_chars_t, int(t["max_lineas"])))

        fin_t = float(duracion_clip) if duracion_clip else 3600.0
        fundido = "\\fad(250,250)" if t["duracion"] else "\\fad(250,0)"
        if t["duracion"]:
            fin_t = min(fin_t, float(t["duracion"]))
        if t["x"] is not None and t["y"] is not None:
            # Posición libre: el centro del título va en (x%, y%) del video
            pos_x = int(ancho * float(t["x"]) / 100)
            pos_y = int(alto * float(t["y"]) / 100)
            efecto = f"{{\\an5\\pos({pos_x},{pos_y}){fundido}}}"
        else:
            efecto = f"{{{fundido}}}"

        estilos.append(
            f"Style: Titulo,{fuente_t},{tam_t},&H00{c_texto_t},&H00{c_texto_t},&H00{c_borde_t},&H80000000,"
            f"{negrita_t},0,0,0,100,100,0,0,1,{borde_t},0,8,{margen_h},{margen_h},{margen_v_t},1"
        )
        eventos.append(f"Dialogue: 1,{_t(0)},{_t(fin_t)},Titulo,,0,0,0,,{efecto}{texto_t}")

    estilos_txt = "\n".join(estilos)
    cabecera = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {ancho}
PlayResY: {alto}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{estilos_txt}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(ruta_ass, "w", encoding="utf-8") as f:
        f.write(cabecera + "\n".join(eventos) + "\n")
    return True