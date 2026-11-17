import numpy as np
import requests

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
MODELO_EMBED = "bge-m3"


def _embeddings(textos, lote=32):
    """Convierte cada texto en un vector que representa su significado."""
    vectores = []
    for i in range(0, len(textos), lote):
        r = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": MODELO_EMBED, "input": textos[i:i + lote]},
            timeout=300,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Ollama respondió {r.status_code}: {r.text}")
        vectores.extend(r.json()["embeddings"])
    m = np.array(vectores, dtype=np.float32)
    return m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)


def _ventanas(segmentos, duracion_min=12):
    """Agrupa segmentos consecutivos en ventanas de al menos ~12 segundos."""
    ventanas, actual = [], []
    for s in segmentos:
        actual.append(s)
        if actual[-1]["fin"] - actual[0]["inicio"] >= duracion_min:
            ventanas.append(actual)
            actual = []
    if actual:
        ventanas.append(actual)
    return ventanas


def _similitudes(vectores, k):
    """sims[i] = parecido entre las k ventanas antes de i y las k desde i."""
    n = len(vectores)
    sims = np.ones(n)
    for i in range(1, n):
        izq = vectores[max(0, i - k):i].mean(axis=0)
        der = vectores[i:i + k].mean(axis=0)
        sims[i] = float(np.dot(izq, der) / (np.linalg.norm(izq) * np.linalg.norm(der) + 1e-9))
    return sims


def _fronteras(sims, sensibilidad, separacion):
    """Elige los puntos donde el parecido cae más (cambios de tema)."""
    interior = sims[1:]
    if len(interior) < 3:
        return []
    umbral = interior.mean() - sensibilidad * interior.std()
    candidatos = []
    for i in range(1, len(sims)):
        izq = sims[i - 1] if i - 1 >= 1 else np.inf
        der = sims[i + 1] if i + 1 < len(sims) else np.inf
        if sims[i] < umbral and sims[i] <= izq and sims[i] <= der:
            candidatos.append(i)
    # Los más marcados primero; se descartan los que quedan demasiado cerca de uno ya elegido
    candidatos.sort(key=lambda i: sims[i])
    elegidas = []
    for i in candidatos:
        if all(abs(i - j) >= separacion for j in elegidas):
            elegidas.append(i)
    return sorted(elegidas)


def segmentar_por_tema(segmentos, k=3, sensibilidad=0.5, separacion=2):
    """Divide la transcripción en unidades por tema.
    Devuelve [{'inicio', 'fin', 'texto'}, ...].
    sensibilidad: más alta = menos cortes; más baja = más cortes."""
    ventanas = _ventanas(segmentos)
    textos = [" ".join(s["texto"] for s in v) for v in ventanas]
    if len(ventanas) < 4:
        return [{"inicio": segmentos[0]["inicio"], "fin": segmentos[-1]["fin"],
                 "texto": " ".join(textos)}]

    vectores = _embeddings(textos)
    sims = _similitudes(vectores, k)
    cortes = [0] + _fronteras(sims, sensibilidad, separacion) + [len(ventanas)]

    unidades = []
    for a, b in zip(cortes[:-1], cortes[1:]):
        unidades.append({
            "inicio": ventanas[a][0]["inicio"],
            "fin": ventanas[b - 1][-1]["fin"],
            "texto": " ".join(textos[a:b]),
        })
    return unidades