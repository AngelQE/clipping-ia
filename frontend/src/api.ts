import type { Clip, Estado, Trabajo } from './types'

async function pedir<T>(url: string, opciones?: RequestInit): Promise<T> {
  const r = await fetch(url, opciones)
  if (!r.ok) {
    let detalle = ''
    try {
      detalle = (await r.json()).detail ?? ''
    } catch {
      // la respuesta no traía un JSON con el motivo
    }
    throw new Error(detalle || `Error ${r.status}`)
  }
  return r.json() as Promise<T>
}

const POST_JSON = (cuerpo: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(cuerpo),
})

const enc = encodeURIComponent

export const listarClips = () => pedir<Clip[]>('/api/clips')

/** Pone el clip en la cola de regeneración. Con aprobar=true se aprueba al terminar bien. */
export const guardarClip = (clip: Clip, aprobar: boolean) =>
  pedir<Trabajo>(
    `/api/clips/${enc(clip.id)}/guardar`,
    POST_JSON({ inicio: clip.inicio, fin: clip.fin, tituloVideo: clip.tituloVideo, aprobar }),
  )

export const listarTrabajos = () => pedir<Trabajo[]>('/api/trabajos')

export const cancelarTrabajo = (id: string) =>
  pedir<{ cancelado: boolean }>(`/api/clips/${enc(id)}/cancelar`, { method: 'POST' })

export const cambiarEstado = (id: string, estado: Estado) =>
  pedir<Clip>(`/api/clips/${enc(id)}/estado`, POST_JSON({ estado }))