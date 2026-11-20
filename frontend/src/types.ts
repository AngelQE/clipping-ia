export interface TituloVideo {
  texto: string
  x: number // % del ancho: centro del título
  y: number // % del alto: centro del título
  tamano: number // píxeles en un video de 1080 de ancho (igual que en el backend)
}

export interface Clip {
  id: string
  titulo: string
  tipo: string
  inicio: number // segundos
  fin: number
  puntaje: number
  razon: string
  tituloVideo: TituloVideo
}