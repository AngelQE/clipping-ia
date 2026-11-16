import subprocess
import numpy as np
from faster_whisper import WhisperModel


def cargar_audio(ruta):
    """Convierte cualquier video/audio a un arreglo de audio 16 kHz mono usando ffmpeg."""
    comando = [
        "ffmpeg", "-i", ruta,
        "-f", "f32le", "-ac", "1", "-ar", "16000",
        "-loglevel", "error", "-",
    ]
    salida = subprocess.run(comando, capture_output=True, check=True).stdout
    return np.frombuffer(salida, dtype=np.float32)


model = WhisperModel("small", device="cpu", compute_type="int8")

audio = cargar_audio("videos/prueba.mp4")
segmentos, info = model.transcribe(audio, language="es")

for s in segmentos:
    print(f"[{s.start:.1f} → {s.end:.1f}] {s.text}")