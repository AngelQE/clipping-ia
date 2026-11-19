from core.pipeline import modo_manual

# A) Subtítulos + título generado por el modelo, arriba durante todo el clip
archivos = modo_manual(
    "videos/prueba.mp4",
    tipo="auto",
    contexto="Un youtuber reacciona a TikToks. Cada clip debe mostrar el TikTok y su reacción.",
    duracion="largo",
    subtitulos=True,
    titulo_en_video=True,
)

# B) Solo título propio (sin subtítulos, sin transcribir: mucho más rápido), los primeros 5 segundos
# archivos = modo_manual(
#     "videos/prueba.mp4",
#     duracion="largo",
#     subtitulos=False,
#     titulo_en_video={"texto": "Rubius reacciona al GTA VI", "duracion": 5, "tamano": 72},
# )

print(archivos)