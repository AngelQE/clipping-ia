from core.pipeline import modo_manual, modo_rango

# A) La IA elige los momentos
archivos = modo_manual(
    "videos/prueba.mp4",
    tipo="reaccion",
    contexto="Un youtuber reacciona a TikToks. Cada clip debe mostrar el TikTok y su reacción.",
    duracion=None,          # prueba también "corto", "largo" o (45, 75)
    formato="borroso",
)

# B) Tú eliges los minutos (descomenta este bloque y comenta el A)
# archivos = modo_rango(
#     "videos/prueba.mp4",
#     [("01:20", "02:05"), ("10:00", "10:45")],
#     formato="borroso",
# )

print(archivos)