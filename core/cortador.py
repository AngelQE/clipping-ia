import json
import os
import re
import shutil
import subprocess

from core.subtitulos import crear_ass

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


def _normalizar(texto):
    return re.sub(r"[^\w]", "", texto.lower())


def _resolucion_salida(ruta_video, formato):
    """Tamaño del video final, para dimensionar los subtítulos."""
    if formato in ("recorte", "borroso"):
        return 1080, 1920
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", ruta_video],
        capture_output=True, text=True,
    )
    try:
        ancho, alto = (int(x) for x in r.stdout.strip().split(",")[:2])
        return ancho, alto
    except ValueError:
        return 1920, 1080


def _preparar_fuentes(estilo_sub):
    """Si hay una fuente propia, la copia a la carpeta 'fuentes' y devuelve esa carpeta."""
    archivo = (estilo_sub or {}).get("archivo_fuente")
    if not archivo:
        return None
    os.makedirs("fuentes", exist_ok=True)
    destino = os.path.join("fuentes", os.path.basename(archivo))
    if os.path.abspath(archivo) != os.path.abspath(destino) and not os.path.exists(destino):
        shutil.copy2(archivo, destino)
    return "fuentes"


def _palabras_del_tramo(palabras_abs, inicio, fin):
    """Palabras (con tiempo del video original) que caen dentro del clip, con tiempo relativo al clip."""
    salida = []
    for p in palabras_abs:
        if p["fin"] <= inicio or p["inicio"] >= fin:
            continue
        salida.append({
            "inicio": round(max(p["inicio"], inicio) - inicio, 2),
            "fin": round(min(p["fin"], fin) - inicio, 2),
            "texto": p["texto"],
        })
    return salida


def _renderizar(ruta_video, inicio, fin, destino, formato, palabras=None, estilo_sub=None, n=0):
    """Corta un clip con ffmpeg, con subtítulos quemados si hay palabras (tiempos relativos al clip)."""
    vf = FILTROS.get(formato)
    if palabras:
        os.makedirs("cache/subs", exist_ok=True)
        ancho, alto = _resolucion_salida(ruta_video, formato)
        ruta_ass = f"cache/subs/sub_{n:02d}.ass"   # ruta relativa con "/" para que ffmpeg no se confunda en Windows
        if crear_ass(palabras, ruta_ass, ancho, alto, estilo_sub):
            filtro_ass = f"ass={ruta_ass}"
            carpeta_fuentes = _preparar_fuentes(estilo_sub)
            if carpeta_fuentes:
                filtro_ass += f":fontsdir={carpeta_fuentes}"
            vf = f"{vf},{filtro_ass}" if vf else filtro_ass
    comando = ["ffmpeg", "-y", "-ss", f"{inicio:.3f}", "-i", ruta_video, "-t", f"{fin - inicio:.3f}"]
    if vf:
        comando += ["-vf", vf]
    comando += ["-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-loglevel", "error", destino]
    r = subprocess.run(comando, capture_output=True)
    if r.returncode != 0:
        print(f"[Cortador] Error: {r.stderr.decode(errors='ignore')}")
        return False
    return True


def _informe_cobertura(n, palabras, duracion):
    """Avisa de tramos largos sin subtítulos, para saber si falta voz por transcribir."""
    if not palabras:
        print(f"[Subtítulos] Clip {n}: 0 palabras detectadas")
        return
    huecos, previo = [], 0.0
    for p in palabras:
        if p["inicio"] - previo > 3.0:
            huecos.append((previo, p["inicio"]))
        previo = max(previo, p["fin"])
    if duracion - previo > 3.0:
        huecos.append((previo, duracion))
    texto = ", ".join(f"{a:.0f}s-{b:.0f}s" for a, b in huecos) or "ninguno"
    print(f"[Subtítulos] Clip {n}: {len(palabras)} palabras | tramos sin texto (más de 3 s): {texto}")


