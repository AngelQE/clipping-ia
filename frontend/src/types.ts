export type Estado = 'pendiente' | 'aprobado' | 'descartado'

export interface TituloVideo {
  visible: boolean // si el título se muestra dentro del video
  texto: string
  x: number // % del ancho: centro del título
  y: number // % del alto: centro del título
  tamano: number // píxeles en un video de 1080 de ancho (igual que en el backend)
}

export interface Clip {
  id: string
  titulo: string
  tipo: string
  estado: Estado
  inicio: number // segundos del video original
  fin: number
  ventana: [number, number] // rango del video con datos disponibles (la ventana de seguridad)
  puntaje: number
  razon: string
  fps?: number | null // cuadros por segundo reales, si el servidor los conoce
  videoUrl: string // vacío en la demostración
  tituloVideo: TituloVideo
}

export type EstadoTrabajo = 'en_cola' | 'procesando' | 'listo' | 'error' | 'cancelado'

export interface Trabajo {
  id: string
  estado: EstadoTrabajo
  aprobar: boolean // si el clip se aprueba al terminar
  mensaje: string
  clip: Clip | null // el clip ya regenerado, cuando termina bien
}