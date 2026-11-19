from core.descarga import descargar
from core.pipeline import procesar_video

URL = "https://www.youtube.com/watch?v=Gm5BJ07acMI"   # sin punto ni espacios al final

ruta = descargar(URL)
if ruta:
    print("Descargado:", ruta)
    procesar_video(ruta, tipo="auto", duracion="auto")