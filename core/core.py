import json
import os
import requests

PROVEEDOR = os.getenv("LLM_PROVEEDOR", "ollama")  # ollama | gemini

def _ollama(prompt: str) -> str:
    r = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": os.getenv("OLLAMA_MODELO", "qwen3:8b"),
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"num_ctx": 8192},
        },
        timeout=600,
    )
    r.raise_for_status()
    return r.json()["response"]

def _gemini(prompt: str) -> str:
    # Lo completamos cuando quieras usar Gemini
    raise NotImplementedError

def pedir_json(prompt: str) -> dict:
    texto = _ollama(prompt) if PROVEEDOR == "ollama" else _gemini(prompt)
    return json.loads(texto)