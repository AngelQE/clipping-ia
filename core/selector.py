from core.llm import pedir_json

PERFILES = {
    "general": {
        "descripcion": "Video con una o varias personas hablando, sin formato especial.",
        "duracion": (20, 60),
        "exigir": [],
        "reglas": (
            "- Empieza con un gancho fuerte (pregunta, afirmación polémica, historia, dato sorprendente).\n"
            "- Tiene la idea completa y termina con cierre."
        ),
    },
    "reaccion": {
        "descripcion": "Un creador ve o escucha contenido ajeno (TikToks, videos, clips) y reacciona o comenta.",
        "duracion": (30, 90),
        "exigir": ["incluye_contenido_original", "incluye_reaccion"],
        "reglas": (
            "- Es un VIDEO DE REACCIÓN. Un buen clip SIEMPRE tiene las DOS partes juntas: "
            "(1) el momento del contenido original que se muestra y (2) la reacción o comentario del creador a ese contenido.\n"
            "- NUNCA elijas un fragmento que sea solo el contenido original sin que el creador reaccione, "
            "ni uno que sea solo comentario sin que se entienda a qué reacciona.\n"
            "- Pistas del contenido original: suena como otra persona, narración o historia ajena. "
            "Pistas de la reacción: risas, exclamaciones, opiniones en primera persona ('no puede ser', 'yo creo', 'qué fuerte').\n"
            "- Las mejores reacciones son las más intensas: sorpresa, risa, indignación o un comentario gracioso."
        ),
    },
    "podcast": {
        "descripcion": "Conversación o entrevista entre dos o más personas.",
        "duracion": (30, 90),
        "exigir": [],
        "reglas": (
            "- Elige historias completas, opiniones fuertes, confesiones, debates o momentos graciosos.\n"
            "- Que se entienda sin haber visto el resto: incluye la pregunta o el contexto que lo provoca.\n"
            "- Evita presentaciones, saludos y charla de relleno."
        ),
    },
    "stream": {
        "descripcion": "Transmisión en vivo de un streamer (juegos, chat, anécdotas).",
        "duracion": (20, 60),
        "exigir": [],
        "reglas": (
            "- Busca picos de emoción: gritos, risas, sustos, jugadas épicas, anécdotas graciosas.\n"
            "- Evita tiempos muertos, lectura del chat sin gracia y silencios."
        ),
    },
    "tutorial": {
        "descripcion": "Explicación o clase donde alguien enseña algo.",
        "duracion": (30, 90),
        "exigir": [],
        "reglas": (
            "- Elige un solo consejo, truco o idea que se entienda completo por sí solo.\n"
            "- Debe empezar planteando el problema o la pregunta y terminar con la solución."
        ),
    },
}

DURACIONES = {
    "corto": (15, 30),
    "medio": (30, 60),
    "largo": (60, 120),
    "auto": (15, 120),
}


def resolver_duracion(duracion, perfil):
    """None -> la del perfil | 'corto'/'medio'/'largo'/'auto' | (min, max) en segundos."""
    if duracion is None:
        return PERFILES[perfil]["duracion"]
    if isinstance(duracion, str):
        return DURACIONES.get(duracion, PERFILES[perfil]["duracion"])
    d_min, d_max = duracion
    return (float(d_min), float(d_max))

def _trozos(segmentos, duracion=600, solape=60):
    """Divide la transcripción en bloques de ~10 min con 1 min de solape."""
    if not segmentos:
        return []
    fin_total = segmentos[-1]["fin"]
    trozos, inicio = [], 0
    while inicio < fin_total:
        fin = inicio + duracion
        parte = [s for s in segmentos if inicio <= s["inicio"] < fin]
        if parte:
            trozos.append(parte)
        inicio = fin - solape
    return trozos


