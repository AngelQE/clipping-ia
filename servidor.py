import glob
import json
import mimetypes
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.cortador import Cancelado, regenerar_clip

CARPETA_SALIDA = "salida"

app = FastAPI(title="Clipping IA")


# --- Regeneración en segundo plano ---------------------------------------------------------

EJECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="render")  # un render a la vez
TRABAJOS_LOCK = threading.Lock()  # protege TRABAJOS y CANDADOS; las secciones críticas son muy cortas
CANDADOS: dict[str, threading.Lock] = {}  # un candado por clip, para leer/escribir su .json


class Trabajo:
    def __init__(self, clip_id: str, aprobar: bool):
        self.clip_id = clip_id
        self.aprobar = aprobar
        self.estado = "en_cola"  # en_cola | procesando | listo | error | cancelado
        self.mensaje = ""
        self.clip: dict | None = None
        self.evento = threading.Event()  # se activa para cancelar


TRABAJOS: dict[str, Trabajo] = {}


def _candado(clip_id: str) -> threading.Lock:
    with TRABAJOS_LOCK:
        return CANDADOS.setdefault(clip_id, threading.Lock())


def _info(t: Trabajo) -> dict:
    return {"id": t.clip_id, "estado": t.estado, "aprobar": t.aprobar, "mensaje": t.mensaje, "clip": t.clip}


# --- Utilidades ---------------------------------------------------------------------------


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
        "estado": d.get("estado", "pendiente"),
        "inicio": inicio,
        "fin": fin,
        "ventana": ventana,
        "puntaje": d.get("puntaje") or 0,
        "razon": d.get("razon", ""),
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


# --- Modelos de entrada -------------------------------------------------------------------


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
    aprobar: bool = False  # si es True, el clip se aprueba al terminar de regenerarse


class EstadoEntrada(BaseModel):
    estado: Literal["pendiente", "aprobado", "descartado"]


# --- Trabajo en segundo plano -------------------------------------------------------------


def _ejecutar(trabajo: Trabajo, ruta: str, datos: GuardarEntrada, titulo) -> None:
    """Corre en el hilo de render: regenera el clip y, si se pidió, lo aprueba al terminar."""
    with TRABAJOS_LOCK:
        if trabajo.evento.is_set():  # se canceló mientras esperaba en la cola
            trabajo.estado = "cancelado"
            return
        trabajo.estado = "procesando"

    try:
        with _candado(trabajo.clip_id):
            ok = regenerar_clip(
                ruta, inicio=datos.inicio, fin=datos.fin, titulo_en_video=titulo, cancelar=trabajo.evento
            )
            if not ok:
                trabajo.estado = "error"
                trabajo.mensaje = "No se pudo regenerar el clip (revisa la consola del servidor)"
                return
            d = _leer(ruta)
            if trabajo.aprobar:
                d["estado"] = "aprobado"
                d["estado_fecha"] = datetime.now().isoformat(timespec="seconds")
            elif d.get("estado") == "aprobado":
                d["estado"] = "pendiente"  # si cambió, lo aprobado ya no es lo que hay: vuelve a revisión
            _escribir(ruta, d)
            trabajo.clip = _a_clip(trabajo.clip_id, d)
            trabajo.estado = "listo"
    except Cancelado:
        trabajo.estado = "cancelado"
    except Exception as e:  # cualquier fallo se informa a la interfaz, no se pierde en el hilo
        trabajo.estado = "error"
        trabajo.mensaje = f"Error inesperado: {e}"


# --- API ----------------------------------------------------------------------------------


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


@app.post("/api/clips/{clip_id}/guardar", status_code=202)
def guardar_clip(clip_id: str, datos: GuardarEntrada):
    """Pone el clip en la cola de regeneración y responde enseguida. El avance se consulta en /api/trabajos."""
    ruta = _ruta_json(clip_id)
    if datos.fin - datos.inicio < 1:
        raise HTTPException(status_code=422, detail="El clip debe durar al menos 1 segundo")

    t = datos.tituloVideo
    titulo = {"texto": t.texto, "x": t.x, "y": t.y, "tamano": t.tamano} if t.visible and t.texto.strip() else False

    with TRABAJOS_LOCK:
        previo = TRABAJOS.get(clip_id)
        if previo and previo.estado in ("en_cola", "procesando"):
            raise HTTPException(status_code=409, detail="Este clip ya se está procesando")
        trabajo = Trabajo(clip_id, datos.aprobar)
        TRABAJOS[clip_id] = trabajo

    EJECUTOR.submit(_ejecutar, trabajo, ruta, datos, titulo)
    return _info(trabajo)


@app.get("/api/trabajos")
def listar_trabajos():
    """Trabajos activos y los que acaban de terminar. Cada resultado final se entrega una sola vez."""
    with TRABAJOS_LOCK:
        salida = [_info(t) for t in TRABAJOS.values()]
        for clave in [k for k, t in TRABAJOS.items() if t.estado in ("listo", "error", "cancelado")]:
            del TRABAJOS[clave]
    return salida


@app.post("/api/clips/{clip_id}/cancelar")
def cancelar_trabajo(clip_id: str):
    """Cancela un trabajo en cola (al instante) o en proceso (se detiene ffmpeg)."""
    with TRABAJOS_LOCK:
        t = TRABAJOS.get(clip_id)
        if t is None or t.estado not in ("en_cola", "procesando"):
            return {"cancelado": False}
        t.evento.set()
        if t.estado == "en_cola":
            t.estado = "cancelado"
    return {"cancelado": True}


@app.post("/api/clips/{clip_id}/estado")
def cambiar_estado(clip_id: str, datos: EstadoEntrada):
    ruta = _ruta_json(clip_id)
    with TRABAJOS_LOCK:
        t = TRABAJOS.get(clip_id)
        if t is not None and t.estado in ("en_cola", "procesando"):
            raise HTTPException(status_code=409, detail="El clip se está regenerando")
    with _candado(clip_id):
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