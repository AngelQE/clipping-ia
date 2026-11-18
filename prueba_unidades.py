import glob
import json
import os
import sys

from core.cortador import formatear_tiempo
from core.segmentador import segmentar_por_tema

nombre = sys.argv[1] if len(sys.argv) > 1 else "prueba"
sensibilidad = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0

archivos = sorted(glob.glob(f"cache/{nombre}_*.json"), key=os.path.getmtime)
if not archivos:
    sys.exit(f"No hay transcripción guardada para '{nombre}'. Ejecuta main.py una vez con ese video.")

with open(archivos[-1], encoding="utf-8") as f:
    datos = json.load(f)
segmentos = datos["segmentos"]

unidades = segmentar_por_tema(segmentos, sensibilidad=sensibilidad)
print(f"{len(unidades)} unidades (sensibilidad {sensibilidad}) | idioma: {datos.get('idioma')}\n")
for u in unidades:
    dur = u["fin"] - u["inicio"]
    print(f"[{formatear_tiempo(u['inicio'])} → {formatear_tiempo(u['fin'])}] ({dur:.0f}s) {u['texto'][:110]}...")