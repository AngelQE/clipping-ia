from core.pipeline import modo_manual

archivos = modo_manual(
    "videos/prueba.mp4",
    tipo="auto",             # opcional: "reaccion", "podcast", "stream", "tutorial", "general"
    contexto="Un youtuber reacciona a TikToks. Cada clip debe mostrar el TikTok y su reacción.",
    duracion="largo",
    motor="unidades",
    relleno_antes=2.5,
    relleno_despues=2.5,
    formato="borroso",
    subtitulos=True,
    idioma=None,             # automático; o "es" / "en"
    estilo_sub={
        "tamano": 56,                    # número
        "fuente": "Arial",
        "archivo_fuente": None,          # o "C:/fuentes/MiFuente.ttf"
        "color_texto": "#FFFFFF",
        "color_resaltado": "#FFFF00",
        "color_borde": "#000000",
        "grosor_borde": 5,
        "mayusculas": True,
        "posicion": 27,
    },
)
print(archivos)