def _guardar_datos(ruta_json, datos):
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def cortar_clips(ruta_video, clips, carpeta_salida="salida", formato="borroso",
                 subtitulos=False, idioma=None, estilo_sub=None, margen=6.0):
    """Corta cada clip. formato: original | recorte | borroso.
    margen: segundos de ventana de seguridad antes y después de cada clip. Se transcriben sus palabras
    una sola vez, para poder mover el inicio o el final después sin volver a transcribir."""
    os.makedirs(carpeta_salida, exist_ok=True)
    if subtitulos:
        from core.transcripcion import transcribir_palabras  # import tardío: carga Whisper solo si hace falta

    archivos = []
    for i, c in enumerate(clips, 1):
        destino = os.path.join(carpeta_salida, f"{i:02d}_{_nombre_seguro(c['titulo'])}.mp4")
        palabras_abs, ventana, palabras_clip = [], None, None

        if subtitulos:
            v_ini = max(0.0, c["inicio"] - margen)
            v_fin = c["fin"] + margen
            relativas = transcribir_palabras(ruta_video, v_ini, v_fin, idioma)
            palabras_abs = [
                {"inicio": round(p["inicio"] + v_ini, 2), "fin": round(p["fin"] + v_ini, 2), "texto": p["texto"]}
                for p in relativas
            ]
            ventana = [round(v_ini, 3), round(v_fin, 3)]
            palabras_clip = _palabras_del_tramo(palabras_abs, c["inicio"], c["fin"])
            _informe_cobertura(i, palabras_clip, c["fin"] - c["inicio"])

        if not _renderizar(ruta_video, c["inicio"], c["fin"], destino, formato, palabras_clip, estilo_sub, i):
            continue

        _guardar_datos(os.path.splitext(destino)[0] + ".json", {
            "archivo": destino,
            "video": os.path.abspath(ruta_video),
            "inicio": round(c["inicio"], 3),
            "fin": round(c["fin"], 3),
            "ventana": ventana,              # rango con palabras disponibles (tiempos del video original)
            "titulo": c["titulo"],
            "razon": c.get("razon", ""),
            "puntaje": c.get("puntaje"),
            "formato": formato,
            "idioma": idioma,
            "estilo_sub": estilo_sub or {},
            "palabras": palabras_abs,        # tiempos del video original
        })
        archivos.append(destino)
    return archivos


def mostrar_palabras(ruta_json):
    """Imprime las palabras de un clip con su número. El * marca las que están dentro del clip."""
    with open(ruta_json, encoding="utf-8") as f:
        datos = json.load(f)
    for i, p in enumerate(datos.get("palabras", [])):
        dentro = "*" if datos["inicio"] <= p["inicio"] < datos["fin"] else " "
        print(f"{i:4d} {dentro} {p['inicio']:8.2f}s  {p['texto']}")


def regenerar_clip(ruta_json, correcciones=None, estilo_sub=None,
                   inicio=None, fin=None, mover_inicio=0.0, mover_fin=0.0):
    """Vuelve a crear un clip desde el video original, sin transcribir de nuevo.
    correcciones: {12: "palabra correcta"} (por número) o {"palabra mala": "palabra buena"}.
    estilo_sub: solo lo que quieras cambiar, por ejemplo {"tamano": 48}.
    Tiempos: inicio/fin (segundos del video original) o mover_inicio/mover_fin.
      mover_inicio=-1.5 empieza 1.5 s antes; mover_fin=+2 termina 2 s después.
    Solo se puede mover dentro de la ventana de seguridad del clip."""
    with open(ruta_json, encoding="utf-8") as f:
        datos = json.load(f)
    if "ventana" not in datos:
        print("[Cortador] Este clip se creó con una versión anterior. Vuelve a generarlo.")
        return False

    palabras = datos.get("palabras") or []
    for clave, nuevo in (correcciones or {}).items():
        if isinstance(clave, int):
            if 0 <= clave < len(palabras):
                palabras[clave]["texto"] = nuevo
        else:
            buscada = _normalizar(clave)
            for p in palabras:
                if _normalizar(p["texto"]) == buscada:
                    p["texto"] = nuevo

    if estilo_sub:
        datos["estilo_sub"] = {**datos.get("estilo_sub", {}), **estilo_sub}

    nuevo_inicio = inicio if inicio is not None else datos["inicio"] + mover_inicio
    nuevo_fin = fin if fin is not None else datos["fin"] + mover_fin
    if datos["ventana"] and palabras:
        v_ini, v_fin = datos["ventana"]
        if nuevo_inicio < v_ini or nuevo_fin > v_fin:
            print(f"[Cortador] Fuera de la ventana de seguridad ({v_ini:.1f}s a {v_fin:.1f}s): se ajusta al límite.")
            nuevo_inicio, nuevo_fin = max(nuevo_inicio, v_ini), min(nuevo_fin, v_fin)
    nuevo_inicio = max(0.0, nuevo_inicio)
    if nuevo_fin - nuevo_inicio < 1.0:
        print("[Cortador] El clip quedaría de menos de 1 segundo; no se cambia nada.")
        return False

    palabras_clip = _palabras_del_tramo(palabras, nuevo_inicio, nuevo_fin) if palabras else None
    ok = _renderizar(datos["video"], nuevo_inicio, nuevo_fin, datos["archivo"], datos["formato"],
                     palabras_clip, datos.get("estilo_sub"), n=0)
    if ok:
        datos["inicio"], datos["fin"], datos["palabras"] = round(nuevo_inicio, 3), round(nuevo_fin, 3), palabras
        _guardar_datos(ruta_json, datos)
        print(f"[Cortador] Clip regenerado: {datos['archivo']} ({nuevo_inicio:.2f}s a {nuevo_fin:.2f}s)")
    return ok