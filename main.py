from core.pipeline import modo_manual

# A) Subtítulos + título generado por el modelo, arriba durante todo el clip
# archivos = modo_manual(
#     "videos/02_Chop es arrollado y vengado.mp4",
#     tipo="auto",
#     contexto="Un youtuber reacciona a TikToks. Cada clip debe mostrar el TikTok y su reacción.",
#     duracion="largo",
#     subtitulos=True,
#     titulo_en_video=True,
# )

# B) Solo título propio (sin subtítulos, sin transcribir: mucho más rápido), los primeros 5 segundos
archivos = modo_manual(
    "videos/JedNRjkzidM_120-300.mp4",
    duracion="largo",
    subtitulos=False,
    titulo_en_video={"texto": "Missa y la telekinesis", "duracion": 8, "tamano": 72},
)

print(archivos)