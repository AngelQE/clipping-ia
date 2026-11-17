import json
import sys

from core.segmentador import segmentar_por_tema
from core.cortador import formatear_tiempo

nombre = sys.argv[1] if len(sys.argv) > 1 else "prueba"
sensibilidad = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5

with open(f"cache/{nombre}.json", encoding="utf-8") as f:
    segmentos = json.load(f)

unidades = segmentar_por_tema(segmentos, sensibilidad=sensibilidad)
print(f"{len(unidades)} unidades (sensibilidad {sensibilidad})\n")
for u in unidades:
    dur = u["fin"] - u["inicio"]
    print(f"[{formatear_tiempo(u['inicio'])} → {formatear_tiempo(u['fin'])}] ({dur:.0f}s) {u['texto'][:110]}...")