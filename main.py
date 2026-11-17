from core.pipeline import modo_manual

archivos = modo_manual(
    "videos/prueba.mp4",
    tipo="reaccion",
    contexto="Un youtuber reacciona a TikToks. Cada clip debe mostrar el TikTok y su reacción.",
    duracion="largo",
    motor="unidades",        # pon "clasico" para comparar con el motor anterior
    relleno_antes=2.5,
    relleno_despues=2.5,
    formato="borroso",
)
print(archivos)