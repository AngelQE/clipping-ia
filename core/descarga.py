import json
import os

import yt_dlp
from yt_dlp.utils import DownloadError, download_range_func


def _guardar_metadatos(ruta_video, info, desplazamiento):
    """Guarda al lado del video datos útiles: créditos y, si existe, el mapa de 'más reproducido'."""
    datos = {
        "id": info.get("id"),
        "titulo": info.get("title"),
        "canal": info.get("uploader") or info.get("channel"),
        "url": info.get("webpage_url"),
        "duracion": info.get("duration"),
        "desplazamiento": desplazamiento,   # segundo del video original donde empieza este archivo
        "heatmap": info.get("heatmap"),     # lista de {start_time, end_time, value} (tiempos del video original), o None
    }
    with open(os.path.splitext(ruta_video)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def descargar(url, carpeta="videos", desde_min=None, hasta_min=None, cookies_navegador=None):
    """Descarga un video completo, o solo un tramo (en minutos). Devuelve la ruta, o None si falla.
    También guarda un .json con el título, el canal y los datos de audiencia si los hay.
    cookies_navegador: "chrome", "firefox", "edge"... solo si YouTube pide iniciar sesión."""
    opciones = {
        "format": "bv*[height<=1080]+ba/b[height<=1080]",
        "merge_output_format": "mp4",
    }
    if cookies_navegador:
        opciones["cookiesfrombrowser"] = (cookies_navegador,)

    sufijo = ""
    desplazamiento = 0.0
    if desde_min is not None or hasta_min is not None:
        inicio = (desde_min or 0) * 60
        fin = hasta_min * 60 if hasta_min is not None else float("inf")
        opciones["download_ranges"] = download_range_func(None, [(inicio, fin)])
        opciones["force_keyframes_at_cuts"] = True
        desplazamiento = float(inicio)
        # El nombre incluye el tramo para que la caché de transcripción no se mezcle
        sufijo = f"_{int(inicio)}-{'fin' if hasta_min is None else int(fin)}"
    opciones["outtmpl"] = f"{carpeta}/%(id)s{sufijo}.%(ext)s"

    try:
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            ruta = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp4"
    except DownloadError as e:
        mensaje = str(e)
        print(f"[Descarga] Falló: {mensaje}")
        if "not available" in mensaje or "unavailable" in mensaje.lower():
            print("  -> Prueba el video en el navegador sin iniciar sesión: puede ser privado, "
                  "eliminado, con restricción de país o de edad, o YouTube bloqueó la petición.")
        if "Sign in" in mensaje or "bot" in mensaje.lower():
            print("  -> YouTube pide verificación. Opción: descargar(url, cookies_navegador='chrome').")
        print("  -> Si falta el motor de JavaScript: instala Deno y actualiza yt-dlp.")
        return None

    _guardar_metadatos(ruta, info, desplazamiento)
    return ruta