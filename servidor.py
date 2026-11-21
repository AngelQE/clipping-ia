import glob
import json
import mimetypes
import os
import subprocess
from functools import lru_cache
from urllib.parse import quote
import threading
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.cortador import regenerar_clip

CARPETA_SALIDA = "salida"

app = FastAPI(title="Clipping IA")
BLOQUEO = threading.Lock()  # un cambio a la vez sobre los .json de los clips


def _ruta_json(clip_id: str) -> str:
    """El id es el nombre del archivo sin extensión. Se rechazan barras y puntos al inicio
    para que nadie pueda salirse de la carpeta."""
    if not clip_id or "/" in clip_id or "\\" in clip_id or clip_id.startswith("."):
        raise HTTPException(status_code=400, detail="Identificador no válido")
    ruta = os.path.join(CARPETA_SALIDA, f"{clip_id}.json")
    if not os.path.isfile(ruta):
        raise HTTPException(status_code=404, detail="Clip no encontrado")
    return ruta


def _leer(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)

def _escribir(ruta: str, d: dict) -> None:
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def _num(valor, defecto):
    return defecto if valor is None else valor


@lru_cache(maxsize=32)
def _fps(ruta_video: str) -> float | None:
    """Cuadros por segundo reales del video, con ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=avg_frame_rate", "-of", "csv=p=0", ruta_video],
            capture_output=True, text=True, timeout=15,
        )
        num, _, den = r.stdout.strip().split(",")[0].partition("/")
        valor = float(num) / float(den or 1)
        return round(valor, 3) if valor > 0 else None
    except (OSError, ValueError, ZeroDivisionError, subprocess.TimeoutExpired):
        return None


def _a_clip(clip_id: str, d: dict) -> dict:
    """Convierte el .json de un clip a lo que usa la interfaz."""
    inicio, fin = d["inicio"], d["fin"]
    ventana = d.get("ventana") or [max(0.0, inicio - 6), fin + 6]
    t = d.get("titulo_video") or {}
    return {
        "id": clip_id,
        "titulo": d.get("titulo", clip_id),
        "tipo": d.get("tipo") or "?",
        "inicio": inicio,
        "fin": fin,
        "ventana": ventana,
        "puntaje": d.get("puntaje") or 0,
        "razon": d.get("razon", ""),
        "estado": d.get("estado", "pendiente"),
        "fps": _fps(d["video"]) if d.get("video") else None,
        "videoUrl": f"/media/fuente/{quote(clip_id)}",
        "tituloVideo": {
            "visible": bool(t),
            "texto": t.get("texto") or d.get("titulo", ""),
            "x": _num(t.get("x"), 50),
            "y": _num(t.get("y"), 16),
            "tamano": _num(t.get("tamano"), 64),
        },
    }


@app.get("/api/clips")
def listar_clips():
    clips = []
    for ruta in sorted(glob.glob(os.path.join(CARPETA_SALIDA, "*.json"))):
        try:
            d = _leer(ruta)
        except (OSError, json.JSONDecodeError):
            continue
        if "inicio" not in d or "fin" not in d or "video" not in d:
            continue
        clips.append(_a_clip(os.path.splitext(os.path.basename(ruta))[0], d))
    return clips


class TituloEntrada(BaseModel):
    visible: bool = True
    texto: str = ""
    x: float = 50.0
    y: float = 16.0
    tamano: float = 64.0


class GuardarEntrada(BaseModel):
    inicio: float
    fin: float
    tituloVideo: TituloEntrada



@app.post("/api/clips/{clip_id}/guardar")
def guardar_clip(clip_id: str, datos: GuardarEntrada):
    """Regenera el clip desde el video original con los tiempos y el título que eligió la persona.
    Es una función normal (no async), así FastAPI la corre en otro hilo y el servidor no se bloquea."""
    ruta = _ruta_json(clip_id)
    if datos.fin - datos.inicio < 1:
        raise HTTPException(status_code=422, detail="El clip debe durar al menos 1 segundo")

    t = datos.tituloVideo
    titulo = {"texto": t.texto, "x": t.x, "y": t.y, "tamano": t.tamano} if t.visible and t.texto.strip() else False

    with BLOQUEO:
        ok = regenerar_clip(ruta, inicio=datos.inicio, fin=datos.fin, titulo_en_video=titulo)
        if not ok:
            raise HTTPException(
                status_code=422,
                detail="No se pudo regenerar el clip (revisa la consola del servidor)",
            )
        d = _leer(ruta)
        if d.get("estado") == "aprobado":
            # Si cambió, lo aprobado ya no es lo que hay: vuelve a revisión
            d["estado"] = "pendiente"
            _escribir(ruta, d)
    return _a_clip(clip_id, d)


class EstadoEntrada(BaseModel):
    estado: Literal["pendiente", "aprobado", "descartado"]


@app.post("/api/clips/{clip_id}/estado")
def cambiar_estado(clip_id: str, datos: EstadoEntrada):
    ruta = _ruta_json(clip_id)
    with BLOQUEO:
        d = _leer(ruta)
        d["estado"] = datos.estado
        d["estado_fecha"] = datetime.now().isoformat(timespec="seconds")
        _escribir(ruta, d)
    return _a_clip(clip_id, d)


@app.get("/media/fuente/{clip_id}")
def video_fuente(clip_id: str):
    ruta = _leer(_ruta_json(clip_id)).get("video")
    if not ruta or not os.path.isfile(ruta):
        raise HTTPException(status_code=404, detail="No encuentro el video original")
    return FileResponse(ruta, media_type=mimetypes.guess_type(ruta)[0] or "video/mp4")


@app.get("/media/clip/{clip_id}")
def video_clip(clip_id: str):
    ruta = _leer(_ruta_json(clip_id)).get("archivo")
    if not ruta or not os.path.isfile(ruta):
        raise HTTPException(status_code=404, detail="No encuentro el clip")
    return FileResponse(ruta, media_type="video/mp4", headers={"Cache-Control": "no-cache"})