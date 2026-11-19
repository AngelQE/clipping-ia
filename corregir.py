from core.cortador import mostrar_palabras, regenerar_clip

RUTA = "salida/01_¿Un tanque se rompe por basura ¡Qué absurdo!.json"
mostrar_palabras(RUTA)     # las palabras con * están dentro del clip

# Corregir palabras (por número o por la palabra mala):
# regenerar_clip(RUTA, correcciones={12: "balsa", "bolsa": "balsa"})

# Empezar 1.5 s antes y terminar 0.8 s antes (dentro de la ventana de seguridad):
# regenerar_clip(RUTA, mover_inicio=-5.5, mover_fin=+5.5)

# Cambiar el estilo de los subtítulos:
# regenerar_clip(RUTA, estilo_sub={"tamano": 36, "color_resaltado": "#00FF00"})

# Cambiar el Título en una clip que ya existe:
# regenerar_clip(RUTA, titulo_en_video="Rubius reacciona al GTA VI")
# regenerar_clip(RUTA, titulo_en_video=False)   # quitarlo