def detectar_tipo(segmentos):
    """Mini agente analista: mira tres muestras del video y decide de qué tipo es."""
    n = len(segmentos)
    if n == 0:
        return "general"
    puntos = [0, n // 2, max(0, n - 15)]
    muestra = "\n---\n".join(
        " ".join(s["texto"] for s in segmentos[p:p + 15]) for p in puntos
    )
    opciones = "\n".join(f'- "{k}": {v["descripcion"]}' for k, v in PERFILES.items())
    prompt = f"""Clasifica este video según su transcripción (tres fragmentos del inicio, medio y final).

Tipos posibles:
{opciones}

Responde SOLO con JSON: {{"tipo": "uno_de_los_tipos"}}

FRAGMENTOS:
{muestra}"""
    try:
        tipo = pedir_json(prompt).get("tipo", "general")
    except Exception:
        return "general"
    return tipo if tipo in PERFILES else "general"


def _prompt(parte, perfil, contexto, d_min, d_max, auto=False):
    p = PERFILES[perfil]
    texto = "\n".join(f"[{int(s['inicio'])}] {s['texto']}" for s in parte)
    extra_json = "".join(f', "{k}": true' for k in p["exigir"])
    extra_ctx = f"\nCONTEXTO DEL VIDEO (dado por el usuario): {contexto}\n" if contexto else ""
    if auto:
        linea_duracion = (
            f"- Duración: la que necesite cada idea para entenderse completa, entre "
            f"{d_min:.0f} y {d_max:.0f} segundos. No rellenes ni cortes la idea a la mitad."
        )
    else:
        linea_duracion = f"- Duración ideal entre {d_min:.0f} y {d_max:.0f} segundos."
    return f"""Eres un editor experto en clips virales para TikTok, Reels y Shorts.
Tipo de video: {perfil} - {p["descripcion"]}
{extra_ctx}
Abajo está la transcripción. Cada línea empieza con el segundo en que se dice.
La transcripción mezcla todas las voces: tú debes deducir por el contenido quién habla y qué es qué.

Elige hasta 3 fragmentos que funcionen solos como clip, con estas reglas:
{linea_duracion}
- Si el momento clave es corto, márcalo igual: el sistema le añadirá el contexto necesario antes y después.
{p["reglas"]}
- Si no hay nada realmente bueno, devuelve una lista vacía. Es mejor pocos clips buenos que muchos regulares.

Puntaje de 1 a 10: 9-10 es excelente, 7-8 es bueno, menos de 7 no lo incluyas.
Escribe primero "razon" (por qué funciona) y después el puntaje.

Responde SOLO con JSON con esta forma:
{{"clips": [{{"inicio": 0, "fin": 0, "titulo": "...", "razon": "...", "puntaje": 1{extra_json}}}]}}
"inicio" y "fin" son segundos tomados de la transcripción.

TRANSCRIPCIÓN:
{texto}"""


def _ajustar(clip, segmentos):
    """Pega el inicio y el fin a los límites reales de las frases."""
    inicios = [s["inicio"] for s in segmentos]
    fines = [s["fin"] for s in segmentos]
    clip["inicio"] = min(inicios, key=lambda t: abs(t - clip["inicio"]))
    clip["fin"] = min(fines, key=lambda t: abs(t - clip["fin"]))
    return clip


def _es_verdadero(valor):
    return valor is True or str(valor).strip().lower() == "true"

def _leer_puntaje(c):
    """Lee el puntaje aunque el modelo escriba mal la clave (ej: 'punt,aje')."""
    for k, v in c.items():
        if str(k).replace(",", "").replace(" ", "").lower().startswith("punt"):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _expandir(clip, segmentos, d_min, d_max):
    """Si el clip es corto le suma contexto (60% antes, 40% después);
    si es largo lo recorta. Luego pega los bordes a los límites de las frases."""
    fin_video = segmentos[-1]["fin"]
    inicio, fin = clip["inicio"], clip["fin"]
    duracion = fin - inicio

    if duracion < d_min:
        faltan = d_min - duracion
        inicio_nuevo = inicio - faltan * 0.6
        fin_nuevo = fin + faltan * 0.4
        # Si nos pasamos del inicio o del final del video, compensamos del otro lado
        if inicio_nuevo < 0:
            fin_nuevo += -inicio_nuevo
            inicio_nuevo = 0
        if fin_nuevo > fin_video:
            inicio_nuevo = max(0, inicio_nuevo - (fin_nuevo - fin_video))
            fin_nuevo = fin_video
        inicio, fin = inicio_nuevo, fin_nuevo
    elif duracion > d_max:
        fin = inicio + d_max

    clip["inicio"], clip["fin"] = inicio, fin
    return _ajustar(clip, segmentos)

def elegir_momentos(segmentos, max_clips=5, tipo="auto", contexto="", duracion=None, debug=True):
    if tipo == "auto":
        tipo = detectar_tipo(segmentos)
    if tipo not in PERFILES:
        tipo = "general"

    d_min, d_max = resolver_duracion(duracion, tipo)
    auto = duracion == "auto"
    p = PERFILES[tipo]
    print(f"[Selector] Tipo: {tipo} | duración: {d_min:.0f}-{d_max:.0f}s | {len(segmentos)} segmentos")
    candidatos = []

    for n, parte in enumerate(_trozos(segmentos), 1):
        try:
            respuesta = pedir_json(_prompt(parte, tipo, contexto, d_min, d_max, auto))
        except Exception as e:
            print(f"[Bloque {n}] Error: {e}")
            continue
        if debug:
            print(f"[Bloque {n}] Respuesta cruda: {respuesta}")

        lista = respuesta.get("clips", []) if isinstance(respuesta, dict) else respuesta
        for c in lista:
            try:
                faltan = [k for k in p["exigir"] if not _es_verdadero(c.get(k))]
                if faltan:
                    if debug:
                        print(f"   descartado (no cumple {faltan}): {c.get('titulo')}")
                    continue
                clip = {
                    "inicio": float(c["inicio"]),
                    "fin": float(c["fin"]),
                    "titulo": str(c.get("titulo", "")),
                    "razon": str(c.get("razon", "")),
                    "puntaje": _leer_puntaje(c),
                }
            except (KeyError, ValueError, TypeError, AttributeError):
                if debug:
                    print(f"   descartado (formato inválido): {c}")
                continue

            if clip["puntaje"] < 7:
                if debug:
                    print(f"   descartado (puntaje {clip['puntaje']} < 7): {clip['titulo']}")
                continue

            duracion_modelo = clip["fin"] - clip["inicio"]
            clip = _expandir(clip, segmentos, d_min, d_max)
            duracion_final = clip["fin"] - clip["inicio"]
            if debug and abs(duracion_final - duracion_modelo) > 1:
                print(f"   ajustado {duracion_modelo:.0f}s -> {duracion_final:.0f}s: {clip['titulo']}")

            if duracion_final < d_min - 8:
                if debug:
                    print(f"   descartado (quedó de {duracion_final:.0f}s): {clip['titulo']}")
                continue
            candidatos.append(clip)

    candidatos.sort(key=lambda c: c["puntaje"], reverse=True)
    elegidos = []
    for c in candidatos:
        if all(c["fin"] <= e["inicio"] or c["inicio"] >= e["fin"] for e in elegidos):
            elegidos.append(c)
    return sorted(elegidos[:max_clips], key=lambda c: c["inicio"])

    # Mejores primero, descartando los que se solapan con uno ya elegido
    candidatos.sort(key=lambda c: c["puntaje"], reverse=True)
    elegidos = []
    for c in candidatos:
        if all(c["fin"] <= e["inicio"] or c["inicio"] >= e["fin"] for e in elegidos):
            elegidos.append(c)
    return sorted(elegidos[:max_clips], key=lambda c: c["inicio"])