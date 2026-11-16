import os
import re
import subprocess

FILTROS = {
    "original": None,
    "recorte": "crop=ih*9/16:ih,scale=1080:1920",
    "borroso": (
        "split[a][b];"
        "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg];"
        "[b]scale=1080:-2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2"
    ),
}


def formatear_tiempo(segundos):
    s = int(segundos)
    return f"{s // 60:02d}:{s % 60:02d}"


def a_segundos(valor):
    """Acepta 75, '75', '1:15' o '01:02:03' y devuelve segundos."""
    if isinstance(valor, (int, float)):
        return float(valor)
    segundos = 0.0
    for parte in str(valor).strip().split(":"):
        segundos = segundos * 60 + float(parte)
    return segundos


def _nombre_seguro(texto):
    texto = re.sub(r'[\\/*?:"<>|]', "", texto).strip()
    return texto[:50] or "clip"


def cortar_clips(ruta_video, clips, carpeta_salida="salida", formato="borroso"):
    """Corta cada clip con ffmpeg. formato: original | recorte | borroso"""
    os.makedirs(carpeta_salida, exist_ok=True)
    filtro = FILTROS.get(formato)
    archivos = []
    for i, c in enumerate(clips, 1):
        destino = os.path.join(carpeta_salida, f"{i:02d}_{_nombre_seguro(c['titulo'])}.mp4")
        comando = ["ffmpeg", "-y", "-ss", str(c["inicio"]), "-i", ruta_video,
                   "-t", str(c["fin"] - c["inicio"])]
        if filtro:
            comando += ["-vf", filtro]
        comando += ["-c:v", "libx264", "-preset", "fast", "-crf", "20",
                    "-c:a", "aac", "-loglevel", "error", destino]
        r = subprocess.run(comando, capture_output=True)
        if r.returncode != 0:
            print(f"[Cortador] Error en el clip {i}: {r.stderr.decode(errors='ignore')}")
            continue
        archivos.append(destino)
    return archivos