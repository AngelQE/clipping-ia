import json
import os

from core.selector_unidades import elegir_momentos_por_unidades
from core.transcripcion import transcribir, liberar_modelo
from core.selector import elegir_momentos
from core.cortador import cortar_clips, a_segundos
from core.llm import liberar_ollama


def _transcribir_con_cache(ruta_video):
    """Guarda la transcripción en cache/ para no repetirla si ya se hizo."""
    os.makedirs("cache", exist_ok=True)
    nombre = os.path.splitext(os.path.basename(ruta_video))[0]
    ruta_cache = os.path.join("cache", f"{nombre}.json")

    if os.path.exists(ruta_cache):
        print("[Cache] Usando transcripción guardada")
        with open(ruta_cache, encoding="utf-8") as f:
            return json.load(f)

    segmentos = transcribir(ruta_video)
    liberar_modelo()  # libera la GPU para Ollama
    with open(ruta_cache, "w", encoding="utf-8") as f:
        json.dump(segmentos, f, ensure_ascii=False)
    return segmentos


def procesar_video(ruta_video, tipo="auto", contexto="", formato="borroso", duracion=None,
                   max_clips=5, motor="unidades", relleno_antes=2.5, relleno_despues=2.5):
    """Proceso completo para UN video. motor: 'unidades' (nuevo) o 'clasico' (anterior)."""
    segmentos = _transcribir_con_cache(ruta_video)
    if motor == "unidades":
        clips = elegir_momentos_por_unidades(
            segmentos, max_clips=max_clips, tipo=tipo, contexto=contexto, duracion=duracion,
            relleno_antes=relleno_antes, relleno_despues=relleno_despues,
        )
    else:
        clips = elegir_momentos(segmentos, max_clips=max_clips, tipo=tipo,
                                contexto=contexto, duracion=duracion)
    liberar_ollama()
    return cortar_clips(ruta_video, clips, formato=formato)


def modo_manual(ruta_video, tipo="auto", contexto="", formato="borroso", duracion=None,
                max_clips=5, motor="unidades", relleno_antes=2.5, relleno_despues=2.5):
    """Tú das el video y la IA elige los momentos."""
    return procesar_video(ruta_video, tipo, contexto, formato, duracion,
                          max_clips, motor, relleno_antes, relleno_despues)

def modo_rango(ruta_video, rangos, formato="borroso"):
    """Tú eliges los minutos exactos. rangos = [("05:12", "06:00"), ...]"""
    clips = []
    for i, (inicio, fin) in enumerate(rangos, 1):
        inicio, fin = a_segundos(inicio), a_segundos(fin)
        if fin <= inicio:
            print(f"[Rango {i}] El fin debe ser mayor que el inicio, se omite")
            continue
        clips.append({"inicio": inicio, "fin": fin, "titulo": f"manual_{i}"})
    return cortar_clips(ruta_video, clips, formato=formato)


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