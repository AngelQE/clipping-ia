import json
import os
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = os.getenv("OLLAMA_MODELO", "qwen3:8b")


def pedir_json(prompt: str) -> dict:
    r = requests.post(
        OLLAMA_URL,
        json={
            "model": MODELO,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "format": "json",
            "options": {"num_ctx": 8192, "temperature": 0.3},
        },
        timeout=900,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Ollama respondió {r.status_code}: {r.text}")
    return json.loads(r.json()["response"])

def liberar_ollama():
    """Descarga el modelo de la GPU para dejar espacio a Whisper."""
    try:
        requests.post(OLLAMA_URL, json={"model": MODELO, "keep_alive": 0}, timeout=30)
    except Exception:
        pass