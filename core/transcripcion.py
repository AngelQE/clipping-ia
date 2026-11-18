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
MODELO_WHISPER = "large-v3"
_modelo = None


def _obtener_modelo():
    """Carga el modelo una sola vez. Usa la GPU y, si falla, cae a CPU."""
    global _modelo
    if _modelo is None:
        try:
            _modelo = WhisperModel(MODELO_WHISPER, device="cuda", compute_type="int8_float16")
            print(f"[Whisper] {MODELO_WHISPER} en GPU")
        except Exception as e:
            print(f"[Whisper] No se pudo usar la GPU ({e}). Usando CPU con 'small'.")
            _modelo = WhisperModel("small", device="cpu", compute_type="int8")
    return _modelo


def cargar_audio(ruta, inicio=None, duracion=None):
    """Convierte video/audio a audio 16 kHz mono con ffmpeg. Opcionalmente solo un tramo."""
    comando = ["ffmpeg"]
    if inicio is not None:
        comando += ["-ss", str(inicio)]
    comando += ["-i", ruta]
    if duracion is not None:
        comando += ["-t", str(duracion)]
    comando += ["-f", "f32le", "-ac", "1", "-ar", "16000", "-loglevel", "error", "-"]
    resultado = subprocess.run(comando, capture_output=True)
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr.decode(errors="ignore"))
    return np.frombuffer(resultado.stdout, dtype=np.float32)


def transcribir(ruta_video, idioma=None, prompt=None):
    """Devuelve (segmentos, idioma). Con idioma=None lo detecta solo."""
    audio = cargar_audio(ruta_video)
    segmentos, info = _obtener_modelo().transcribe(
        audio,
        language=idioma,
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=prompt,
    )
    lista = [
        {"inicio": round(s.start, 2), "fin": round(s.end, 2), "texto": s.text.strip()}
        for s in segmentos
    ]
    return lista, info.language

def liberar_modelo():
    """Descarga Whisper de la memoria para dejar la GPU libre."""
    global _modelo
    _modelo = None
    import gc
    gc.collect()

def _buscar_huecos(palabras, duracion, minimo=2.5):
    """Tramos de más de 'minimo' segundos sin ninguna palabra."""
    huecos, previo = [], 0.0
    for p in palabras:
        if p["inicio"] - previo > minimo:
            huecos.append((previo, p["inicio"]))
        previo = max(previo, p["fin"])
    if duracion - previo > minimo:
        huecos.append((previo, duracion))
    return huecos


def _rellenar_huecos(audio, palabras, duracion, idioma, prompt=None):
    """Segunda pasada. En audios largos Whisper a veces se salta tramos con voz.
    Se vuelve a intentar solo en los huecos, en trozos cortos y sin el filtro de voz."""
    modelo = _obtener_modelo()
    nuevas = []
    for h_ini, h_fin in _buscar_huecos(palabras, duracion):
        t = max(0.0, h_ini - 0.3)
        while t < h_fin:
            t_fin = min(h_fin + 0.3, t + 12.0, duracion)
            if t_fin - t < 0.5:
                break
            trozo = audio[int(t * 16000):int(t_fin * 16000)]
            segmentos, _ = modelo.transcribe(
                trozo,
                language=idioma,
                beam_size=5,
                condition_on_previous_text=False,
                initial_prompt=prompt,
                word_timestamps=True,
                vad_filter=False,
                no_speech_threshold=None,
                log_prob_threshold=None,
            )
            for s in segmentos:
                # Descarta lo que parece inventado (ruido o música)
                if s.avg_logprob < -1.5 or s.compression_ratio > 2.4:
                    continue
                for w in (s.words or []):
                    texto = w.word.strip()
                    if not texto:
                        continue
                    ini, fin = t + w.start, t + w.end
                    if h_ini <= (ini + fin) / 2 <= h_fin:
                        nuevas.append({"inicio": round(ini, 2), "fin": round(fin, 2), "texto": texto})
            t = t_fin
    if nuevas:
        print(f"[Whisper] Recuperé {len(nuevas)} palabras en tramos que la primera pasada se saltó")
    return sorted(palabras + nuevas, key=lambda p: p["inicio"])


def transcribir_palabras(ruta_video, inicio, fin, idioma=None, prompt=None,
                         sensible=True, rellenar=True):
    """Palabras de un tramo con su tiempo, relativo al inicio del tramo.
    sensible: ajustes permisivos para no perder voces bajas.
    rellenar: segunda pasada en los huecos sin texto."""
    audio = cargar_audio(ruta_video, inicio=inicio, duracion=fin - inicio)
    opciones = dict(
        language=idioma,
        beam_size=5,
        condition_on_previous_text=False,
        initial_prompt=prompt,
        word_timestamps=True,
        vad_filter=True,
    )
    if sensible:
        opciones.update(
            vad_parameters=dict(threshold=0.3, min_silence_duration_ms=700, speech_pad_ms=400),
            no_speech_threshold=0.9,
            log_prob_threshold=None,
        )
    segmentos, _ = _obtener_modelo().transcribe(audio, **opciones)
    palabras = []
    for s in segmentos:
        for w in (s.words or []):
            texto = w.word.strip()
            if texto:
                palabras.append({"inicio": round(w.start, 2), "fin": round(w.end, 2), "texto": texto})
    if rellenar:
        palabras = _rellenar_huecos(audio, palabras, len(audio) / 16000, idioma, prompt)
    return palabras