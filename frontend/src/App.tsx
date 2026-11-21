import { useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { Upload } from 'lucide-react'
import PreviewStage from './components/PreviewStage'
import Timeline from './components/Timeline'
import TituloPanel from './components/TituloPanel'
import { clipsDemo } from './demo'
import { formatTime } from './lib/time'
import type { Clip, TituloVideo } from './types'

export default function App() {
  const [clips, setClips] = useState<Clip[]>(clipsDemo)
  const [selId, setSelId] = useState<string | null>(clipsDemo[0]?.id ?? null)
  const [zonasSeguras, setZonasSeguras] = useState(false)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [fps, setFps] = useState(30)
  const videoRef = useRef<HTMLVideoElement>(null)
  const archivoRef = useRef<HTMLInputElement>(null)

  const sel = clips.find((c) => c.id === selId) ?? null

  const actualizarClip = (cambios: Partial<Clip>) => {
    if (!sel) return
    setClips((prev) => prev.map((c) => (c.id === sel.id ? { ...c, ...cambios } : c)))
  }

  const actualizarTitulo = (cambios: Partial<TituloVideo>) => {
    if (!sel) return
    actualizarClip({ tituloVideo: { ...sel.tituloVideo, ...cambios } })
  }

  const alElegirArchivo = (e: ChangeEvent<HTMLInputElement>) => {
    const archivo = e.target.files?.[0]
    if (!archivo) return
    if (videoUrl) URL.revokeObjectURL(videoUrl)
    setVideoUrl(URL.createObjectURL(archivo))
    e.target.value = '' // permite elegir el mismo archivo otra vez
  }

  // Solo para la demostración: reparte el video cargado entre los clips de ejemplo
  const alVideoListo = (duracion: number) => {
    setClips((prev) => {
      const seg = duracion / Math.max(prev.length, 1)
      return prev.map((c, i) => ({
        ...c,
        ventana: [0, duracion] as [number, number],
        inicio: i * seg + seg * 0.15,
        fin: i * seg + seg * 0.85,
      }))
    })
  }

  return (
    <div className="flex min-h-dvh flex-col pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)] lg:grid lg:h-dvh lg:min-h-0 lg:grid-cols-[300px_minmax(0,1fr)_320px] lg:grid-rows-[minmax(0,1fr)]">
      {/* Lista de clips */}
      <aside className="max-h-[30dvh] shrink-0 overflow-y-auto border-b border-line bg-panel p-3 lg:max-h-none lg:border-b-0 lg:border-r">
        <div className="mb-3 flex items-center justify-between gap-2 px-1">
          <h2 className="text-xs font-medium uppercase tracking-wider text-muted">
            {clips.length} {clips.length === 1 ? 'clip' : 'clips'}
          </h2>
          <button
            type="button"
            onClick={() => archivoRef.current?.click()}
            className="press inline-flex items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs hover:bg-raised"
          >
            <Upload size={14} aria-hidden />
            Cargar video
          </button>
          <input ref={archivoRef} type="file" accept="video/*" className="hidden" onChange={alElegirArchivo} />
        </div>

        {clips.length === 0 ? (
          <p className="px-1 text-sm text-muted">Todavía no hay clips. Genera uno y aparecerá aquí.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {clips.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => setSelId(c.id)}
                  aria-pressed={c.id === selId}
                  className={`press w-full min-w-0 rounded-lg border p-3 text-left ${
                    c.id === selId ? 'border-accent bg-raised' : 'border-line hover:bg-raised'
                  }`}
                >
                  <span className="line-clamp-2 wrap-break-word text-sm font-medium">{c.titulo}</span>
                  <span className="mt-1.5 flex items-center gap-2 text-xs text-muted">
                    <span className="rounded bg-bg px-1.5 py-0.5">{c.tipo}</span>
                    <span className="tnum">
                      {formatTime(c.inicio)}–{formatTime(c.fin)}
                    </span>
                    <span className="tnum ml-auto">{Math.round(c.fin - c.inicio)} s</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Vista previa y línea de tiempo */}
      <main className="flex min-h-0 flex-col">
        <div className="flex h-[70dvh] items-center justify-center p-4 lg:h-auto lg:min-h-0 lg:flex-1">
          {sel ? (
            <PreviewStage
              titulo={sel.tituloVideo}
              onChange={actualizarTitulo}
              zonasSeguras={zonasSeguras}
              videoRef={videoRef}
              videoSrc={videoUrl}
              onVideoListo={alVideoListo}
            />
          ) : (
            <p className="text-sm text-muted">Selecciona un clip</p>
          )}
        </div>
        {sel && (
          <Timeline
            videoRef={videoRef}
            videoSrc={videoUrl}
            clipId={sel.id}
            inicio={sel.inicio}
            fin={sel.fin}
            ventana={sel.ventana}
            fps={fps}
            onFps={setFps}
            onCambio={actualizarClip}
          />
        )}
      </main>

      {/* Ajustes */}
      <section className="shrink-0 overflow-y-auto border-t border-line bg-panel p-4 lg:border-l lg:border-t-0">
        {sel && (
          <>
            <h2 className="text-xs font-medium uppercase tracking-wider text-muted">Por qué se eligió</h2>
            <p className="mb-5 mt-1.5 text-sm leading-relaxed">{sel.razon}</p>
            <TituloPanel
              titulo={sel.tituloVideo}
              onChange={actualizarTitulo}
              zonasSeguras={zonasSeguras}
              onZonasSeguras={setZonasSeguras}
            />
          </>
        )}
      </section>
    </div>
  )
}