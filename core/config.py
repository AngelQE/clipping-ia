from dataclasses import dataclass


@dataclass
class TrabajoAuto:
    # Qué cazar
    nicho: str = ""
    max_videos: int = 3
    fuente_min_minutos: float = 3      # ignora videos fuente más cortos que esto
    fuente_max_minutos: float = 60     # ignora videos fuente más largos que esto

    # Qué parte de cada video procesar (en minutos; None = completo)
    desde_min: float | None = None
    hasta_min: float | None = None

    # Cómo editar
    tipo: str = "auto"
    contexto: str = ""
    duracion: object = "auto"          # "corto" | "medio" | "largo" | "auto" | (min, max) en segundos
    max_clips: int = 5
    formato: str = "borroso"

    # Control tuyo
    aprobar_links: bool = True         # el cazador propone y tú apruebas antes de descargar