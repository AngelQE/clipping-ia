import type { Clip, Estado } from './types'

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

export const listarClips = () => pedir<Clip[]>('/api/clips')

export const guardarClip = (clip: Clip) =>
  pedir<Clip>(`/api/clips/${encodeURIComponent(clip.id)}/guardar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ inicio: clip.inicio, fin: clip.fin, tituloVideo: clip.tituloVideo }),
  })

  export const cambiarEstado = (id: string, estado: Estado) =>
  pedir<Clip>(`/api/clips/${encodeURIComponent(id)}/estado`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ estado }),
  })