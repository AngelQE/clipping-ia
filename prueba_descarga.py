from core.descarga import descargar
from core.pipeline import procesar_video

ruta = descargar("https://www.youtube.com/watch?v=XXXXXXXX", desde_min=2, hasta_min=12)
print("Descargado:", ruta)
procesar_video(ruta, tipo="auto", duracion="auto")