import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import sys
import subprocess
import numpy as np


def _registrar_dlls_nvidia():
    """En Windows, le dice a Python dónde están las DLL de CUDA instaladas por pip."""
    if sys.platform != "win32":
        return
    import site
    for base in site.getsitepackages():
        nvidia = os.path.join(base, "nvidia")
        if not os.path.isdir(nvidia):
            continue
        for sub in os.listdir(nvidia):
            bin_dir = os.path.join(nvidia, sub, "bin")
            if os.path.isdir(bin_dir):
                os.add_dll_directory(bin_dir)
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]


_registrar_dlls_nvidia()

from faster_whisper import WhisperModel  # noqa: E402

_modelo = None


def _obtener_modelo():
    """Carga el modelo una sola vez. Usa la GPU y, si falla, cae a CPU."""
    global _modelo
    if _modelo is None:
        try:
            _modelo = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
            print("[Whisper] large-v3 en GPU")
        except Exception as e:
            print(f"[Whisper] No se pudo usar la GPU ({e}). Usando CPU con 'small'.")
            _modelo = WhisperModel("small", device="cpu", compute_type="int8")
    return _modelo


def cargar_audio(ruta):
    """Convierte cualquier video/audio a audio 16 kHz mono usando ffmpeg."""
    comando = [
        "ffmpeg", "-i", ruta,
        "-f", "f32le", "-ac", "1", "-ar", "16000",
        "-loglevel", "error", "-",
    ]
    resultado = subprocess.run(comando, capture_output=True)
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr.decode(errors="ignore"))
    return np.frombuffer(resultado.stdout, dtype=np.float32)


def transcribir(ruta_video, idioma="es", prompt=None):
    """Devuelve una lista de segmentos: [{'inicio':..., 'fin':..., 'texto':...}]"""
    audio = cargar_audio(ruta_video)
    segmentos, _ = _obtener_modelo().transcribe(
        audio,
        language=idioma,
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=prompt,
    )
    return [
        {"inicio": round(s.start, 2), "fin": round(s.end, 2), "texto": s.text.strip()}
        for s in segmentos
    ]

def liberar_modelo():
    """Descarga Whisper de la memoria para dejar la GPU libre."""
    global _modelo
    _modelo = None
    import gc
    gc.collect()