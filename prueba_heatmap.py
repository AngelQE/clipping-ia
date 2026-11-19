import json
import sys

from core.cortador import formatear_tiempo

ruta = sys.argv[1]   # por ejemplo: videos/ID_DEL_VIDEO.json
with open(ruta, encoding="utf-8") as f:
    datos = json.load(f)

mapa = datos.get("heatmap")
if not mapa:
    sys.exit("Este video no trae datos de 'más reproducido' (puede faltar en videos recientes o con pocas vistas).")

print(f"{datos['titulo']} | canal: {datos['canal']}\n")
mejores = sorted(mapa, key=lambda p: p["value"], reverse=True)[:8]
for p in sorted(mejores, key=lambda p: p["start_time"]):
    print(f"{formatear_tiempo(p['start_time'])} → {formatear_tiempo(p['end_time'])}   intensidad {p['value']:.2f}")