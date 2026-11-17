import re
import subprocess
import sys


def cortes_de_escena(ruta, umbral=0.35):
    """Devuelve los segundos en que la imagen cambia bruscamente."""
    comando = [
        "ffmpeg", "-i", ruta,
        "-vf", f"scale=320:-2,select='gt(scene,{umbral})',showinfo",
        "-an", "-f", "null", "-",
    ]
    r = subprocess.run(comando, capture_output=True, text=True,
                       encoding="utf-8", errors="ignore")
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else "videos/prueba.mp4"
    umbral = float(sys.argv[2]) if len(sys.argv) > 2 else 0.35
    tiempos = cortes_de_escena(ruta, umbral)
    print(f"{len(tiempos)} cortes con umbral {umbral}")
    for t in tiempos:
        print(f"{int(t) // 60:02d}:{int(t) % 60:02d}  ({t:.1f}s)")