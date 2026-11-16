import yt_dlp
from yt_dlp.utils import download_range_func


def descargar(url, carpeta="videos", desde_min=None, hasta_min=None):
    """Descarga un video, o solo un tramo (en minutos) si se indican desde/hasta."""
    opciones = {
        "format": "bv*[height<=1080]+ba/b[height<=1080]",
        "merge_output_format": "mp4",
    }
    sufijo = ""
    if desde_min is not None or hasta_min is not None:
        inicio = (desde_min or 0) * 60
        fin = hasta_min * 60 if hasta_min is not None else float("inf")
        opciones["download_ranges"] = download_range_func(None, [(inicio, fin)])
        opciones["force_keyframes_at_cuts"] = True
        # El nombre incluye el tramo para que la caché de transcripción no se mezcle
        sufijo = f"_{int(inicio)}-{'fin' if hasta_min is None else int(fin)}"
    opciones["outtmpl"] = f"{carpeta}/%(id)s{sufijo}.%(ext)s"

    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp4"