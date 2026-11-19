import hashlib
import json
import os

from core.transcripcion import transcribir, liberar_modelo, MODELO_WHISPER
from core.selector import elegir_momentos
from core.selector_unidades import elegir_momentos_por_unidades
from core.cortador import cortar_clips, a_segundos
from core.llm import liberar_ollama

NOMBRES_IDIOMA = {"es": "español", "en": "inglés", "pt": "portugués",
                  "fr": "francés", "de": "alemán", "it": "italiano"}

def _huella(ruta_video, idioma):
    """Identifica el contenido del video (no solo su nombre) para que la caché nunca se mezcle."""
    h = hashlib.sha1()
    estado = os.stat(ruta_video)
    h.update(f"{estado.st_size}|{estado.st_mtime_ns}|{MODELO_WHISPER}|{idioma}".encode())
    with open(ruta_video, "rb") as f:
        h.update(f.read(1024 * 1024))
    return h.hexdigest()[:10]


def _transcribir_con_cache(ruta_video, idioma=None, forzar=False):
    """Devuelve (segmentos, idioma). La caché se identifica por el contenido del video."""
    os.makedirs("cache", exist_ok=True)
    nombre = os.path.splitext(os.path.basename(ruta_video))[0]
    ruta_cache = os.path.join("cache", f"{nombre}_{_huella(ruta_video, idioma)}.json")

    if os.path.exists(ruta_cache) and not forzar:
        print("[Cache] Usando transcripción guardada")
        with open(ruta_cache, encoding="utf-8") as f:
            datos = json.load(f)
        return datos["segmentos"], datos["idioma"]

    segmentos, idioma_detectado = transcribir(ruta_video, idioma=idioma)
    liberar_modelo()  # libera la GPU para Ollama
    with open(ruta_cache, "w", encoding="utf-8") as f:
        json.dump({"idioma": idioma_detectado, "segmentos": segmentos}, f, ensure_ascii=False)
    print(f"[Whisper] Idioma: {idioma_detectado}")
    return segmentos, idioma_detectado


def _contexto_con_idioma(contexto, idioma):
    """Le indica al modelo en qué idioma escribir el título."""
    nombre = NOMBRES_IDIOMA.get(idioma, idioma)
    nota = f"El video está en {nombre}. Escribe el campo 'titulo' en ese idioma y el campo 'razon' en español."
    return f"{contexto} {nota}".strip()

def procesar_video(ruta_video, tipo="auto", contexto="", formato="borroso", duracion=None,
                   max_clips=5, motor="unidades", relleno_antes=2.5, relleno_despues=2.5,
                   subtitulos=True, idioma=None, forzar=False, estilo_sub=None,
                   titulo_en_video=None):
    """Proceso completo para UN video. idioma=None lo detecta; forzar=True ignora la caché."""
    segmentos, idioma = _transcribir_con_cache(ruta_video, idioma, forzar)
    if not segmentos:
        print("[Pipeline] No se detectó voz en el video.")
        return []
    contexto = _contexto_con_idioma(contexto, idioma)

    if motor == "unidades":
        clips = elegir_momentos_por_unidades(
            segmentos, max_clips=max_clips, tipo=tipo, contexto=contexto, duracion=duracion,
            relleno_antes=relleno_antes, relleno_despues=relleno_despues,
        )
    else:
        clips = elegir_momentos(segmentos, max_clips=max_clips, tipo=tipo,
                                contexto=contexto, duracion=duracion)
    liberar_ollama()
    archivos = cortar_clips(ruta_video, clips, formato=formato, subtitulos=subtitulos,
                            idioma=idioma, estilo_sub=estilo_sub, titulo_en_video=titulo_en_video)
    if subtitulos:
        liberar_modelo()
    return archivos


def modo_manual(ruta_video, tipo="auto", contexto="", formato="borroso", duracion=None,
                max_clips=5, motor="unidades", relleno_antes=2.5, relleno_despues=2.5,
                subtitulos=True, idioma=None, forzar=False, estilo_sub=None,
                titulo_en_video=None):
    """Tú das el video y la IA elige los momentos."""
    return procesar_video(ruta_video, tipo, contexto, formato, duracion, max_clips, motor,
                          relleno_antes, relleno_despues, subtitulos, idioma, forzar,
                          estilo_sub, titulo_en_video)


def modo_rango(ruta_video, rangos, formato="borroso", subtitulos=True, idioma=None,
               estilo_sub=None, titulo_en_video=None):
    """Tú eliges los minutos exactos. rangos = [("05:12", "06:00"), ...]
    Aquí titulo_en_video=True no tiene un título generado: usa un texto propio."""
    clips = []
    for i, (inicio, fin) in enumerate(rangos, 1):
        inicio, fin = a_segundos(inicio), a_segundos(fin)
        if fin <= inicio:
            print(f"[Rango {i}] El fin debe ser mayor que el inicio, se omite")
            continue
        clips.append({"inicio": inicio, "fin": fin, "titulo": f"manual_{i}"})
    archivos = cortar_clips(ruta_video, clips, formato=formato, subtitulos=subtitulos,
                            idioma=idioma, estilo_sub=estilo_sub, titulo_en_video=titulo_en_video)
    if subtitulos:
        liberar_modelo()
    return archivos


def modo_automatico(trabajo):
    """trabajo es un TrabajoAuto. Se completa en la fase de agentes."""
    # 1. cazador.buscar(trabajo.nicho, trabajo.max_videos,
    #                   trabajo.fuente_min_minutos, trabajo.fuente_max_minutos)
    #       -> lista de links con título, vistas y por qué es viral
    # 2. si trabajo.aprobar_links: esperar a que tú apruebes los links
    # 3. analista.perfil(trabajo.nicho) -> texto que se suma a trabajo.contexto
    # 4. por cada link:
    #       ruta = descargar(link, desde_min=trabajo.desde_min, hasta_min=trabajo.hasta_min)
    #       procesar_video(ruta, tipo=trabajo.tipo, contexto=contexto_final,
    #                      formato=trabajo.formato, duracion=trabajo.duracion,
    #                      max_clips=trabajo.max_clips)
    raise NotImplementedError("Se construye en la fase de agentes")