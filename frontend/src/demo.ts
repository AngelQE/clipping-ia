import type { Clip, TituloVideo } from './types'

const titulo = (texto: string): TituloVideo => ({ visible: true, texto, x: 50, y: 16, tamano: 64 })

const clipsBase: Omit<Clip, 'estado'>[] = [
  {
    id: 'c1',
    titulo: 'Un tanque se bloquea con basura',
    tipo: 'reaccion',
    inicio: 312.4,
    fin: 358.1,
    ventana: [306.4, 364.1],
    puntaje: 9,
    razon: 'Planteamiento claro, reacción de incredulidad y remate gracioso.',
    videoUrl: '',
    tituloVideo: titulo('Un tanque se bloquea con basura'),
  },
  {
    id: 'c2',
    titulo: '¿Cómo le llega a los chavos mal hablados?',
    tipo: 'podcast',
    inicio: 95.0,
    fin: 171.5,
    ventana: [89.0, 177.5],
    puntaje: 8,
    razon: 'Pregunta fuerte seguida de una anécdota completa.',
    videoUrl: '',
    tituloVideo: titulo('¿Cómo le llega a los chavos mal hablados?'),
  },
  {
    id: 'c3',
    titulo: 'De una maleta salió un hotel de 8 pisos y nadie entiende cómo cabía todo ahí dentro',
    tipo: 'reaccion',
    inicio: 640.2,
    fin: 702.9,
    ventana: [634.2, 708.9],
    puntaje: 9,
    razon: 'El TikTok completo y la reacción principal justo después.',
    videoUrl: '',
    tituloVideo: titulo('De una maleta salió un hotel de 8 pisos y nadie entiende cómo cabía todo ahí dentro'),
  },
  {
    id: 'c4',
    titulo: '🔥 Esto NO se hace en un directo 🔥',
    tipo: 'stream',
    inicio: 1520.0,
    fin: 1561.4,
    ventana: [1514.0, 1567.4],
    puntaje: 7,
    razon: 'Pico de emoción con reacción clara del streamer.',
    videoUrl: '',
    tituloVideo: titulo('🔥 Esto NO se hace en un directo 🔥'),
  },
]

export const clipsDemo: Clip[] = clipsBase.map((c) => ({ ...c, estado: 'pendiente' as const }))