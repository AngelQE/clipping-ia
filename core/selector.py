from core.llm import pedir_json

REGLAS_COMUNES = """- El clip debe entenderse por sí solo, sin haber visto el resto del video.
- Debe empezar en una frase fuerte y completa (nunca con "y", "pero", "entonces" ni con un "eso" que se refiere a algo anterior) y terminar en una frase completa, de preferencia un remate, un chiste o una conclusión.
- Evita saludos, despedidas, pedir suscripciones o likes, patrocinios y tiempos muertos.
- "titulo": un gancho de máximo 8 palabras, como lo escribiría un creador de TikTok. No una descripción."""

PERFILES = {
    "general": {
        "descripcion": "Video con una o varias personas hablando, sin formato especial.",
        "duracion": (20, 60),
        "exigir": [],
        "reglas": (
            "- Estructura ideal: GANCHO (pregunta, afirmación polémica, historia o dato sorprendente) "
            "-> desarrollo -> REMATE o cierre.\n"
            "- Prefiere ideas completas con emoción, humor, conflicto o sorpresa."
        ),
    },
    "reaccion": {
        "descripcion": (
            "Un creador (youtuber, streamer o grupo) ve o escucha contenido ajeno -TikToks, videos, "
            "noticias, tráilers, música- y reacciona con emoción, burla, crítica o comentario. "
            "La reacción es lo central; el contenido ajeno se muestra para que se entienda a qué reacciona."
        ),
        "duracion": (30, 90),
        "exigir": ["incluye_contenido_original", "incluye_reaccion"],
        "reglas": (
            "- Un buen clip tiene tres partes en este orden: (1) PLANTEAMIENTO: el contenido original, "
            "lo que se cuenta o se muestra; (2) REACCIÓN: sorpresa, risa, indignación, burla o un "
            "comentario ingenioso del creador; (3) REMATE: un chiste, una conclusión o la frase más fuerte.\n"
            "- Es OBLIGATORIO que el clip incluya el contenido original Y la reacción juntos. Nunca elijas "
            "solo el contenido ajeno sin que el creador reaccione, ni solo comentarios sin que se entienda "
            "a qué reaccionan. Si el contenido original no se oye en la transcripción, el creador suele "
            "describirlo (\"mira, el tipo...\", \"dice que...\"): eso cuenta como contenido original.\n"
            "- Pistas del CONTENIDO ORIGINAL: una historia o narración en tercera persona, frases largas "
            "y seguidas con otro estilo (locución, guion), situaciones que se exponen sin opinión, "
            "diálogos de personas ajenas al creador.\n"
            "- Pistas de la REACCIÓN (en cualquier idioma): interjecciones (\"no puede ser\", \"¿qué?\", "
            "\"no way\", \"what?!\", \"oh my god\", \"bro\", \"haha\"), preguntas retóricas, opiniones en primera "
            "persona (\"yo creo\", \"I think\", \"that's crazy\"), burlas, comparaciones, comentarios dirigidos a "
            "la audiencia o al chat. Ojo: la transcripción a veces omite risas y gritos.\n"
            "- Los mejores clips: reacción intensa y auténtica, comentario muy gracioso, o un contraste "
            "fuerte entre lo absurdo del original y la reacción.\n"
            "- Evita: que el creador hable de otros temas (saludos, suscripciones, patrocinios), lectura "
            "del chat sin gracia, repeticiones, y cortes en medio del contenido original antes de que se entienda."
        ),
        "ejemplo": (
            "EJEMPLO (inventado, solo para mostrar el formato; no copies sus datos):\n"
            "[200] Y el señor del video construye un barco con botellas de plástico\n"
            "[208] dice que lleva tres meses juntando botellas y que va a cruzar el río con eso\n"
            "[221] Que no necesita motor, que con la corriente le alcanza, que ya lo calculó todo\n"
            "[234] Espera, espera, ¿con eso? ¿Y no se hunde?\n"
            "[238] No puede ser, o sea, ni siquiera le puso un remo. Jajaja\n"
            "[246] Bro, a ver, ¿y si se moja la mochila qué? Esto es lo más absurdo que he visto hoy\n"
            "[262] y lo mejor es que el tipo sigue convencido de que va a llegar\n"
            "Respuesta esperada:\n"
            '{"clips": [{"inicio": 200, "fin": 266, "titulo": "Cruza el río en un barco de botellas", '
            '"razon": "Planteamiento claro del barco, reacción de incredulidad y remate gracioso", '
            '"puntaje": 9, "incluye_contenido_original": true, "incluye_reaccion": true}]}'
        ),
    },
    "podcast": {
        "descripcion": "Conversación o entrevista entre dos o más personas.",
        "duracion": (30, 90),
        "exigir": [],
        "reglas": (
            "- Estructura ideal: PROVOCACIÓN o pregunta -> respuesta, anécdota u opinión fuerte -> "
            "REMATE (frase memorable, chiste o conclusión).\n"
            "- Elige anécdotas con inicio, nudo y desenlace, opiniones polémicas, confesiones, datos "
            "sorprendentes, desacuerdos entre los participantes y momentos graciosos.\n"
            "- Incluye la pregunta o el contexto mínimo que provoca el momento. Evita lo que depende de "
            "algo dicho antes (\"como te decía\", \"eso que mencionamos\").\n"
            "- Evita presentaciones, publicidad, charla de relleno y despedidas."
        ),
    },
    "stream": {
        "descripcion": "Transmisión en vivo de un streamer (juegos, chat, anécdotas).",
        "duracion": (20, 60),
        "exigir": [],
        "reglas": (
            "- Busca picos de emoción: gritos, risas, sustos, jugadas épicas, fallos graciosos, "
            "reacciones a donaciones o al chat.\n"
            "- Estructura ideal: PREPARACIÓN (qué intenta hacer o qué pasa) -> MOMENTO CLAVE -> REACCIÓN del streamer.\n"
            "- Que se entienda qué ocurrió sin ver la pantalla: si el streamer no lo explica, el momento es débil.\n"
            "- Evita tiempos muertos, pantallas de carga, lectura del chat sin gracia, silencios y charla técnica."
        ),
    },
    "tutorial": {
        "descripcion": "Explicación o clase donde alguien enseña algo.",
        "duracion": (30, 90),
        "exigir": [],
        "reglas": (
            "- Elige UN solo consejo, truco o idea que se entienda completo por sí solo.\n"
            "- Estructura ideal: PROBLEMA o pregunta (\"¿cómo...?\", \"el error más común es...\") -> "
            "EXPLICACIÓN en pocos pasos -> RESULTADO o conclusión.\n"
            "- Prefiere explicaciones con un dato concreto, un ejemplo o un antes y después.\n"
            "- Evita introducciones, \"antes de empezar\", pedir suscripciones y pasos a medias."
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
        clave = duracion.strip().lower()
        if clave not in DURACIONES:
            print(f"[Selector] La duración '{duracion}' no existe (opciones: {', '.join(DURACIONES)}). "
                  f"Uso la del perfil.")
            return PERFILES[perfil]["duracion"]
        return DURACIONES[clave]
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
    ejemplo = f"\n{p['ejemplo']}\n" if p.get("ejemplo") else ""
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
{REGLAS_COMUNES}
- Si no hay nada realmente bueno, devuelve una lista vacía. Es mejor pocos clips buenos que muchos regulares.
{ejemplo}
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
    auto = isinstance(duracion, str) and duracion.strip().lower() == "auto"
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

            if duracion_final < d_min * 0.7:
                if debug:
                    print(f"   descartado (quedó de {duracion_final:.0f}s): {clip['titulo']}")
                continue
            # Marca los que quedaron bajo la duración preferente, para la pantalla de aprobación
            clip["corto"] = duracion_final < d_min
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