from core.descarga import descargar
from core.pipeline import procesar_video

URL = "https://www.youtube.com/watch?v=JedNRjkzidM"   # sin punto ni espacios al final

ruta = descargar(URL, desde_min=2, hasta_min=5)
if ruta:
    print("Descargado:", ruta)
    procesar_video(ruta, tipo="auto", duracion="auto")