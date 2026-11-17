from core.llm import pedir_json
from core.segmentador import segmentar_por_tema
from core.selector import (PERFILES, REGLAS_COMUNES, resolver_duracion,
                           detectar_tipo, _leer_puntaje, _es_verdadero)


def _a_indice(u):
    """Acepta 3, '3' o 'U3'."""
    if isinstance(u, int):
        return u
    return int("".join(ch for ch in str(u) if ch.isdigit()))


def _bloques(unidades, max_segundos=600):
    """Agrupa unidades consecutivas en bloques de ~10 min, con 1 unidad de solape."""
    bloques, inicio = [], 0
    while inicio < len(unidades):
        fin, total = inicio, 0
        while fin < len(unidades) and (total < max_segundos or fin == inicio):
            total += unidades[fin]["fin"] - unidades[fin]["inicio"]
            fin += 1
        bloques.append(list(range(inicio, fin)))
        if fin >= len(unidades):
            break
        inicio = fin - 1 if fin - 1 > inicio else fin
    return bloques


def _fin_en_frase(segmentos, limite, inicio):
    """El fin de frase más cercano sin pasarse del límite."""
    fines = [s["fin"] for s in segmentos if inicio < s["fin"] <= limite]
    return max(fines) if fines else limite


def _prompt(bloque, unidades, perfil, contexto, d_min, d_max, auto):
    p = PERFILES[perfil]
    extra_json = "".join(f', "{k}": true' for k in p["exigir"])
    extra_ctx = f"\nCONTEXTO DEL VIDEO (dado por el usuario): {contexto}\n" if contexto else ""
    if auto:
        linea = f"- Duración total del clip: la que necesite la historia, entre {d_min:.0f} y {d_max:.0f} segundos."
    else:
        linea = f"- Duración total ideal del clip: entre {d_min:.0f} y {d_max:.0f} segundos."
    texto = "\n\n".join(
        f"[U{i}] ({unidades[i]['inicio']:.0f}s a {unidades[i]['fin']:.0f}s, "
        f"{unidades[i]['fin'] - unidades[i]['inicio']:.0f}s)\n{unidades[i]['texto']}"
        for i in bloque
    )
    return f"""Eres un editor experto en clips virales para TikTok, Reels y Shorts.
Tipo de video: {perfil} - {p["descripcion"]}
{extra_ctx}
Abajo hay unidades numeradas (U0, U1, ...). Ya están separadas por tema y en orden cronológico. Cada una muestra su tiempo y su texto. La transcripción mezcla todas las voces: deduce por el contenido quién habla.

Un clip es UNA unidad o VARIAS unidades CONSECUTIVAS. Une unidades consecutivas solo si hablan de lo mismo y forman una historia continua (por ejemplo, un video que el creador va viendo por partes y comentando). Si una unidad sola ya es una historia completa, úsala sola. Nunca mezcles temas distintos.

Elige hasta 3 clips con estas reglas:
{linea}
{p["reglas"]}
{REGLAS_COMUNES}
- Si no hay nada realmente bueno, devuelve una lista vacía. Es mejor pocos clips buenos que muchos regulares.

Puntaje de 1 a 10: 9-10 es excelente, 7-8 es bueno, menos de 7 no lo incluyas.
Escribe primero "razon" (por qué funciona) y después el puntaje.

Responde SOLO con JSON con esta forma:
{{"clips": [{{"unidades": [0, 1], "titulo": "...", "razon": "...", "puntaje": 1{extra_json}}}]}}

UNIDADES:
{texto}"""


def elegir_momentos_por_unidades(segmentos, max_clips=5, tipo="auto", contexto="",
                                 duracion=None, relleno_antes=2.5, relleno_despues=2.5,
                                 sensibilidad=0.0, debug=True):
    # Primero los embeddings y después el modelo de texto, para que Ollama no cambie de modelo de más
    unidades = segmentar_por_tema(segmentos, sensibilidad=sensibilidad)

    if tipo == "auto":
        tipo = detectar_tipo(segmentos)
    if tipo not in PERFILES:
        tipo = "general"

    d_min, d_max = resolver_duracion(duracion, tipo)
    auto = duracion == "auto"
    p = PERFILES[tipo]
    fin_video = segmentos[-1]["fin"]
    print(f"[Selector] Tipo: {tipo} | duración: {d_min:.0f}-{d_max:.0f}s | {len(unidades)} unidades")

    candidatos = []
    for n, bloque in enumerate(_bloques(unidades), 1):
        try:
            respuesta = pedir_json(_prompt(bloque, unidades, tipo, contexto, d_min, d_max, auto))
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
                ids = sorted({_a_indice(u) for u in c["unidades"]})
                if not ids or any(i not in bloque for i in ids) or ids != list(range(ids[0], ids[-1] + 1)):
                    if debug:
                        print(f"   descartado (unidades inválidas {c.get('unidades')}): {c.get('titulo')}")
                    continue
                puntaje = _leer_puntaje(c)
                titulo = str(c.get("titulo", ""))
                razon = str(c.get("razon", ""))
            except (KeyError, ValueError, TypeError, AttributeError):
                if debug:
                    print(f"   descartado (formato inválido): {c}")
                continue

            if puntaje < 7:
                if debug:
                    print(f"   descartado (puntaje {puntaje} < 7): {titulo}")
                continue

            # Si se pasa del máximo, quita unidades del final (la idea queda completa, solo más corta)
            while len(ids) > 1 and unidades[ids[-1]]["fin"] - unidades[ids[0]]["inicio"] > d_max:
                ids.pop()
            inicio = unidades[ids[0]]["inicio"]
            fin = unidades[ids[-1]]["fin"]
            if fin - inicio > d_max:
                fin = _fin_en_frase(segmentos, inicio + d_max, inicio)

            duracion_final = fin - inicio
            if duracion_final < d_min * 0.7:
                if debug:
                    print(f"   descartado (quedó de {duracion_final:.0f}s): {titulo}")
                continue

            candidatos.append({
                "inicio": inicio, "fin": fin, "titulo": titulo, "razon": razon,
                "puntaje": puntaje, "corto": duracion_final < d_min,
            })

    # Mejores primero, sin solapes
    candidatos.sort(key=lambda c: c["puntaje"], reverse=True)
    elegidos = []
    for c in candidatos:
        if all(c["fin"] <= e["inicio"] or c["inicio"] >= e["fin"] for e in elegidos):
            elegidos.append(c)
    elegidos = elegidos[:max_clips]

    # Margen antes y después
    for c in elegidos:
        c["inicio"] = max(0.0, c["inicio"] - relleno_antes)
        c["fin"] = min(fin_video, c["fin"] + relleno_despues)

    return sorted(elegidos, key=lambda c: c["inicio"])